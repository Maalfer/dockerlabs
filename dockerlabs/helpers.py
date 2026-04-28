"""
Helper functions para reducir duplicación de templates
"""

from flask import render_template

def render_403_error():
    """Renderiza el template de error 403"""
    return render_template('dockerlabs/errors/403.html'), 403

def render_404_error():
    """Renderiza el template de error 404"""
    return render_template('dockerlabs/errors/404.html'), 404
