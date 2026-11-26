"""Helpers de imagen de perfil de usuario."""


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
