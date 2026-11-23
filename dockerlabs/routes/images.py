import io
import os
import re

from fastapi import HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from werkzeug.utils import secure_filename

from dockerlabs.database import db_session
from dockerlabs.models import Machine, User
from dockerlabs.extensions import db


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
            candidates_names = [username, username.lower(), secure_filename(username), secure_filename(username).lower()]
            candidates_names = list(dict.fromkeys(candidates_names))
            for name in candidates_names:
                for ext in allowed_profile_extensions:
                    candidate = os.path.join(profile_upload_folder, f"{name}{ext}")
                    if os.path.exists(candidate):
                        return f"dockerlabs/images/perfiles/{name}{ext}"
            return default_image

        # Clean up any stale session from a previous request on this thread
        db_session.remove()

        try:
            user = db.session.get(User, user_id)
        except Exception:
            db_session.remove()
            user = None

        if user:
            # 1. Primero buscar en el nuevo sistema (uploads/perfiles)
            if user.profile_image_path:
                try:
                    full_path = os.path.join(base_dir, user.profile_image_path)
                    if os.path.exists(full_path):
                        mime = user.profile_image_mime or "image/jpeg"
                        return FileResponse(full_path, media_type=mime, headers={"Cache-Control": "public, max-age=3600"})
                except Exception:
                    pass
            
            # 2. Si no existe en nuevo sistema, buscar en BD antigua (compatibilidad)
            try:
                image_data = user.profile_image_data
                if image_data:
                    mime = user.profile_image_mime or "image/jpeg"
                    return StreamingResponse(io.BytesIO(image_data), media_type=mime, headers={"Cache-Control": "public, max-age=3600"})
            except Exception:
                pass

            # 2.5. Buscar en uploads/perfiles/ por patrón user_{id}_*.ext
            perfiles_dir = os.path.join(base_dir, "uploads", "perfiles")
            if os.path.isdir(perfiles_dir):
                _mime_map = {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png', '.gif': 'image/gif', '.webp': 'image/webp'}
                for fname in sorted(os.listdir(perfiles_dir), reverse=True):
                    if re.match(rf"user_{user_id}_\d+\.\w+$", fname):
                        full_path = os.path.join(perfiles_dir, fname)
                        ext = os.path.splitext(fname)[1].lower()
                        mime = _mime_map.get(ext, 'image/jpeg')
                        return FileResponse(full_path, media_type=mime, headers={"Cache-Control": "public, max-age=3600"})

        # 3. Si no existe en ninguno, buscar en disco estático (fallback)
        disk_path = get_profile_image_static_path(user.username if user else None, uid=user_id)
        if disk_path and disk_path != default_image:
            full_path = os.path.join(base_dir, "static", disk_path)
            if os.path.exists(full_path):
                return FileResponse(full_path, headers={"Cache-Control": "public, max-age=3600"})

        # 4. Imagen por defecto
        default_path = os.path.join(base_dir, "static", default_image)
        if os.path.exists(default_path):
            return FileResponse(default_path)
        raise HTTPException(status_code=404, detail="Imagen no encontrada")

    _LADOS_MINIATURA = (64, 96, 128)

    def _miniatura_logo(base_dir: str, logo_path: str, lado: int):
        """Miniatura WebP del logo, cacheada en disco (uploads/logos/thumbs).

        El nombre del logo lleva la marca de tiempo de su subida, así que cada
        logo nuevo genera una miniatura nueva y la antigua nunca queda desfasada.
        Devuelve la ruta o None si no se pudo generar (se sirve el original).
        """
        nombre = os.path.basename(logo_path or "")
        origen = os.path.join(base_dir, "uploads", "logos", nombre)
        if not nombre or not os.path.isfile(origen):
            return None
        carpeta = os.path.join(base_dir, "uploads", "logos", "thumbs")
        destino = os.path.join(carpeta, f"{os.path.splitext(nombre)[0]}_{lado}.webp")
        if os.path.isfile(destino):
            return destino
        try:
            from PIL import Image
            os.makedirs(carpeta, exist_ok=True)
            with Image.open(origen) as im:
                if im.mode not in ("RGB", "RGBA"):
                    im = im.convert("RGBA")
                im.thumbnail((lado, lado))
                temporal = f"{destino}.{os.getpid()}.tmp"
                im.save(temporal, "WEBP", quality=82, method=4)
            os.replace(temporal, destino)   # atómico: dos peticiones a la vez no se pisan
            return destino
        except Exception:
            return None

    def _serve_machine_logo_logic(machine_id: int, lado: int = 0, version: str = ""):

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

        # Clean up any stale session from a previous request on this thread
        db_session.remove()

        try:
            machine = db.session.get(Machine, machine_id)
        except Exception:
            db_session.remove()
            machine = None

        if machine:
            # 1. Primero buscar en el nuevo sistema (uploads/logos)
            if machine.logo_path:
                try:
                    full_path = os.path.join(base_dir, machine.logo_path)
                    if os.path.exists(full_path):
                        # Con ?v=<nombre del fichero> la URL cambia en cada subida: se puede
                        # cachear un año. Sin versión se mantiene la revalidación de siempre.
                        inmutable = bool(version) and version == os.path.basename(machine.logo_path)
                        cache = "public, max-age=31536000, immutable" if inmutable else "no-cache"
                        if lado in _LADOS_MINIATURA:
                            mini = _miniatura_logo(base_dir, machine.logo_path, lado)
                            if mini:
                                return FileResponse(mini, media_type="image/webp", headers={"Cache-Control": cache})
                        mime = machine.logo_mime or "image/jpeg"
                        return FileResponse(full_path, media_type=mime, headers={"Cache-Control": cache})
                except Exception:
                    pass

            # 2. Si no existe en nuevo sistema, buscar en BD antigua (compatibilidad)
            try:
                logo_data = machine.logo_data
                if logo_data:
                    mime = machine.logo_mime or "image/jpeg"
                    return StreamingResponse(io.BytesIO(logo_data), media_type=mime, headers={"Cache-Control": "no-cache"})
            except Exception:
                pass

        # 3. Si no existe en ninguno, buscar en disco estático (fallback)
        if machine and machine.imagen:
            full_path = os.path.join(base_dir, "static", machine.imagen)
            if os.path.exists(full_path):
                return FileResponse(full_path, headers={"Cache-Control": "no-cache"})

        # 4. Logo por defecto
        default_logo = os.path.join(base_dir, "static", "dockerlabs", "images", "logos", "logo.png")
        if os.path.exists(default_logo):
            return FileResponse(default_logo)
        raise HTTPException(status_code=404, detail="Logo no encontrado")

    @pages_router.get("/img/perfil/{user_id}")
    def serve_profile_image(user_id: int):
        return _serve_profile_image_logic(user_id)

    @pages_router.get("/img/maquina/{machine_id}")
    def serve_machine_logo(machine_id: int, s: int = 0, v: str = ""):
        return _serve_machine_logo_logic(machine_id, s, v)

