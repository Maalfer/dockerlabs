import fcntl
import io
import math
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import datetime

import secrets
from fastapi import Depends, File, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

from dockerlabs.models import User


def register_pages_admin_routes(
    pages_router,
    get_flask_session,
    verify_csrf_token,
    require_auth_and_role,
    set_flask_session_cookie,
    templates,
    generate_csrf_token,
    url_for,
    alchemy_db,
):
    @pages_router.get("/instrucciones-uso", response_class=HTMLResponse)
    def instrucciones_uso_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/instrucciones_uso.html",
            {"url_for": url_for, "session": flask_session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/soporte", response_class=HTMLResponse)
    def soporte_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request, "dockerlabs/info/soporte.html", {"url_for": url_for, "session": flask_session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/equipo", response_class=HTMLResponse)
    def equipo_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request, "dockerlabs/equipo.html", {"url_for": url_for, "session": flask_session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/enviar-maquina", response_class=HTMLResponse)
    def enviar_maquina_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/enviar_maquina.html",
            {"url_for": url_for, "session": flask_session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/como-se-crea-una-maquina", response_class=HTMLResponse)
    def como_se_crea_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/como_se_crea_una_maquina.html",
            {"url_for": url_for, "session": flask_session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/agradecimientos", response_class=HTMLResponse)
    def agradecimientos_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/agradecimientos.html",
            {"url_for": url_for, "session": flask_session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/terminos-condiciones", response_class=HTMLResponse)
    def terminos_condiciones_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/terminos-condiciones.html",
            {"url_for": url_for, "session": flask_session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/bug-bounty")
    def bug_bounty_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        return RedirectResponse(url="/", status_code=302)

    @pages_router.get("/politica-privacidad", response_class=HTMLResponse)
    def politica_privacidad_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        return templates.TemplateResponse(
            request,
            "politicas/politica_privacidad.html",
            {"url_for": url_for, "session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/politica-cookies", response_class=HTMLResponse)
    def politica_cookies_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        return templates.TemplateResponse(
            request,
            "politicas/politica_cookies.html",
            {"url_for": url_for, "session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/condiciones-uso", response_class=HTMLResponse)
    def condiciones_uso_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        return templates.TemplateResponse(
            request, "politicas/condiciones_uso.html", {"url_for": url_for, "session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/gestion-usuarios", response_class=HTMLResponse)
    def gestion_usuarios_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador"])
        if not ok:
            return redirect

        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 10))
        search = request.query_params.get("search", "").strip()

        query = User.query
        if search:
            query = query.filter((User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")) | (User.role.ilike(f"%{search}%")))

        total = query.count()
        usuarios = query.order_by(User.id.asc()).offset((page - 1) * per_page).limit(per_page).all()
        total_pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages

        csrf_token = flask_session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/gestion_usuarios.html",
            {
                "usuarios": usuarios,
                "session": flask_session,
                "csrf_token_value": csrf_token,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_prev": has_prev,
                "has_next": has_next,
                "search": search,
                "url_for": url_for,
                "current_user_role": flask_session.get("role", ""),
            },
        )

    @pages_router.get("/gestion-maquinas", response_class=HTMLResponse)
    def gestion_maquinas_page(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        page: int = 1,
        per_page: int = 20,
        search: str = "",
    ):
        from sqlalchemy import or_
        from dockerlabs.models import Category, Machine

        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect

        current_username = flask_session.get("username", "")
        role = flask_session.get("role", "")

        def build_query(origen):
            query = Machine.query.filter_by(origen=origen)
            if role not in ("admin", "moderador"):
                if current_username:
                    query = query.filter_by(autor=current_username)
                else:
                    return query.filter(False)
            if search:
                search_term = f"%{search}%"
                query = query.filter(or_(Machine.nombre.ilike(search_term), Machine.autor.ilike(search_term), Machine.dificultad.ilike(search_term)))
            return query.order_by(Machine.id.asc())

        docker_query = build_query("docker")
        bunker_query = build_query("bunker")
        docker_total = docker_query.count()
        bunker_total = bunker_query.count()

        # Manual pagination using SQLAlchemy limit/offset
        docker_items = docker_query.limit(per_page).offset((page - 1) * per_page).all()
        bunker_items = bunker_query.limit(per_page).offset((page - 1) * per_page).all()

        maquinas_docker = docker_items
        maquinas_bunker = bunker_items

        # Calculate pagination properties
        docker_pages = math.ceil(docker_total / per_page) if per_page > 0 else 1
        bunker_pages = math.ceil(bunker_total / per_page) if per_page > 0 else 1
        docker_has_prev = page > 1
        docker_has_next = page < docker_pages
        bunker_has_prev = page > 1
        bunker_has_next = page < bunker_pages

        categorias_map = {}
        if maquinas_docker:
            docker_ids = [m.id for m in maquinas_docker]
            docker_cats = Category.query.filter_by(origen="docker").filter(Category.machine_id.in_(docker_ids)).all()
            docker_lookup = {c.machine_id: c.categoria for c in docker_cats}
            for m in maquinas_docker:
                categorias_map[("docker", m.id)] = docker_lookup.get(m.id, "")

        if maquinas_bunker:
            bunker_ids = [m.id for m in maquinas_bunker]
            if bunker_ids:
                bunker_cats = Category.query.filter(Category.origen == "bunker", Category.machine_id.in_(bunker_ids)).all()
                bunker_lookup = {c.machine_id: c.categoria for c in bunker_cats}
                for m in maquinas_bunker:
                    categorias_map[("bunker", m.id)] = bunker_lookup.get(m.id, "")

        current_user_role = flask_session.get("role", "")
        csrf_token = flask_session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/gestion_maquinas.html",
            {
                "maquinas_docker": maquinas_docker,
                "maquinas_bunker": maquinas_bunker,
                "categorias_map": categorias_map,
                "csrf_token_value": csrf_token,
                "page": page,
                "per_page": per_page,
                "search": search,
                "docker_total": docker_total,
                "bunker_total": bunker_total,
                "docker_pages": docker_pages,
                "bunker_pages": bunker_pages,
                "docker_has_prev": docker_has_prev,
                "docker_has_next": docker_has_next,
                "bunker_has_prev": bunker_has_prev,
                "bunker_has_next": bunker_has_next,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "session": flask_session,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.get("/backups", response_class=HTMLResponse)
    def backups_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        user_id = flask_session.get('user_id')
        role = flask_session.get('role', '')
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)
        if role != 'admin':
            return RedirectResponse(url="/", status_code=302)
        csrf_token = flask_session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/backups.html",
            {"session": flask_session, "url_for": url_for, "current_user_role": role, "csrf_token_value": csrf_token, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    def _get_db_paths():
        from dockerlabs.database import DATABASE_PATH

        db_path = DATABASE_PATH
        if not db_path:
            raise RuntimeError("DATABASE path is not configured")
        return {"db": db_path, "wal": f"{db_path}-wal", "shm": f"{db_path}-shm", "journal": f"{db_path}-journal"}

    def _get_db_engine():
        from dockerlabs.database import engine
        return engine

    def _acquire_db_lock():
        db_paths = _get_db_paths()
        lock_path = f"{db_paths['db']}.lock"
        os.makedirs(os.path.dirname(db_paths["db"]), exist_ok=True)
        lock_fh = open(lock_path, "a+")
        fcntl.flock(lock_fh.fileno(), fcntl.LOCK_EX)
        return lock_fh

    def _create_sqlite_snapshot_db(tmp_dir):
        db_paths = _get_db_paths()
        src_db = db_paths["db"]
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

    @pages_router.post("/backups/download")
    async def download_backup(
        request: Request,
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        user_id = flask_session.get('user_id')
        role = flask_session.get('role', '')
        if not user_id:
            return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        if role != 'admin':
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        lock_fh = _acquire_db_lock()
        try:
            alchemy_db.session.remove()
            _get_db_engine().dispose()
            with tempfile.TemporaryDirectory(prefix="dockerlabs_backup_") as tmp_dir:
                snapshot_db_path = _create_sqlite_snapshot_db(tmp_dir)
                db_paths = _get_db_paths()
                extras = []
                for k in ("wal", "shm", "journal"):
                    p = db_paths[k]
                    if os.path.exists(p) and os.path.isfile(p):
                        extras.append(p)
                
                # Incluir carpeta de almacenamiento de imágenes
                almacenamiento_dir = os.path.join(os.path.dirname(db_paths["db"]), "almacenamiento")
                
                zip_bytes = io.BytesIO()
                with zipfile.ZipFile(zip_bytes, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(snapshot_db_path, arcname=os.path.basename(snapshot_db_path))
                    for p in extras:
                        zf.write(p, arcname=os.path.basename(p))
                    
                    # Agregar carpeta almacenamiento si existe
                    if os.path.exists(almacenamiento_dir) and os.path.isdir(almacenamiento_dir):
                        for root, dirs, files in os.walk(almacenamiento_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                arcname = os.path.join("almacenamiento", os.path.relpath(file_path, almacenamiento_dir))
                                zf.write(file_path, arcname=arcname)
                
                zip_bytes.seek(0)
                return StreamingResponse(
                    zip_bytes,
                    media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="dockerlabs_backup.zip"'},
                )
        finally:
            try:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
            finally:
                lock_fh.close()

    @pages_router.post("/backups/restore")
    async def restore_backup(
        backup_zip: UploadFile = File(...),
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        user_id = flask_session.get('user_id')
        role = flask_session.get('role', '')
        if not user_id:
            return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})
        if role != 'admin':
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        if not backup_zip or not (backup_zip.filename or "").lower().endswith(".zip"):
            flask_session["_flashes"] = [("danger", "Debes proporcionar un archivo .zip")]
            cookie = set_flask_session_cookie(flask_session)
            resp = RedirectResponse(url="/backups", status_code=302)
            resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
            return resp

        lock_fh = _acquire_db_lock()
        try:
            with tempfile.TemporaryDirectory(prefix="dockerlabs_restore_") as tmp_dir:
                zip_path = os.path.join(tmp_dir, "upload.zip")
                content = await backup_zip.read()
                with open(zip_path, "wb") as f:
                    f.write(content)
                extract_dir = os.path.join(tmp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extract_dir)

                db_paths = _get_db_paths()
                expected_db_name = os.path.basename(db_paths["db"])
                candidate_db = os.path.join(extract_dir, expected_db_name)
                if not os.path.exists(candidate_db):
                    db_candidates = []
                    for root, _, files in os.walk(extract_dir):
                        for fn in files:
                            if fn.lower().endswith(".db"):
                                db_candidates.append(os.path.join(root, fn))
                    if len(db_candidates) != 1:
                        flask_session["_flashes"] = [("danger", "El .zip debe contener exactamente un archivo .db (o el nombre esperado).")]
                        cookie = set_flask_session_cookie(flask_session)
                        resp = RedirectResponse(url="/backups", status_code=302)
                        resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
                        return resp
                    candidate_db = db_candidates[0]

                candidate_wal = None
                candidate_shm = None
                candidate_journal = None
                for fn in os.listdir(extract_dir):
                    if fn == os.path.basename(db_paths["wal"]):
                        candidate_wal = os.path.join(extract_dir, fn)
                    elif fn == os.path.basename(db_paths["shm"]):
                        candidate_shm = os.path.join(extract_dir, fn)
                    elif fn == os.path.basename(db_paths["journal"]):
                        candidate_journal = os.path.join(extract_dir, fn)

                alchemy_db.session.remove()
                _get_db_engine().dispose()
                db_dir = os.path.dirname(db_paths["db"])
                os.makedirs(db_dir, exist_ok=True)
                for p in (db_paths["wal"], db_paths["shm"], db_paths["journal"]):
                    try:
                        if os.path.exists(p):
                            os.remove(p)
                    except Exception:
                        pass

                with tempfile.NamedTemporaryFile(dir=db_dir, prefix=".restore_tmp.", suffix=".db", delete=False) as tmp_db_fh:
                    tmp_db_path = tmp_db_fh.name
                try:
                    shutil.copyfile(candidate_db, tmp_db_path)
                    os.replace(tmp_db_path, db_paths["db"])
                finally:
                    try:
                        if os.path.exists(tmp_db_path):
                            os.remove(tmp_db_path)
                    except Exception:
                        pass

                if candidate_wal:
                    shutil.copyfile(candidate_wal, db_paths["wal"] + ".tmp")
                    os.replace(db_paths["wal"] + ".tmp", db_paths["wal"])
                if candidate_shm:
                    shutil.copyfile(candidate_shm, db_paths["shm"] + ".tmp")
                    os.replace(db_paths["shm"] + ".tmp", db_paths["shm"])
                if candidate_journal:
                    shutil.copyfile(candidate_journal, db_paths["journal"] + ".tmp")
                    os.replace(db_paths["journal"] + ".tmp", db_paths["journal"])

                # Restaurar carpeta almacenamiento si existe en el backup
                almacenamiento_extract_dir = os.path.join(extract_dir, "almacenamiento")
                if os.path.exists(almacenamiento_extract_dir) and os.path.isdir(almacenamiento_extract_dir):
                    almacenamiento_target_dir = os.path.join(db_dir, "almacenamiento")
                    # Eliminar carpeta almacenamiento existente si existe
                    if os.path.exists(almacenamiento_target_dir):
                        shutil.rmtree(almacenamiento_target_dir, ignore_errors=True)
                    # Copiar carpeta almacenamiento desde el backup
                    shutil.copytree(almacenamiento_extract_dir, almacenamiento_target_dir)

            flask_session["_flashes"] = [("success", "Backup restaurado correctamente.")]
            cookie = set_flask_session_cookie(flask_session)
            resp = RedirectResponse(url="/backups", status_code=302)
            resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
            return resp
        except zipfile.BadZipFile:
            flask_session["_flashes"] = [("danger", "El archivo .zip no es válido.")]
            cookie = set_flask_session_cookie(flask_session)
            resp = RedirectResponse(url="/backups", status_code=302)
            resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
            return resp
        except Exception as e:
            flask_session["_flashes"] = [("danger", f"Error al restaurar el backup: {str(e)}")]
            cookie = set_flask_session_cookie(flask_session)
            resp = RedirectResponse(url="/backups", status_code=302)
            resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
            return resp
        finally:
            try:
                fcntl.flock(lock_fh.fileno(), fcntl.LOCK_UN)
            finally:
                lock_fh.close()

    @pages_router.get("/pending-machines", response_class=HTMLResponse)
    def pending_machines_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        from dockerlabs.models import PendingMachineSubmission

        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador"])
        if not ok:
            return redirect
        machines = PendingMachineSubmission.query.order_by(PendingMachineSubmission.submitted_at.desc()).all()
        current_user_role = flask_session.get("role", "")
        csrf_token = flask_session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/pending.html",
            {"machines": machines, "session": flask_session, "url_for": url_for, "current_user_role": current_user_role, "csrf_token_value": csrf_token, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/user-pending", response_class=HTMLResponse)
    def user_pending_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        user_id = flask_session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/auth/user-pending.html",
            {"username": flask_session.get("username"), "session": flask_session, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/writeups-recibidos", response_class=HTMLResponse)
    def writeups_recibidos_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect
        user = User.query.get(flask_session.get("user_id")) if flask_session.get("user_id") else None
        csrf_token = flask_session.get("csrf_token") or secrets.token_urlsafe(32)
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_recibidos.html",
            {"session": flask_session, "user": user, "csrf_token_value": csrf_token, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/writeups-publicados", response_class=HTMLResponse)
    def writeups_publicados_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect
        user = User.query.get(flask_session.get("user_id")) if flask_session.get("user_id") else None
        csrf_token = flask_session.get("csrf_token") or secrets.token_urlsafe(32)
        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_publicados.html",
            {"user": user, "session": flask_session, "csrf_token_value": csrf_token, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/peticiones", response_class=HTMLResponse)
    def peticiones_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        from dockerlabs.models import (
            WriteupEditRequest, MachineClaim, UsernameChangeRequest,
            MachineEditRequest, NameClaim, User
        )
        from sqlalchemy import func

        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador"])
        if not ok:
            return redirect

        # 1. Reclamaciones de autoría de máquinas
        claims = MachineClaim.query.order_by(MachineClaim.id.desc()).all()

        # 2. Peticiones de cambio de username (con info adicional del usuario)
        username_requests = UsernameChangeRequest.query.order_by(UsernameChangeRequest.id.desc()).all()
        username_change_requests = []
        for r in username_requests:
            user = User.query.get(r.user_id)
            username_change_requests.append({
                "id": r.id,
                "user_id": r.user_id,
                "old_username": r.old_username,
                "requested_username": r.requested_username,
                "reason": r.reason,
                "contacto_opcional": r.contacto_opcional,
                "estado": r.estado,
                "created_at": r.created_at,
                "processed_by": r.processed_by,
                "processed_at": r.processed_at,
                "decision_reason": r.decision_reason,
                "user_email": user.email if user else None,
                "conflict_count": getattr(r, 'conflict_count', None),
                "conflict_examples": getattr(r, 'conflict_examples', None),
            })

        # 3. Peticiones de edición de máquinas
        machine_edits = MachineEditRequest.query.order_by(MachineEditRequest.id.desc()).all()
        machine_edit_requests = []
        for r in machine_edits:
            import json
            try:
                nuevos = json.loads(r.nuevos_datos) if r.nuevos_datos else {}
            except:
                nuevos = {}
            machine_edit_requests.append({
                "id": r.id,
                "machine_id": r.machine_id,
                "origen": r.origen,
                "autor": r.autor,
                "nuevos": nuevos,
                "estado": r.estado,
                "fecha": r.fecha,
            })

        # 4. Peticiones de registro de nombres duplicados
        name_claims = NameClaim.query.order_by(NameClaim.id.desc()).all()
        peticiones_nombres = []
        for p in name_claims:
            user = User.query.filter_by(username=p.username).first()
            peticiones_nombres.append({
                "id": p.id,
                "username": p.username,
                "email": p.email,
                "nombre_solicitado": p.nombre_solicitado,
                "nombre_actual": p.nombre_actual,
                "motivo": p.motivo,
                "estado": p.estado,
                "created_at": p.created_at,
            })

        # 5. Peticiones de edición de writeups
        writeup_edits = WriteupEditRequest.query.order_by(WriteupEditRequest.id.desc()).all()
        edit_requests = []
        for r in writeup_edits:
            edit_requests.append({
                "id": r.id,
                "writeup_id": r.writeup_id,
                "user_id": r.user_id,
                "username": r.username,
                "maquina_actual": r.maquina_original,
                "autor_actual": r.autor_original,
                "url_actual": r.url_original,
                "tipo_actual": r.tipo_original,
                "maquina_nueva": r.maquina_nueva,
                "autor_nuevo": r.autor_nuevo,
                "url_nueva": r.url_nueva,
                "tipo_nuevo": r.tipo_nuevo,
                "estado": r.estado,
                "created_at": r.created_at,
            })

        current_user_role = flask_session.get("role", "")
        csrf_token = flask_session.get("csrf_token") or secrets.token_urlsafe(32)

        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/peticiones.html",
            {
                "claims": claims,
                "username_change_requests": username_change_requests,
                "machine_edit_requests": machine_edit_requests,
                "peticiones_nombres": peticiones_nombres,
                "edit_requests": edit_requests,
                "session": flask_session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.get("/estadisticas", response_class=HTMLResponse)
    def estadisticas_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        from dockerlabs.models import Machine, Writeup

        def parse_date_flexible(date_str):
            """Parse date string trying multiple formats."""
            for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
            raise ValueError(f"Unable to parse date: {date_str}")

        def get_distribution_by_year(items, date_extractor):
            """Calculate distribution by year."""
            years = {}
            for item in items:
                year = date_extractor(item).year
                years[year] = years.get(year, 0) + 1
            return years

        def get_distribution_by_month(items, date_extractor):
            """Calculate distribution by month."""
            months = {}
            for item in items:
                date = date_extractor(item)
                month_key = f"{date.year}-{date.month:02d}"
                months[month_key] = months.get(month_key, 0) + 1
            return months

        def get_distribution_by_field(items, field_name):
            """Calculate distribution by a specific field."""
            distribution = {}
            for item in items:
                value = getattr(item, field_name, None)
                if value:
                    distribution[value] = distribution.get(value, 0) + 1
            return distribution

        machines = Machine.query.all()
        writeups = Writeup.query.all()
        users = User.query.all()

        machine_stats = {
            "total": len(machines),
            "by_dificultad": get_distribution_by_field(machines, "dificultad"),
            "by_origen": get_distribution_by_field(machines, "origen"),
            "by_year": get_distribution_by_year(machines, lambda m: parse_date_flexible(m.fecha)),
            "by_month": get_distribution_by_month(machines, lambda m: parse_date_flexible(m.fecha)),
        }

        writeup_stats = {
            "total": len(writeups),
            "by_tipo": get_distribution_by_field(writeups, "tipo"),
            "by_year": get_distribution_by_year(writeups, lambda w: w.created_at),
            "by_month": get_distribution_by_month(writeups, lambda w: w.created_at),
        }

        user_stats = {
            "total": len(users),
            "by_role": get_distribution_by_field(users, "role"),
            "by_year": get_distribution_by_year(users, lambda u: u.created_at),
            "by_month": get_distribution_by_month(users, lambda u: u.created_at),
        }

        current_user_role = flask_session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/estadisticas.html",
            {"machine_stats": machine_stats, "writeup_stats": writeup_stats, "user_stats": user_stats, "session": flask_session, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )
