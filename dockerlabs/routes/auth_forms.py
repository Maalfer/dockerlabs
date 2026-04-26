import re

from fastapi import Depends, Form, Request
from fastapi.responses import RedirectResponse

from dockerlabs.models import UsernameChangeRequest as UCR


def register_auth_form_routes(pages_router, get_flask_session, verify_csrf_token, set_flask_session_cookie, alchemy_db):
    @pages_router.post("/request_username_change")
    async def form_request_username_change(
        request: Request,
        requested_username: str = Form(...),
        reason: str = Form(""),
        contacto_opcional: str = Form(""),
        flask_session: dict = Depends(get_flask_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """
        Versión form-based de solicitud de cambio de nombre.
        Equivalente a POST /request_username_change en auth.py (Flask).
        Redirige con mensaje flash en la sesión.
        """
        user_id = flask_session.get("user_id")
        old_username = (flask_session.get("username") or "").strip()

        def redirect_with_flash(msg: str, category: str = "danger"):
            flask_session["_flashes"] = [(category, msg)]
            cookie = set_flask_session_cookie(flask_session)
            resp = RedirectResponse(url="/dashboard", status_code=302)
            resp.set_cookie("session", cookie, httponly=True, path="/", samesite="lax")
            return resp

        if not user_id:
            return redirect_with_flash("Debes iniciar sesión para solicitar un cambio de nombre.", "warning")

        requested_username = requested_username.strip()
        if not requested_username:
            return redirect_with_flash("Debes proporcionar un nuevo nombre de usuario.")

        if not re.match(r"^[a-zA-Z0-9_-]{3,20}$", requested_username):
            return redirect_with_flash(
                "El nombre debe tener entre 3 y 20 caracteres y solo letras, números, guiones y guiones bajos."
            )

        existing = UCR.query.filter_by(user_id=user_id, estado="pendiente").first()
        if existing:
            return redirect_with_flash("Ya tienes una solicitud de cambio de nombre pendiente.", "warning")

        try:
            new_req = UCR(
                user_id=user_id,
                old_username=old_username,
                requested_username=requested_username,
                reason=(reason or "").strip(),
                contacto_opcional=(contacto_opcional or "").strip(),
                estado="pendiente",
            )
            alchemy_db.session.add(new_req)
            alchemy_db.session.commit()
            return redirect_with_flash("Solicitud enviada correctamente. El equipo de administración la revisará pronto.", "success")
        except Exception as e:
            alchemy_db.session.rollback()
            return redirect_with_flash(f"Error al enviar la solicitud: {str(e)}")

