from flask import Blueprint, render_template, request, session, redirect, flash, url_for, current_app, send_file
from flask_limiter.errors import RateLimitExceeded

from datetime import datetime
import re
from collections import defaultdict

from dockerlabs.models import (
    User,
    Machine,
    Writeup,
    PendingMachineSubmission
)

from dockerlabs.extensions import db
from .decorators import role_required, csrf_protect
from flask_login import login_required

import os
import io
import shutil
import sqlite3
import tempfile
import zipfile
import fcntl

main_bp = Blueprint('main', __name__)

def _get_db_paths():
    db_path = current_app.config.get('DATABASE')
    if not db_path:
        raise RuntimeError("DATABASE path is not configured")
    return {
        "db": db_path,
        "wal": f"{db_path}-wal",
        "shm": f"{db_path}-shm",
        "journal": f"{db_path}-journal",
    }

def _acquire_db_lock():
    db_paths = _get_db_paths()
    lock_path = f"{db_paths['db']}.lock"
    os.makedirs(os.path.dirname(db_paths['db']), exist_ok=True)
    lock_fh = open(lock_path, 'a+')
    fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
    return lock_fh

def _create_sqlite_snapshot_db(tmp_dir):
    db_paths = _get_db_paths()
    src_db = db_paths['db']
    snapshot_path = os.path.join(tmp_dir, os.path.basename(src_db))

    if not os.path.exists(src_db):
        raise FileNotFoundError("Database file not found")

    src = sqlite3.connect(src_db)
    try:
        try:
            src.execute("PRAGMA wal_checkpoint(FULL);")
        except Exception:
            pass

        dest = sqlite3.connect(snapshot_path)
        try:
            src.backup(dest)
            dest.commit()
        finally:
            dest.close()
    finally:
        src.close()

    return snapshot_path

@main_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('dockerlabs/errors/403.html'), 403

@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('dockerlabs/errors/404.html'), 404

@main_bp.app_errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
           
    retry_after = None
    try:
        m = re.search(r"(\d+)", str(e.description or ""))
        if m:
            retry_after = int(m.group(1))
    except Exception:
        retry_after = None

    if not retry_after:
        retry_after = 15

    session['rate_limit_remaining'] = retry_after

    return redirect(request.path)

@main_bp.route('/403.html')
def error_403_page():
    """
    Página de error 403 (Prohibido).
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Página de error 403.
    """
    return render_template('dockerlabs/403.html')

@main_bp.route('/backups/download', methods=['POST'])
@login_required
@role_required('admin')
@csrf_protect
def download_backup():
    from dockerlabs.extensions import db as alchemy_db

    lock_fh = _acquire_db_lock()
    try:
        alchemy_db.session.remove()
        alchemy_db.engine.dispose()

        with tempfile.TemporaryDirectory(prefix="dockerlabs_backup_") as tmp_dir:
            snapshot_db_path = _create_sqlite_snapshot_db(tmp_dir)

            db_paths = _get_db_paths()
            extras = []
            for k in ('wal', 'shm', 'journal'):
                p = db_paths[k]
                if os.path.exists(p) and os.path.isfile(p):
                    extras.append(p)

            zip_bytes = io.BytesIO()
            with zipfile.ZipFile(zip_bytes, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
                zf.write(snapshot_db_path, arcname=os.path.basename(snapshot_db_path))
                for p in extras:
                    zf.write(p, arcname=os.path.basename(p))

            zip_bytes.seek(0)
            return send_file(
                zip_bytes,
                as_attachment=True,
                download_name='dockerlabs_sqlite_backup.zip',
                mimetype='application/zip'
            )
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fh.close()


@main_bp.route('/backups/restore', methods=['POST'])
@login_required
@role_required('admin')
@csrf_protect
def restore_backup():
    from dockerlabs.extensions import db as alchemy_db

    upload = request.files.get('backup_zip')
    if not upload or not (upload.filename or '').lower().endswith('.zip'):
        flash("Debes proporcionar un archivo .zip", "danger")
        return redirect('/backups')

    lock_fh = _acquire_db_lock()
    try:
        with tempfile.TemporaryDirectory(prefix="dockerlabs_restore_") as tmp_dir:
            zip_path = os.path.join(tmp_dir, 'upload.zip')
            upload.save(zip_path)

            extract_dir = os.path.join(tmp_dir, 'extracted')
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(extract_dir)

            db_paths = _get_db_paths()
            expected_db_name = os.path.basename(db_paths['db'])
            candidate_db = os.path.join(extract_dir, expected_db_name)
            if not os.path.exists(candidate_db):
                db_candidates = []
                for root, _, files in os.walk(extract_dir):
                    for fn in files:
                        if fn.lower().endswith('.db'):
                            db_candidates.append(os.path.join(root, fn))
                if len(db_candidates) != 1:
                    flash("El .zip debe contener exactamente un archivo .db (o el nombre esperado).", "danger")
                    return redirect('/backups')
                candidate_db = db_candidates[0]

            candidate_wal = None
            candidate_shm = None
            candidate_journal = None
            for fn in os.listdir(extract_dir):
                if fn == os.path.basename(db_paths['wal']):
                    candidate_wal = os.path.join(extract_dir, fn)
                elif fn == os.path.basename(db_paths['shm']):
                    candidate_shm = os.path.join(extract_dir, fn)
                elif fn == os.path.basename(db_paths['journal']):
                    candidate_journal = os.path.join(extract_dir, fn)

            alchemy_db.session.remove()
            alchemy_db.engine.dispose()

            db_dir = os.path.dirname(db_paths['db'])
            os.makedirs(db_dir, exist_ok=True)

            for p in (db_paths['wal'], db_paths['shm'], db_paths['journal']):
                try:
                    if os.path.exists(p):
                        os.remove(p)
                except Exception:
                    pass

            with tempfile.NamedTemporaryFile(dir=db_dir, prefix='.restore_tmp.', suffix='.db', delete=False) as tmp_db_fh:
                tmp_db_path = tmp_db_fh.name
            try:
                shutil.copyfile(candidate_db, tmp_db_path)
                os.replace(tmp_db_path, db_paths['db'])
            finally:
                try:
                    if os.path.exists(tmp_db_path):
                        os.remove(tmp_db_path)
                except Exception:
                    pass

            if candidate_wal:
                shutil.copyfile(candidate_wal, db_paths['wal'] + '.tmp')
                os.replace(db_paths['wal'] + '.tmp', db_paths['wal'])
            if candidate_shm:
                shutil.copyfile(candidate_shm, db_paths['shm'] + '.tmp')
                os.replace(db_paths['shm'] + '.tmp', db_paths['shm'])
            if candidate_journal:
                shutil.copyfile(candidate_journal, db_paths['journal'] + '.tmp')
                os.replace(db_paths['journal'] + '.tmp', db_paths['journal'])

        flash("Backup restaurado correctamente.", "success")
        return redirect('/backups')
    except zipfile.BadZipFile:
        flash("El archivo .zip no es válido.", "danger")
        return redirect('/backups')
    except Exception as e:
        flash(f"Error al restaurar el backup: {str(e)}", "danger")
        return redirect('/backups')
    finally:
        try:
            fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
        finally:
            lock_fh.close()

# =========================
# PENDING MACHINES (ADMIN)
# =========================

