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

@main_bp.route('/api/estadisticas')
def api_estadisticas():
    """
    API de estadísticas (JSON).
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

    from flask import jsonify

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

    return jsonify({
        'machine_stats': machine_stats,
        'writeup_stats': writeup_stats,
        'user_stats': user_stats
    })
