"""Helpers de imagen de perfil de usuario."""

import os
from werkzeug.utils import secure_filename

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
PROFILE_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'dockerlabs', 'images', 'perfiles')
ALLOWED_PROFILE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}


def get_profile_image_static_path(username, user_id=None):
    """Devuelve la ruta estática de la imagen de perfil de un usuario (para disco)."""
    default_image = "dockerlabs/images/balu.webp"

    if user_id:
        for ext in ALLOWED_PROFILE_EXTENSIONS:
            candidate = os.path.join(PROFILE_UPLOAD_FOLDER, f"{user_id}{ext}")
            if os.path.exists(candidate):
                return f"dockerlabs/images/perfiles/{user_id}{ext}"

    if not username:
        return default_image

    if '/' in username or '\\' in username or '..' in username:
        return default_image

    candidates_names = [username, username.lower()]
    s_name = secure_filename(username)
    if s_name != username:
        candidates_names.append(s_name)
        candidates_names.append(s_name.lower())
    candidates_names = list(dict.fromkeys(candidates_names))

    for name in candidates_names:
        for ext in ALLOWED_PROFILE_EXTENSIONS:
            candidate = os.path.join(PROFILE_UPLOAD_FOLDER, f"{name}{ext}")
            if os.path.exists(candidate):
                return f"dockerlabs/images/perfiles/{name}{ext}"

    return default_image


def get_profile_image_url(username=None, user_id=None):
    """Devuelve la URL del endpoint /img/perfil/<id> para el usuario."""
    if user_id:
        return f'/img/perfil/{user_id}'
    if username:
        from .models import User
        user = User.query.filter_by(username=username).first()
        if user:
            return f'/img/perfil/{user.id}'
    return '/static/dockerlabs/images/balu.webp'
