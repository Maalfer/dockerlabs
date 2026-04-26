import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = None

def configure_limiter(global_limiter):
    """Configura el limiter global desde asgi.py"""
    global limiter
    limiter = global_limiter


def register_pages_core_routes(
    pages_router,
    get_flask_session,
    create_flask_session_cookie,
    get_fastapi_profile_image_url,
    url_for,
    templates,
    alchemy_db,
):
    @pages_router.get("/", response_class=HTMLResponse)
    def index_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        from dockerlabs.models import Category, CompletedMachine, Machine

        query = (
            alchemy_db.session.query(Machine, Category.categoria)
            .filter(Machine.origen == "docker")
            .outerjoin(Category, (Machine.id == Category.machine_id) & (Category.origen == "docker"))
            .order_by(Machine.id.asc())
            .all()
        )

        all_maquinas = []
        for m, cat_name in query:
            all_maquinas.append(
                {
                    "id": m.id,
                    "nombre": m.nombre,
                    "dificultad": m.dificultad,
                    "clase": m.clase,
                    "color": m.color,
                    "autor": m.autor,
                    "enlace_autor": m.enlace_autor,
                    "fecha": m.fecha,
                    "imagen": m.imagen,
                    "imagen_url": f"/api/img/maquina/{m.id}",
                    "descripcion": m.descripcion,
                    "link_descarga": m.link_descarga,
                    "categoria": cat_name,
                }
            )

        maquinas_con_fecha = []
        for m_dict in all_maquinas:
            fecha_str = m_dict["fecha"]
            try:
                parts = fecha_str.split("/")
                if len(parts) == 3:
                    fecha_iso = f"{parts[2]}-{parts[1]}-{parts[0]}"
                    maquinas_con_fecha.append((m_dict, fecha_iso))
            except Exception:
                pass

        maquinas_con_fecha.sort(key=lambda x: x[1], reverse=True)
        machine_ranks = {}
        top_2_items = maquinas_con_fecha[:2]
        for idx, (m, _) in enumerate(top_2_items):
            machine_ranks[m["id"]] = idx + 1

        top_2_ids = {m["id"] for m, _ in top_2_items}
        top_2 = [m for m, _ in top_2_items]
        rest = [m for m in all_maquinas if m["id"] not in top_2_ids]
        maquinas = top_2 + rest

        completed_machines = []
        user_id = flask_session.get("user_id")
        if user_id:
            comp_objs = CompletedMachine.query.filter_by(user_id=user_id).all()
            completed_machines = [c.machine_name.strip() for c in comp_objs]

        single_machine = len(maquinas) == 1
        categorias_map = {}
        for m in maquinas:
            categorias_map[m["id"]] = m["categoria"] if m["categoria"] else ""

        session_data = {}
        if user_id:
            session_data = {"user_id": user_id, "username": flask_session.get("username"), "role": flask_session.get("role")}

        context = {
            "request": request,
            "maquinas": maquinas,
            "completed_machines": completed_machines,
            "machine_ranks": machine_ranks,
            "single_machine": single_machine,
            "categorias_map": categorias_map,
            "current_user": {"is_authenticated": bool(user_id), "id": user_id},
            "session": session_data,
            "csrf_token_value": secrets.token_urlsafe(32),
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        return templates.TemplateResponse(request, "dockerlabs/home.html", context)

    @pages_router.get("/dashboard", response_class=HTMLResponse)
    def dashboard_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        from dockerlabs.models import Machine

        user_id = flask_session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)

        role = flask_session.get("role", "")
        if role not in ["admin", "moderador", "jugador"]:
            raise HTTPException(status_code=403, detail="Acceso denegado")

        maquinas = (
            Machine.query.filter_by(origen="docker").with_entities(Machine.id, Machine.nombre, Machine.autor).order_by(Machine.nombre.asc()).all()
        )

        current_username = flask_session.get("username")
        profile_image_url = get_fastapi_profile_image_url(username=current_username, user_id=user_id)

        session_data = {}
        if user_id:
            session_data = {"user_id": user_id, "username": current_username, "role": role}

        context = {
            "request": request,
            "maquinas": maquinas,
            "profile_image_url": profile_image_url,
            "user": {"id": user_id, "username": current_username, "role": role},
            "current_user_role": role,
            "session": session_data,
            "csrf_token_value": secrets.token_urlsafe(32),
            "get_profile_image_url": get_fastapi_profile_image_url,
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        return templates.TemplateResponse(request, "dockerlabs/admin/dashboard.html", context)

    @pages_router.get("/logout")
    def logout_page(request: Request):
        response = RedirectResponse(url="/", status_code=302)
        response.delete_cookie(key="session", path="/")
        return response

    @pages_router.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        user_id = flask_session.get("user_id")
        if user_id:
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token = secrets.token_urlsafe(32)
        flask_session["csrf_token"] = csrf_token
        cookie_val = create_flask_session_cookie(
            flask_session.get("user_id") or 0,
            flask_session.get("username") or "",
            flask_session.get("role") or "jugador",
            existing_session=flask_session,
        )

        context = {
            "request": request,
            "csrf_token_value": csrf_token,
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
            "session": flask_session,
            "success": None,
            "remaining": None,
        }

        response = templates.TemplateResponse(request, "dockerlabs/auth/login.html", context)
        response.set_cookie(key="session", value=cookie_val, httponly=True, path="/", samesite="lax")
        return response

    @pages_router.get("/register", response_class=HTMLResponse)
    def register_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        if flask_session.get("user_id"):
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token = secrets.token_urlsafe(32)
        flask_session["csrf_token"] = csrf_token
        cookie_val = create_flask_session_cookie(
            flask_session.get("user_id") or 0,
            flask_session.get("username") or "",
            flask_session.get("role") or "jugador",
            existing_session=flask_session,
        )

        session_data = {}
        if flask_session.get("user_id"):
            session_data = {
                "user_id": flask_session.get("user_id"),
                "username": flask_session.get("username"),
                "role": flask_session.get("role"),
            }

        context = {
            "remaining": request.query_params.get("remaining"),
            "session": session_data,
            "csrf_token_value": csrf_token,
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        response = templates.TemplateResponse(request, "dockerlabs/auth/register.html", context)
        response.set_cookie(key="session", value=cookie_val, httponly=True, path="/", samesite="lax")
        return response

    @pages_router.get("/recover", response_class=HTMLResponse)
    def recover_page(request: Request, flask_session: dict = Depends(get_flask_session)):
        if flask_session.get("user_id"):
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token = secrets.token_urlsafe(32)
        flask_session["csrf_token"] = csrf_token
        cookie_val = create_flask_session_cookie(
            flask_session.get("user_id") or 0,
            flask_session.get("username") or "",
            flask_session.get("role") or "jugador",
            existing_session=flask_session,
        )

        session_data = {}
        if flask_session.get("user_id"):
            session_data = {
                "user_id": flask_session.get("user_id"),
                "username": flask_session.get("username"),
                "role": flask_session.get("role"),
            }

        context = {"session": session_data, "csrf_token_value": csrf_token, "url_for": url_for, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        response = templates.TemplateResponse(request, "dockerlabs/auth/recover.html", context)
        response.set_cookie(key="session", value=cookie_val, httponly=True, path="/", samesite="lax")
        return response

