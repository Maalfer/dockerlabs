import hashlib
import os
import re
import secrets
from datetime import datetime
from urllib.parse import quote, urlencode

from sqlalchemy.exc import IntegrityError

from fastapi import Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from dockerlabs.models import OutboundClickLog

from dockerlabs.models import ApiToken, Category, Certificate, CompletedMachine, EmailChangeToken, EmailVerificationToken, Machine, PasswordResetToken, User


def register_pages_core_routes(
    pages_router,
    get_session,
    create_session_cookie,
    compute_csrf_token,
    get_fastapi_profile_image_url,
    url_for,
    templates,
    db,
):
    # Enlaces salientes hacia elrincondelhacker.es con recuento propio y UTM (trazabilidad de leads:
    # MailerUp guarda utm_source=dockerlabs como origen del suscriptor). Ver /opt/mailerup/docs/TRAZABILIDAD.md
    _GO_DESTINOS = {
        "newsletter": "https://elrincondelhacker.es/newsletter",
        "academia": "https://elrincondelhacker.es/",
    }
    _GO_BOTS = ("bot", "crawl", "spider", "curl", "wget", "python-requests", "headless", "preview", "monitor", "facebookexternalhit")

    @pages_router.get("/go/{destino}", include_in_schema=False)
    def go_externo(destino: str, request: Request, o: str = "footer"):
        base = _GO_DESTINOS.get(destino)
        if not base:
            raise HTTPException(status_code=404)
        origen = re.sub(r"[^a-z0-9-]", "", (o or "").lower())[:30] or "footer"
        ua = request.headers.get("user-agent", "")
        if ua and not any(b in ua.lower() for b in _GO_BOTS):
            try:
                ip = request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "")
                day = datetime.utcnow().strftime("%Y-%m-%d")
                visitor = hashlib.sha256(f"{os.environ.get('SECRET_KEY', 'dockerlabs')}|{ip}|{ua}|{day}".encode()).hexdigest()[:16]
                db.session.add(OutboundClickLog(destino=destino, origen=origen, visitor=visitor))
                db.session.commit()
            except Exception:
                db.session.rollback()   # el recuento nunca debe impedir la redirección
        qs = urlencode({"utm_source": "dockerlabs", "utm_medium": origen, "utm_campaign": destino})
        return RedirectResponse(f"{base}?{qs}", status_code=302, headers={"Cache-Control": "no-store"})

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

        # La fecha no guarda hora: a igualdad de dia, el id (orden de subida) desempata
        maquinas_con_fecha.sort(key=lambda x: (x[1], x[0]["id"]), reverse=True)
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

        current_username = session.get("username")
        profile_image_url = get_fastapi_profile_image_url(username=current_username, user_id=user_id)

        user = User.query.get(user_id) if user_id else None

        session_data = {"user_id": user_id, "username": current_username, "role": role}

        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = secrets.token_urlsafe(32)
            session["csrf_token"] = csrf_token

        # Perfil público (`/u/<slug>`). El slug lo mantiene dockerlabs/slugs.py;
        # el username es el alias que acepta el endpoint si aún no hubiera slug.
        perfil_slug = (user.slug if user and user.slug else current_username) or ""
        perfil_path = f"/u/{quote(perfil_slug, safe='')}"
        perfil_web_path = f"/perfil/{quote(perfil_slug, safe='')}"
        perfil_publico = bool(user.perfil_publico) if user else True

        # Un cert_id real del usuario para que los enlaces de ejemplo de la API
        # se puedan copiar y pegar tal cual. Si no tiene ninguno, se omiten.
        cert = Certificate.query.filter_by(user_id=user_id).first() if user_id else None
        perfil_cert_id = cert.cert_id if cert else None

        # Sección "Tokens de API": solo se calcula (y solo se pinta en la
        # plantilla) para admins. Nunca se envía el token en claro; solo lo
        # que ya vive en BD (label, prefijo, fechas).
        api_tokens = []
        if role == "admin":
            api_tokens = ApiToken.query.order_by(ApiToken.created_at.desc()).all()

        context = {
            "request": request,
            "profile_image_url": profile_image_url,
            "perfil_slug": perfil_slug,
            "perfil_path": perfil_path,
            "perfil_url": f"https://dockerlabs.es{perfil_path}",
            "perfil_web_path": perfil_web_path,
            "perfil_web_url": f"https://dockerlabs.es{perfil_web_path}",
            "perfil_publico": perfil_publico,
            "perfil_cert_id": perfil_cert_id,
            "api_tokens": api_tokens,
            "user": user,
            "current_user_role": role,
            "session": session_data,
            "csrf_token_value": csrf_token,
            "get_profile_image_url": get_fastapi_profile_image_url,
            "url_for": url_for,
            # El nonce debe ser el que el middleware puso en la cabecera CSP,
            # no uno nuevo, o el script inline no casaría con la política.
            "g": {"csp_nonce": getattr(request.state, "csp_nonce", "")},
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

    def _anonymous_csrf_token(session):
        """Token CSRF para un GET de login/register/recover.

        Si ya hay una sesión (con `_id`), `get_session()` ya calculó el token
        real (determinista, HMAC del `_id`) en `session['csrf_token']` y se
        reutiliza tal cual. Si no hay sesión todavía, se crea una nueva con
        un `_id` fijado de antemano para poder calcular aquí mismo ese mismo
        token — antes se generaba un token aleatorio sin relación alguna con
        el que `verify_csrf_token` acaba comprobando, así que el formulario
        nunca podía validarse con el token que el usuario veía.

        Devuelve (csrf_token, cookie_val_o_None). cookie_val es None cuando
        se reutiliza la sesión existente y no hace falta reescribir la cookie.
        """
        csrf_token = session.get("csrf_token")
        if csrf_token:
            return csrf_token, None

        import hashlib
        import os
        new_id = hashlib.sha512(os.urandom(24)).hexdigest()
        csrf_token = compute_csrf_token(new_id)
        cookie_val = create_session_cookie(
            session.get("user_id") or 0,
            session.get("username") or "",
            session.get("role") or "jugador",
            existing_session=session,
            _id=new_id,
        )
        return csrf_token, cookie_val

    @pages_router.get("/login", response_class=HTMLResponse)
    def login_page(request: Request, session: dict = Depends(get_session)):
        user_id = session.get("user_id")
        if user_id:
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token, cookie_val = _anonymous_csrf_token(session)

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
        if cookie_val:
            response.set_cookie(key="session", value=cookie_val, httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.get("/register", response_class=HTMLResponse)
    def register_page(request: Request, session: dict = Depends(get_session)):
        if session.get("user_id"):
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token, cookie_val = _anonymous_csrf_token(session)

        context = {
            "remaining": request.query_params.get("remaining"),
            "session": {},
            "csrf_token_value": csrf_token,
            "url_for": url_for,
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        response = templates.TemplateResponse(request, "dockerlabs/auth/register.html", context)
        if cookie_val:
            response.set_cookie(key="session", value=cookie_val, httponly=True, secure=True, path="/", samesite="lax")
        return response

    @pages_router.get("/recover", response_class=HTMLResponse)
    def recover_page(request: Request, session: dict = Depends(get_session)):
        if session.get("user_id"):
            return RedirectResponse(url="/dashboard", status_code=302)

        csrf_token, cookie_val = _anonymous_csrf_token(session)

        context = {"session": {}, "csrf_token_value": csrf_token, "url_for": url_for, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        response = templates.TemplateResponse(request, "dockerlabs/auth/recover.html", context)
        if cookie_val:
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

    @pages_router.get("/confirm-email-change", response_class=HTMLResponse)
    def confirm_email_change_page(request: Request, session: dict = Depends(get_session), token: str = ""):
        error = None
        success = False
        new_email = ""
        changed_user_id = None

        if not token:
            error = "Enlace invalido."
        else:
            change_tok = EmailChangeToken.query.filter_by(token=token, used=False).first()
            if not change_tok:
                error = "Enlace invalido o ya utilizado."
            elif datetime.utcnow() > change_tok.expires_at:
                error = "El enlace ha expirado. Solicita el cambio de correo de nuevo desde tu perfil."
            else:
                existing = User.query.filter(
                    User.email == change_tok.new_email, User.id != change_tok.user_id
                ).first()
                if existing:
                    error = "Ese correo ya esta registrado por otra cuenta."
                else:
                    user_obj = User.query.get(change_tok.user_id)
                    if not user_obj:
                        error = "Usuario no encontrado."
                    else:
                        user_obj.email = change_tok.new_email
                        # Invalida el resto de sesiones abiertas, igual que un
                        # cambio de contraseña: el email es tan sensible como
                        # ella (es la vía de "olvidé mi contraseña").
                        user_obj.session_version = (user_obj.session_version or 1) + 1
                        change_tok.used = True
                        db.session.commit()
                        success = True
                        new_email = user_obj.email
                        changed_user_id = user_obj.id

        context = {
            "request": request,
            "success": success,
            "error": error,
            "new_email": new_email,
            "url_for": url_for,
            "session": {},
            "current_user_role": "",
            "g": {"csp_nonce": secrets.token_urlsafe(32)},
        }
        response = templates.TemplateResponse(request, "dockerlabs/auth/confirm_email_change.html", context)

        # Si quien confirma es la misma sesión que lo solicitó, se refresca su
        # cookie con el session_version nuevo para que no quede ella misma
        # deslogueada por el cambio que acaba de hacer a propósito.
        if success and session.get("user_id") == changed_user_id:
            cookie_val = create_session_cookie(
                changed_user_id,
                session.get("username") or "",
                session.get("role") or "jugador",
                existing_session=session,
                _id=session.get("_id"),
                session_version=User.query.get(changed_user_id).session_version,
            )
            response.set_cookie(key="session", value=cookie_val, httponly=True, secure=True, path="/", samesite="lax")

        return response

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


