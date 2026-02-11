from flask import Blueprint, render_template, request, session, redirect
from flask_limiter.errors import RateLimitExceeded
from dockerlabs.models import User, Machine, Writeup
from datetime import datetime
import re
from collections import defaultdict

main_bp = Blueprint('main', __name__)

@main_bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('dockerlabs/403.html'), 403

@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('dockerlabs/404.html'), 404

@main_bp.app_errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
           
    retry_after = None
    try:
        m = re.search(r"(\d+)", str(e.description or ""))
        if m:
            retry_after = int(m.group(1))
    except Exception:
        retry_after = None

    if not retry_after:
        retry_after = 15

    session['rate_limit_remaining'] = retry_after

    return redirect(request.path)

@main_bp.route('/403.html')
def error_403_page():
    """
    Página de error 403 (Prohibido).
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Página de error 403.
    """
    return render_template('dockerlabs/403.html')

@main_bp.route('/instrucciones-uso')
def instrucciones_uso():
    """
    Página de instrucciones.
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Instrucciones.
    """
    return render_template('dockerlabs/instrucciones_uso.html')

@main_bp.route('/enviar-maquina')
def enviar_maquina():
    """
    Página enviar máquina.
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Página para enviar máquina.
    """
    return render_template('dockerlabs/enviar_maquina.html')

@main_bp.route('/como-se-crea-una-maquina')
def como_se_crea():
    """
    Página de cómo crear una máquina.
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Página de tutorial.
    """
    return render_template('dockerlabs/como_se_crea_una_maquina.html')

@main_bp.route('/agradecimientos')
def agradecimientos():
    """
    Página de agradecimientos.
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Agradecimientos.
    """
    return render_template('dockerlabs/agradecimientos.html')

@main_bp.route('/politica-privacidad')
def politica_privacidad():
    """
    Política de privacidad.
    ---
    tags:
      - Legal
    responses:
      200:
        description: Política de privacidad.
    """
    return render_template('politicas/politica_privacidad.html')

@main_bp.route('/politica-cookies')
def politica_cookies():
    """
    Política de cookies.
    ---
    tags:
      - Legal
    responses:
      200:
        description: Política de cookies.
    """
    return render_template('politicas/politica_cookies.html')

@main_bp.route('/condiciones-uso')
def condiciones_uso():
    """
    Condiciones de uso.
    ---
    tags:
      - Legal
    responses:
      200:
        description: Condiciones de uso.
    """
    return render_template('politicas/condiciones_uso.html')

@main_bp.route('/estadisticas')
def estadisticas():
    """
    Página de estadísticas.
    ---
    tags:
      - Páginas
    responses:
      200:
        description: Estadísticas de la plataforma.
    """
    # Helper to calculate percentages per year
    def get_distribution_by_year(items, date_extractor):
        year_counts = defaultdict(int)
        total = 0
        for item in items:
            try:
                year = date_extractor(item)
                if year:
                    year_counts[year] += 1
                    total += 1
            except:
                continue
        
        distribution = {}
        if total > 0:
            for year, count in year_counts.items():
                distribution[year] = round((count / total) * 100, 2)
        
        # Return sorted by year
        return dict(sorted(distribution.items()))

    # --- Machines ---
    machines = Machine.query.all()
    def machine_date_extractor(m):
        # Format is dd/mm/yyyy
        return datetime.strptime(m.fecha, "%d/%m/%Y").year

    machine_stats = get_distribution_by_year(machines, machine_date_extractor)

    # --- Writeups ---
    writeups = Writeup.query.all()
    def writeup_date_extractor(w):
        return w.created_at.year if w.created_at else None

    writeup_stats = get_distribution_by_year(writeups, writeup_date_extractor)

    # --- Users ---
    users = User.query.all()
    def user_date_extractor(u):
        return u.created_at.year if u.created_at else None

    user_stats = get_distribution_by_year(users, user_date_extractor)

    return render_template('dockerlabs/estadisticas.html', 
                         machine_stats=machine_stats,
                         writeup_stats=writeup_stats,
                         user_stats=user_stats)
