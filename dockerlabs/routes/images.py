import io
import os

from fastapi import HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from dockerlabs.models import Machine, User

limiter = None

def configure_limiter(global_limiter):
    """Configura el limiter global desde asgi.py"""
    global limiter
    limiter = global_limiter


def register_image_routes(api_router, pages_router):
    def _serve_profile_image_logic(user_id: int):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        profile_upload_folder = os.path.join(base_dir, "static", "dockerlabs", "images", "perfiles")
        allowed_profile_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
        default_image = "dockerlabs/images/balu.webp"

        def get_profile_image_static_path(username, uid=None):
            if uid:
                for ext in allowed_profile_extensions:
                    candidate = os.path.join(profile_upload_folder, f"{uid}{ext}")
                    if os.path.exists(candidate):
                        return f"dockerlabs/images/perfiles/{uid}{ext}"
            if not username:
                return default_image
            if "/" in username or "\\" in username or ".." in username:
                return default_image
            from werkzeug.utils import secure_filename

            candidates_names = [username, username.lower(), secure_filename(username), secure_filename(username).lower()]
            candidates_names = list(dict.fromkeys(candidates_names))
            for name in candidates_names:
                for ext in allowed_profile_extensions:
                    candidate = os.path.join(profile_upload_folder, f"{name}{ext}")
                    if os.path.exists(candidate):
                        return f"dockerlabs/images/perfiles/{name}{ext}"
            return default_image

        user = User.query.get(user_id)
        if user:
            try:
                image_data = user.profile_image_data
                if image_data:
                    mime = user.profile_image_mime or "image/jpeg"
                    return StreamingResponse(io.BytesIO(image_data), media_type=mime, headers={"Cache-Control": "public, max-age=3600"})
            except Exception:
                pass

        disk_path = get_profile_image_static_path(user.username if user else None, uid=user_id)
        if disk_path and disk_path != default_image:
            full_path = os.path.join(base_dir, "static", disk_path)
            if os.path.exists(full_path):
                return FileResponse(full_path, headers={"Cache-Control": "public, max-age=3600"})

        default_path = os.path.join(base_dir, "static", default_image)
        if os.path.exists(default_path):
            return FileResponse(default_path)
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    def _serve_machine_logo_logic(machine_id: int):
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        machine = Machine.query.get(machine_id)

        if machine:
            try:
                logo_data = machine.logo_data
                if logo_data:
                    mime = machine.logo_mime or "image/jpeg"
                    return StreamingResponse(io.BytesIO(logo_data), media_type=mime, headers={"Cache-Control": "public, max-age=3600"})
            except Exception:
                pass

        if machine and machine.imagen:
            full_path = os.path.join(base_dir, "static", machine.imagen)
            if os.path.exists(full_path):
                return FileResponse(full_path, headers={"Cache-Control": "public, max-age=3600"})

        default_logo = os.path.join(base_dir, "static", "dockerlabs", "images", "logos", "logo.png")
        if os.path.exists(default_logo):
            return FileResponse(default_logo)
        raise HTTPException(status_code=404, detail="Logo no encontrado")

    @pages_router.get("/img/perfil/{user_id}")
    def serve_profile_image(user_id: int):
        return _serve_profile_image_logic(user_id)

    @pages_router.get("/img/maquina/{machine_id}")
    def serve_machine_logo(machine_id: int):
        return _serve_machine_logo_logic(machine_id)

    @api_router.get("/img/perfil/{user_id}")
    def serve_profile_image_api(request: Request, user_id: int):
        return _serve_profile_image_logic(user_id)

    @api_router.get("/img/maquina/{machine_id}")
    def serve_machine_logo_api(request: Request, machine_id: int):
        return _serve_machine_logo_logic(machine_id)

