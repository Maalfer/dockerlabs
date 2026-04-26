import fcntl
import io
import os
import shutil
import sqlite3
import tempfile
import zipfile

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
    def instrucciones_uso_page(request: Request):
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/instrucciones_uso.html",
            {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/soporte", response_class=HTMLResponse)
    def soporte_page(request: Request):
        return templates.TemplateResponse(
            request, "dockerlabs/info/soporte.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/equipo", response_class=HTMLResponse)
    def equipo_page(request: Request):
        return templates.TemplateResponse(
            request, "dockerlabs/equipo.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/enviar-maquina", response_class=HTMLResponse)
    def enviar_maquina_page(request: Request):
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/enviar_maquina.html",
            {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/como-se-crea-una-maquina", response_class=HTMLResponse)
    def como_se_crea_page(request: Request):
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/como_se_crea_una_maquina.html",
            {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/agradecimientos", response_class=HTMLResponse)
    def agradecimientos_page(request: Request):
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/agradecimientos.html",
            {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/terminos-condiciones", response_class=HTMLResponse)
    def terminos_condiciones_page(request: Request):
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/terminos-condiciones.html",
            {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/bug-bounty", response_class=HTMLResponse)
    def bug_bounty_page(request: Request):
        return templates.TemplateResponse(
            request, "dockerlabs/bug_bounty.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/politica-privacidad", response_class=HTMLResponse)
    def politica_privacidad_page(request: Request):
        return templates.TemplateResponse(
            request,
            "politicas/politica_privacidad.html",
            {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/politica-cookies", response_class=HTMLResponse)
    def politica_cookies_page(request: Request):
        return templates.TemplateResponse(
            request,
            "politicas/politica_cookies.html",
            {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/condiciones-uso", response_class=HTMLResponse)
    def condiciones_uso_page(request: Request):
        return templates.TemplateResponse(
            request, "politicas/condiciones_uso.html", {"url_for": url_for, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
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

        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/gestion_usuarios.html",
            {
                "usuarios": usuarios,
                "session": flask_session,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_prev": has_prev,
                "has_next": has_next,
                "search": search,
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
        docker_pagination = docker_query.paginate(page=page, per_page=per_page, error_out=False)
        bunker_pagination = bunker_query.paginate(page=page, per_page=per_page, error_out=False)
        maquinas_docker = docker_pagination.items
        maquinas_bunker = bunker_pagination.items

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

        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/gestion_maquinas.html",
            {
                "maquinas_docker": maquinas_docker,
                "maquinas_bunker": maquinas_bunker,
                "categorias_map": categorias_map,
                "csrf_token_value": generate_csrf_token(),
                "page": page,
                "per_page": per_page,
                "search": search,
                "docker_total": docker_total,
                "bunker_total": bunker_total,
                "docker_pages": docker_pagination.pages,
                "bunker_pages": bunker_pagination.pages,
                "docker_has_prev": docker_pagination.has_prev,
                "docker_has_next": docker_pagination.has_next,
                "bunker_has_prev": bunker_pagination.has_prev,
                "bunker_has_next": bunker_pagination.has_next,
            },
        )

    @pages_router.get("/backups", response_class=HTMLResponse)
    def backups_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        ok, redirect = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return redirect
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/backups.html",
            {"session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    def _get_db_paths():
        from dockerlabs.database import DATABASE_PATH

        db_path = DATABASE_PATH
        if not db_path:
            raise RuntimeError("DATABASE path is not configured")
        return {"db": db_path, "wal": f"{db_path}-wal", "shm": f"{db_path}-shm", "journal": f"{db_path}-journal"}

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
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, redirect = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return redirect

        lock_fh = _acquire_db_lock()
        try:
            alchemy_db.session.remove()
            alchemy_db.engine.dispose()
            with tempfile.TemporaryDirectory(prefix="dockerlabs_backup_") as tmp_dir:
                snapshot_db_path = _create_sqlite_snapshot_db(tmp_dir)
                db_paths = _get_db_paths()
                extras = []
                for k in ("wal", "shm", "journal"):
                    p = db_paths[k]
                    if os.path.exists(p) and os.path.isfile(p):
                        extras.append(p)
                zip_bytes = io.BytesIO()
                with zipfile.ZipFile(zip_bytes, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    zf.write(snapshot_db_path, arcname=os.path.basename(snapshot_db_path))
                    for p in extras:
                        zf.write(p, arcname=os.path.basename(p))
                zip_bytes.seek(0)
                return StreamingResponse(
                    zip_bytes,
                    media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="dockerlabs_sqlite_backup.zip"'},
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
        ok, redirect = require_auth_and_role(flask_session, ["admin"])
        if not ok:
            return redirect

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
                alchemy_db.engine.dispose()
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
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/pending_machines.html",
            {"machines": machines, "session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/user-pending", response_class=HTMLResponse)
    def user_pending_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        user_id = flask_session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/user_pending.html",
            {"username": flask_session.get("username"), "session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/writeups-recibidos", response_class=HTMLResponse)
    def writeups_recibidos_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect
        user = User.query.get(flask_session.get("user_id")) if flask_session.get("user_id") else None
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_recibidos.html",
            {"session": flask_session, "user": user, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/writeups-publicados", response_class=HTMLResponse)
    def writeups_publicados_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect
        user = User.query.get(flask_session.get("user_id")) if flask_session.get("user_id") else None
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_publicados.html",
            {"user": user, "session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/peticiones-writeups", response_class=HTMLResponse)
    def peticiones_writeups_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        from dockerlabs.models import WriteupEditRequest

        ok, redirect = require_auth_and_role(flask_session, ["admin", "moderador"])
        if not ok:
            return redirect
        requests = WriteupEditRequest.query.order_by(WriteupEditRequest.id.desc()).all()
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/peticiones_writeups.html",
            {"peticiones": requests, "session": flask_session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/estadisticas", response_class=HTMLResponse)
    def estadisticas_page(request: Request):
        from dockerlabs.models import Machine, Writeup

        def get_distribution_by_year(items, date_extractor):
            year_counts = {}
            total = 0
            for item in items:
                try:
                    year = date_extractor(item)
                    if year:
                        year_counts[year] = year_counts.get(year, 0) + 1
                        total += 1
                except Exception:
                    continue
            distribution = {}
            if total > 0:
                for year, count in year_counts.items():
                    distribution[year] = round((count / total) * 100, 2)
            return dict(sorted(distribution.items()))

        machines = Machine.query.all()

        def machine_date_extractor(m):
            try:
                parts = m.fecha.split("/")
                if len(parts) == 3:
                    return int(parts[2])
            except Exception:
                return None
            return None

        machine_stats = get_distribution_by_year(machines, machine_date_extractor)
        writeups = Writeup.query.all()

        def writeup_date_extractor(w):
            return w.created_at.year if w.created_at else None

        writeup_stats = get_distribution_by_year(writeups, writeup_date_extractor)
        users = User.query.all()

        def user_date_extractor(u):
            return u.created_at.year if u.created_at else None

        user_stats = get_distribution_by_year(users, user_date_extractor)
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/estadisticas.html",
            {"machine_stats": machine_stats, "writeup_stats": writeup_stats, "user_stats": user_stats, "session": {}, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

