import secrets
from datetime import datetime
from sqlalchemy.exc import IntegrityError

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from dockerlabs.models import Category, CompletedMachine, EmailVerificationToken, Machine, PasswordResetToken, User


def register_pages_core_routes(
    pages_router,
    get_session,
    create_session_cookie,
    get_fastapi_profile_image_url,
    url_for,
    templates,
    db,
):
    @pages_router.get("/", response_class=HTMLResponse)
    def index_page(request: Request, session: dict = Depends(get_session)):
        query = (
            db.session.query(Machine, Category.categoria)
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
                    "imagen_url": f"/img/maquina/{m.id}",
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
        rest = [m for m, _ in maquinas_con_fecha if m["id"] not in top_2_ids]
        maquinas = top_2 + rest

        completed_machines = []
        user_id = session.get("user_id")
        if user_id:
            comp_objs = CompletedMachine.query.filter_by(user_id=user_id).all()
            completed_machines = [c.machine_name.strip() for c in comp_objs]

        single_machine = len(maquinas) == 1
        categorias_map = {}
        for m in maquinas:
            categorias_map[m["id"]] = m["categoria"] if m["categoria"] else ""

        session_data = {}
        current_user_role = ""
        if user_id:
            current_user_role = session.get("role", "")
            session_data = {"user_id": user_id, "username": session.get("username"), "role": current_user_role}

        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        context = {
            "request": request,
            "maquinas": maquinas,
            "completed_machines": completed_machines,
            "machine_ranks": machine_ranks,
            "single_machine": single_machine,
            "categorias_map": categorias_map,
            "current_user": {"is_authenticated": bool(user_id), "id": user_id},
            "session": session_data,
            "csrf_token_value": csrf_token,
            "url_for": url_for,
            "current_user_role": current_user_role,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        return templates.TemplateResponse(request, "dockerlabs/home.html", context)

    @pages_router.get("/dashboard", response_class=HTMLResponse)
    def dashboard_page(request: Request, session: dict = Depends(get_session)):
        user_id = session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)

        role = session.get("role", "")
        if role not in ["admin", "moderador", "jugador"]:
            raise HTTPException(status_code=403, detail="Acceso denegado")

        maquinas = (
            Machine.query.filter_by(origen="docker").with_entities(Machine.id, Machine.nombre, Machine.autor).order_by(Machine.nombre.asc()).all()
        )

        current_username = session.get("username")
        profile_image_url = get_fastapi_profile_image_url(username=current_username, user_id=user_id)

        user = User.query.get(user_id) if user_id else None

        session_data = {"user_id": user_id, "username": current_username, "role": role}

        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        context = {
            "request": request,
            "maquinas": maquinas,
            "profile_image_url": profile_image_url,
            "user": user,
            "current_user_role": role,
            "session": session_data,
            "csrf_token_value": csrf_token,
            "get_profile_image_url": get_fastapi_profile_image_url,
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        return templates.TemplateResponse(request, "dockerlabs/admin/dashboard.html", context)

    @pages_router.get("/certificados", response_class=HTMLResponse)
    def certificados_page(request: Request, session: dict = Depends(get_session)):
        user_id = session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)

        role = session.get("role", "")
        if role not in ["admin", "moderador", "jugador"]:
            raise HTTPException(status_code=403, detail="Acceso denegado")

        current_username = session.get("username")
        profile_image_url = get_fastapi_profile_image_url(username=current_username, user_id=user_id)

        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        context = {
            "request": request,
            "profile_image_url": profile_image_url,
            "session": {"user_id": user_id, "username": current_username, "role": role},
            "current_user_role": role,
            "csrf_token_value": csrf_token,
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        return templates.TemplateResponse(request, "dockerlabs/user/certificados.html", context)

    @pages_router.get("/logout")
    def logout_page(request: Request):
        response = RedirectResponse(url="/", status_code=302)
        response.delete_cookie(key="session", path="/")
        return response

    @pages_router.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, session: dict = Depends(get_session)):
        user_id = session.get("user_id")
        if user_id:
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token = secrets.token_urlsafe(32)
        session["csrf_token"] = csrf_token
        cookie_val = create_session_cookie(
            session.get("user_id") or 0,
            session.get("username") or "",
            session.get("role") or "jugador",
            existing_session=session,
        )

        context = {
            "request": request,
            "csrf_token_value": csrf_token,
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
            "session": session,
            "success": None,
            "remaining": None,
        }

        response = templates.TemplateResponse(request, "dockerlabs/auth/login.html", context)
        response.set_cookie(key="session", value=cookie_val, httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.get("/register", response_class=HTMLResponse)
    def register_page(request: Request, session: dict = Depends(get_session)):
        if session.get("user_id"):
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token = secrets.token_urlsafe(32)
        session["csrf_token"] = csrf_token
        cookie_val = create_session_cookie(
            session.get("user_id") or 0,
            session.get("username") or "",
            session.get("role") or "jugador",
            existing_session=session,
        )

        context = {
            "remaining": request.query_params.get("remaining"),
            "session": {},
            "csrf_token_value": csrf_token,
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        response = templates.TemplateResponse(request, "dockerlabs/auth/register.html", context)
        response.set_cookie(key="session", value=cookie_val, httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.get("/recover", response_class=HTMLResponse)
    def recover_page(request: Request, session: dict = Depends(get_session)):
        if session.get("user_id"):
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token = secrets.token_urlsafe(32)
        session["csrf_token"] = csrf_token
        cookie_val = create_session_cookie(
            session.get("user_id") or 0,
            session.get("username") or "",
            session.get("role") or "jugador",
            existing_session=session,
        )

        context = {"session": {}, "csrf_token_value": csrf_token, "url_for": url_for, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        response = templates.TemplateResponse(request, "dockerlabs/auth/recover.html", context)
        response.set_cookie(key="session", value=cookie_val, httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.get("/verify-email", response_class=HTMLResponse)
    def verify_email_page(request: Request, token: str = ""):
        error = None
        success = False
        username = ""

        if not token:
            error = "Enlace de verificacion invalido."
        else:
            pending = EmailVerificationToken.query.filter_by(token=token).first()
            if not pending:
                error = "Enlace de verificacion invalido o ya utilizado."
            elif datetime.utcnow() > pending.expires_at:
                db.session.delete(pending)
                db.session.commit()
                error = "El enlace de verificacion ha expirado. Vuelve a registrarte."
            else:
                existing = User.query.filter(
                    (User.username == pending.username) | (User.email == pending.email)
                ).first()
                if existing:
                    db.session.delete(pending)
                    db.session.commit()
                    error = "El usuario o correo ya esta registrado."
                else:
                    try:
                        new_user = User(
                            username=pending.username,
                            email=pending.email,
                            password_hash=pending.password_hash,
                            role="jugador",
                        )
                        db.session.add(new_user)
                        db.session.delete(pending)
                        db.session.commit()
                        success = True
                        username = new_user.username
                    except IntegrityError:
                        db.session.rollback()
                        error = "El usuario o correo ya esta registrado."
                    except Exception:
                        db.session.rollback()
                        error = "Error al crear la cuenta. Intentalo de nuevo."

        context = {
            "request": request,
            "success": success,
            "error": error,
            "username": username,
            "url_for": url_for,
            "session": {},
            "current_user_role": "",
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        return templates.TemplateResponse(request, "dockerlabs/auth/verify_email.html", context)

    @pages_router.get("/reset-password", response_class=HTMLResponse)
    def reset_password_page(request: Request, token: str = ""):
        error = None
        valid_token = False

        if not token:
            error = "Enlace invalido."
        else:
            reset_tok = PasswordResetToken.query.filter_by(token=token, used=False).first()
            if not reset_tok:
                error = "Enlace invalido o ya utilizado."
            elif datetime.utcnow() > reset_tok.expires_at:
                error = "El enlace ha expirado. Solicita uno nuevo desde la pagina de recuperacion."
            else:
                valid_token = True

        csrf_token = secrets.token_urlsafe(32)
        context = {
            "request": request,
            "token": token,
            "valid_token": valid_token,
            "error": error,
            "csrf_token_value": csrf_token,
            "url_for": url_for,
            "session": {},
            "current_user_role": "",
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        return templates.TemplateResponse(request, "dockerlabs/auth/reset_password.html", context)


