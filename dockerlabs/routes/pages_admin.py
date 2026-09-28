import math
from datetime import datetime, timedelta

import secrets
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_

from dockerlabs.models import (Category, Certificate, CertificateRequestLog,
    CompletedMachine, Machine, MachineDownloadLog, PendingMachineSubmission,
    Rating, User, Writeup, PageVisitLog, OutboundClickLog)


def _parse_date_flexible(date_str: str):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unable to parse date: {date_str}")


def _distribution_by_year(items, date_fn):
    years = {}
    for item in items:
        year = date_fn(item).year
        years[year] = years.get(year, 0) + 1
    return years


def _distribution_by_month(items, date_fn):
    months = {}
    for item in items:
        d = date_fn(item)
        key = f"{d.year}-{d.month:02d}"
        months[key] = months.get(key, 0) + 1
    return months


def _distribution_by_field(items, field: str):
    dist = {}
    for item in items:
        val = getattr(item, field, None)
        if val:
            dist[val] = dist.get(val, 0) + 1
    return dist


def _bucket_granularity(start: datetime, end: datetime):
    """Elige la granularidad del eje temporal de forma inteligente según cuánto
    dure el rango: días (<=5 semanas), semanas (<=6 meses) o meses (más largo)."""
    span = (end - start).days
    if span <= 35:
        return "day"
    if span <= 183:
        return "week"
    return "month"


def _bucketize(items, date_fn, start, end):
    """Agrupa `items` en buckets ordenados (con huecos rellenos a 0) usando la
    granularidad automática del rango. Claves: 'YYYY-MM-DD' (day),
    'YYYY-Www' con inicio ISO (week) o 'YYYY-MM' (month)."""
    granularity = _bucket_granularity(start, end)

    if granularity == "day":
        keys = []
        day = datetime(start.year, start.month, start.day)
        last = datetime(end.year, end.month, end.day)
        while day <= last:
            keys.append(day.strftime("%Y-%m-%d"))
            day += timedelta(days=1)
    elif granularity == "week":
        keys = []
        wk = datetime(start.year, start.month, start.day) - timedelta(days=datetime(start.year, start.month, start.day).weekday())
        last = datetime(end.year, end.month, end.day)
        while wk <= last:
            keys.append(f"{wk.year}-W{wk.isocalendar()[1]:02d}")
            wk += timedelta(days=7)
    else:
        keys = []
        label = datetime(start.year, start.month, 1)
        while label <= datetime(end.year, end.month, 1):
            keys.append(label.strftime("%Y-%m"))
            label = datetime(label.year + (1 if label.month == 12 else 0), (label.month % 12) + 1, 1)

    counts = {k: 0 for k in keys}
    for item in items:
        d = date_fn(item)
        if not d or not (start <= d <= end):
            continue
        if granularity == "day":
            key = d.strftime("%Y-%m-%d")
        elif granularity == "week":
            key = f"{d.year}-W{d.isocalendar()[1]:02d}"
        else:
            key = d.strftime("%Y-%m")
        if key in counts:
            counts[key] += 1
    return counts


def _bucketize_unique(items, date_fn, key_fn, start, end):
    """Como _bucketize pero cuenta valores distintos de `key_fn` por bucket."""
    base = _bucketize(items, date_fn, start, end)
    granularity = _bucket_granularity(start, end)
    seen = {k: set() for k in base}
    for item in items:
        d = date_fn(item)
        if not d or not (start <= d <= end):
            continue
        if granularity == "day":
            key = d.strftime("%Y-%m-%d")
        elif granularity == "week":
            key = f"{d.year}-W{d.isocalendar()[1]:02d}"
        else:
            key = d.strftime("%Y-%m")
        if key in seen:
            seen[key].add(key_fn(item))
    return {k: len(v) for k, v in seen.items()}


def _parse_iso_date(value: str):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _resolve_range(rango: str, desde: str, hasta: str, visible_min: datetime):
    """Resuelve un rango de fechas [start, end] (datetime naive, UTC) a partir
    del preseleccionador `rango` + rango personalizado (desde/hasta).

    Devuelve un dict con start, end (inclusive), label (título para el gráfico)
    y un booleano `empty` indicando si el rango no cruza datos visibles."""
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)

    def end_of_day(d):
        return datetime(d.year, d.month, d.day, 23, 59, 59)

    start = end = None
    label = ""

    if rango == "hoy":
        start, end, label = today, end_of_day(today), f"de hoy ({today.day:02d}/{today.month:02d}/{today.year})"
    elif rango == "semana":
        start = today - timedelta(days=today.weekday())
        end, label = end_of_day(today), "de esta semana"
    elif rango == "semana_anterior":
        # Semana natural pasada (lunes a domingo anteriores)
        this_monday = today - timedelta(days=today.weekday())
        start = this_monday - timedelta(days=7)
        end, label = end_of_day(this_monday - timedelta(days=1)), "de la semana pasada"
    elif rango == "mes":
        start, end, label = datetime(today.year, today.month, 1), end_of_day(today), "de este mes"
    elif rango == "mes_anterior":
        if today.month == 1:
            prev_year, prev_month = today.year - 1, 12
        else:
            prev_year, prev_month = today.year, today.month - 1
        start = datetime(prev_year, prev_month, 1)
        nxt = datetime(prev_year + (1 if prev_month == 12 else 0), (prev_month % 12) + 1, 1)
        end, label = end_of_day(nxt - timedelta(days=1)), f"de {prev_month:02d}/{prev_year}"
    elif rango == "7d":
        start, end, label = today - timedelta(days=6), end_of_day(today), "de los últimos 7 días"
    elif rango == "30d":
        start, end, label = today - timedelta(days=29), end_of_day(today), "de los últimos 30 días"
    elif rango == "90d":
        start, end, label = today - timedelta(days=89), end_of_day(today), "de los últimos 90 días"
    elif rango == "anio":
        start, end, label = datetime(today.year, 1, 1), end_of_day(today), f"de {today.year}"
    elif rango == "todo":
        start, end, label = datetime(2000, 1, 1), end_of_day(today), "histórico"
    elif rango == "personalizado":
        s = _parse_iso_date(desde) if desde else None
        e = _parse_iso_date(hasta) if hasta else None
        if not s or not e or e < s:
            rango, start, end, label = "mes", datetime(today.year, today.month, 1), end_of_day(today), "de este mes"
        else:
            start, end = s, end_of_day(e)
            label = f"de {s.day:02d}/{s.month:02d}/{s.year} a {e.day:02d}/{e.month:02d}/{e.year}"
    else:
        start, end, label = datetime(today.year, today.month, 1), end_of_day(today), "de este mes"

    empty = bool(visible_min) and end < visible_min
    return {
        "rango": rango,
        "start": start,
        "end": end,
        "label": label,
        "empty": empty,
        "granularity": _bucket_granularity(start, end),
    }


def _smart_presets(visible_min: datetime, active: str):
    """Construye la lista de presets de filtro disponibles. Un preset con ventana
    [s, e] queda 'disabled' si termina antes del primer dato visible (e <
    visible_min): ofrecerlo solo mostraría un gráfico vacío. Si aún no hay
    registros temporales, todos quedan habilitados para uso futuro."""
    now = datetime.utcnow()
    today = datetime(now.year, now.month, now.day)
    this_monday = today - timedelta(days=today.weekday())
    prev_sunday = this_monday - timedelta(days=1)

    if now.month == 1:
        prev_ym = (now.year - 1, 12)
    else:
        prev_ym = (now.year, now.month - 1)
    prev_month_end = datetime(prev_ym[0], prev_ym[1] + 1, 1) - timedelta(days=1)
    if prev_ym[1] == 12:
        prev_month_end = datetime(prev_ym[0], 12, 31)

    def disabled(end):
        # Deshabilitar si la ventana acaba antes del primer dato visible
        return bool(visible_min) and end < visible_min.date()

    def daykey(d):
        return d.date()

    return [
        {"key": "hoy",              "label": "Hoy",                 "disabled": disabled(daykey(today))},
        {"key": "semana",           "label": "Esta semana",         "disabled": disabled(daykey(today))},
        {"key": "semana_anterior",  "label": "Semana pasada",       "disabled": disabled(daykey(prev_sunday))},
        {"key": "mes",              "label": "Este mes",            "disabled": disabled(daykey(today))},
        {"key": "mes_anterior",     "label": "Mes pasado",          "disabled": disabled(prev_month_end.date())},
        {"key": "7d",               "label": "Últimos 7 días",      "disabled": disabled(daykey(today))},
        {"key": "30d",              "label": "Últimos 30 días",     "disabled": disabled(daykey(today))},
        {"key": "90d",              "label": "Últimos 90 días",     "disabled": disabled(daykey(today))},
        {"key": "anio",             "label": f"Año {today.year}",   "disabled": disabled(daykey(today))},
        {"key": "todo",             "label": "Todo el histórico",   "disabled": disabled(daykey(today))},
        {"key": "personalizado",    "label": "Rango personalizado", "disabled": False},
    ]


def _average(values):
    values = [v for v in values if v is not None]
    return round(sum(values) / len(values), 2) if values else 0


def register_pages_admin_routes(
    pages_router,
    get_session,
    verify_csrf_token,
    require_auth_and_role,
    encode_session_cookie,
    templates,
    url_for,
    db,
):
    @pages_router.get("/instrucciones-uso", response_class=HTMLResponse)
    def instrucciones_uso_page(request: Request, session: dict = Depends(get_session)):
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/instrucciones_uso.html",
            {"url_for": url_for, "session": session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/soporte", response_class=HTMLResponse)
    def soporte_page(request: Request, session: dict = Depends(get_session)):
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request, "dockerlabs/info/soporte.html", {"url_for": url_for, "session": session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/equipo", response_class=HTMLResponse)
    def equipo_page(request: Request, session: dict = Depends(get_session)):
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request, "dockerlabs/equipo.html", {"url_for": url_for, "session": session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/enviar-maquina", response_class=HTMLResponse)
    def enviar_maquina_page(request: Request, session: dict = Depends(get_session)):
        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/enviar_maquina.html",
            {"url_for": url_for, "session": session, "current_user_role": current_user_role, "csrf_token_value": csrf_token, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/como-se-crea-una-maquina", response_class=HTMLResponse)
    def como_se_crea_page(request: Request, session: dict = Depends(get_session)):
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/como_se_crea_una_maquina.html",
            {"url_for": url_for, "session": session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/agradecimientos", response_class=HTMLResponse)
    def agradecimientos_page(request: Request, session: dict = Depends(get_session)):
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/agradecimientos.html",
            {"url_for": url_for, "session": session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/terminos-condiciones", response_class=HTMLResponse)
    def terminos_condiciones_page(request: Request, session: dict = Depends(get_session)):
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/terminos-condiciones.html",
            {"url_for": url_for, "session": session, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/bug-bounty")
    def bug_bounty_page(request: Request, session: dict = Depends(get_session)):
        return RedirectResponse(url="/", status_code=302)

    @pages_router.get("/politica-privacidad", response_class=HTMLResponse)
    def politica_privacidad_page(request: Request, session: dict = Depends(get_session)):
        return templates.TemplateResponse(
            request,
            "politicas/politica_privacidad.html",
            {"url_for": url_for, "session": session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/politica-cookies", response_class=HTMLResponse)
    def politica_cookies_page(request: Request, session: dict = Depends(get_session)):
        return templates.TemplateResponse(
            request,
            "politicas/politica_cookies.html",
            {"url_for": url_for, "session": session, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/condiciones-uso", response_class=HTMLResponse)
    def condiciones_uso_page(request: Request, session: dict = Depends(get_session)):
        return templates.TemplateResponse(
            request, "politicas/condiciones_uso.html", {"url_for": url_for, "session": session, "g": {"csp_nonce": secrets.token_urlsafe(32)}}
        )

    @pages_router.get("/gestion-usuarios", response_class=HTMLResponse)
    def gestion_usuarios_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return redirect

        page = int(request.query_params.get("page", 1))
        per_page = int(request.query_params.get("per_page", 10))
        search = request.query_params.get("search", "").strip()

        query = User.query
        if search:
            query = query.filter((User.username.ilike(f"%{search}%")) | (User.email.ilike(f"%{search}%")) | (User.role.ilike(f"%{search}%")))

        total = query.count()
        usuarios = query.order_by(User.id.asc()).offset((page - 1) * per_page).limit(per_page).all()
        total_pages = (total + per_page - 1) // per_page
        has_prev = page > 1
        has_next = page < total_pages

        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/gestion_usuarios.html",
            {
                "usuarios": usuarios,
                "session": session,
                "csrf_token_value": csrf_token,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_prev": has_prev,
                "has_next": has_next,
                "search": search,
                "url_for": url_for,
                "current_user_role": session.get("role", ""),
            },
        )

    @pages_router.get("/gestion-maquinas", response_class=HTMLResponse)
    def gestion_maquinas_page(
        request: Request,
        session: dict = Depends(get_session),
        page: int = 1,
        per_page: int = 20,
        search: str = "",
    ):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect

        current_username = session.get("username", "")
        role = session.get("role", "")

        def build_query(origen):
            query = Machine.query.filter_by(origen=origen)
            if role not in ("admin", "moderador"):
                if current_username:
                    query = query.filter_by(autor=current_username)
                else:
                    return query.filter(False)
            if search:
                search_term = f"%{search}%"
                query = query.filter(or_(Machine.nombre.ilike(search_term), Machine.autor.ilike(search_term), Machine.dificultad.ilike(search_term)))
            return query.order_by(Machine.id.asc())

        docker_query = build_query("docker")
        bunker_query = build_query("bunker")
        docker_total = docker_query.count()
        bunker_total = bunker_query.count()

        maquinas_docker = docker_query.limit(per_page).offset((page - 1) * per_page).all()
        maquinas_bunker = bunker_query.limit(per_page).offset((page - 1) * per_page).all()

        docker_pages = math.ceil(docker_total / per_page) if per_page > 0 else 1
        bunker_pages = math.ceil(bunker_total / per_page) if per_page > 0 else 1
        docker_has_prev = page > 1
        docker_has_next = page < docker_pages
        bunker_has_prev = page > 1
        bunker_has_next = page < bunker_pages

        categorias_map = {}
        if maquinas_docker:
            docker_ids = [m.id for m in maquinas_docker]
            docker_cats = Category.query.filter_by(origen="docker").filter(Category.machine_id.in_(docker_ids)).all()
            docker_lookup = {c.machine_id: c.categoria for c in docker_cats}
            for m in maquinas_docker:
                categorias_map[("docker", m.id)] = docker_lookup.get(m.id, "")

        if maquinas_bunker:
            bunker_ids = [m.id for m in maquinas_bunker]
            if bunker_ids:
                bunker_cats = Category.query.filter(Category.origen == "bunker", Category.machine_id.in_(bunker_ids)).all()
                bunker_lookup = {c.machine_id: c.categoria for c in bunker_cats}
                for m in maquinas_bunker:
                    categorias_map[("bunker", m.id)] = bunker_lookup.get(m.id, "")

        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/gestion_maquinas.html",
            {
                "maquinas_docker": maquinas_docker,
                "maquinas_bunker": maquinas_bunker,
                "categorias_map": categorias_map,
                "csrf_token_value": csrf_token,
                "page": page,
                "per_page": per_page,
                "search": search,
                "docker_total": docker_total,
                "bunker_total": bunker_total,
                "docker_pages": docker_pages,
                "bunker_pages": bunker_pages,
                "docker_has_prev": docker_has_prev,
                "docker_has_next": docker_has_next,
                "bunker_has_prev": bunker_has_prev,
                "bunker_has_next": bunker_has_next,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "session": session,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.get("/pending-machines", response_class=HTMLResponse)
    def pending_machines_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return redirect
        machines = PendingMachineSubmission.query.order_by(PendingMachineSubmission.submitted_at.desc()).all()
        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/pending.html",
            {"machines": machines, "session": session, "url_for": url_for, "current_user_role": current_user_role, "csrf_token_value": csrf_token, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/user-pending", response_class=HTMLResponse)
    def user_pending_page(request: Request, session: dict = Depends(get_session)):
        user_id = session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/auth/user-pending.html",
            {"username": session.get("username"), "session": session, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )


    @pages_router.get("/writeups-analisis", response_class=HTMLResponse)
    def writeups_analisis_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return redirect
        user = User.query.get(session.get("user_id")) if session.get("user_id") else None
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_analisis.html",
            {"user": user, "session": session, "csrf_token_value": csrf_token, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/writeups-recibidos", response_class=HTMLResponse)
    def writeups_recibidos_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect
        user = User.query.get(session.get("user_id")) if session.get("user_id") else None
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_recibidos.html",
            {"session": session, "user": user, "csrf_token_value": csrf_token, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/writeups-publicados", response_class=HTMLResponse)
    def writeups_publicados_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect
        user = User.query.get(session.get("user_id")) if session.get("user_id") else None
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_publicados.html",
            {"user": user, "session": session, "csrf_token_value": csrf_token, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @pages_router.get("/estadisticas", response_class=HTMLResponse)
    def estadisticas_page(
        request: Request,
        rango: str = "mes",
        desde: str = "",
        hasta: str = "",
        session: dict = Depends(get_session),
    ):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return redirect

        now = datetime.utcnow()
        month_start = datetime(now.year, now.month, 1)

        machines = Machine.query.all()
        writeups = Writeup.query.all()
        users = User.query.all()
        certificates = Certificate.query.all()
        completed = CompletedMachine.query.all()
        ratings = Rating.query.all()
        pending_submissions = PendingMachineSubmission.query.all()

        downloads_all = MachineDownloadLog.query.all()
        visits_all = PageVisitLog.query.all()
        outbound_all = OutboundClickLog.query.all()
        cert_requests_all = CertificateRequestLog.query.all()

        # Primer dato visible (para que el filtro sea inteligente: solo se
        # ofrecen presets que crucen datos reales). Si no hay registro temporal
        # aún, visible_min es None y se ofrecen todos los presets.
        dl_dates = [d.created_at for d in downloads_all if d.created_at]
        cr_dates = [c.created_at for c in cert_requests_all if c.created_at]
        vi_dates = [v.created_at for v in visits_all if v.created_at]
        ob_dates = [o.created_at for o in outbound_all if o.created_at]
        all_dates = dl_dates + cr_dates + vi_dates + ob_dates
        visible_min = min(all_dates) if all_dates else None

        resolved = _resolve_range(rango, desde, hasta, visible_min)
        start, end, active_rango = resolved["start"], resolved["end"], resolved["rango"]
        filtro_label = resolved["label"]

        downloads_filtered = [d for d in downloads_all if d.created_at and start <= d.created_at <= end]
        cert_requests_filtered = [c for c in cert_requests_all if c.created_at and start <= c.created_at <= end]

        visits_filtered = [v for v in visits_all if v.created_at and start <= v.created_at <= end]
        today_str = now.strftime("%Y-%m-%d")
        visits_today = [v for v in visits_all if v.created_at and v.created_at.strftime("%Y-%m-%d") == today_str]
        visit_stats = {
            "total_en_rango": len(visits_filtered),
            "hoy": len(visits_today),
            "unicos_hoy": len({v.visitor for v in visits_today}),
            "by_day": _bucketize(visits_filtered, lambda v: v.created_at, start, end),
            "unique_by_day": _bucketize_unique(visits_filtered, lambda v: v.created_at, lambda v: v.visitor, start, end),
            "since": min(vi_dates).strftime("%d/%m/%Y") if vi_dates else None,
        }

        ob_filtered = [o for o in outbound_all if o.created_at and start <= o.created_at <= end]
        _by = {}
        for o in ob_filtered:
            _by.setdefault((o.destino, o.origen), []).append(o)
        outbound_stats = {
            "total_en_rango": len(ob_filtered),
            "unicos_en_rango": len({o.visitor for o in ob_filtered}),
            "newsletter": len([o for o in ob_filtered if o.destino == "newsletter"]),
            "academia": len([o for o in ob_filtered if o.destino == "academia"]),
            "newsletter_by_day": _bucketize([o for o in ob_filtered if o.destino == "newsletter"], lambda o: o.created_at, start, end),
            "academia_by_day": _bucketize([o for o in ob_filtered if o.destino == "academia"], lambda o: o.created_at, start, end),
            "por_origen": [{"destino": d, "origen": og, "clics": len(v), "unicos": len({x.visitor for x in v})}
                           for (d, og), v in sorted(_by.items(), key=lambda kv: -len(kv[1]))],
            "since": min(ob_dates).strftime("%d/%m/%Y") if ob_dates else None,
        }

        filtro = {
            "active": active_rango,
            "desde": desde,
            "hasta": hasta,
            "label": filtro_label,
            "total_descargas": len(downloads_filtered),
            "total_certificados": len(cert_requests_filtered),
            "presets": _smart_presets(visible_min, active_rango),
            "granularity": _bucket_granularity(start, end),
            "visible_since": visible_min.strftime("%d/%m/%Y") if visible_min else None,
            "empty": resolved["empty"],
        }

        machine_stats = {
            "total": len(machines),
            "by_dificultad": _distribution_by_field(machines, "dificultad"),
            "by_origen": _distribution_by_field(machines, "origen"),
            "by_year": _distribution_by_year(machines, lambda m: _parse_date_flexible(m.fecha)),
            "by_month": _distribution_by_month(machines, lambda m: _parse_date_flexible(m.fecha)),
        }

        # Writeups por máquina. Writeup.maquina es texto libre (no FK), así que
        # se cruza por nombre normalizado. Se parte de la lista de máquinas para
        # que las que tienen 0 writeups también entren en "menos writeups"; los
        # writeups de máquinas que ya no existen se ignoran.
        _norm = lambda v: (v or "").strip().lower()
        writeups_count = {}
        for w in writeups:
            k = _norm(w.maquina)
            writeups_count[k] = writeups_count.get(k, 0) + 1
        # Solo máquinas de DockerLabs: las de BunkerLabs (origen "bunker") no cuentan.
        machine_writeups = [(m, writeups_count.get(_norm(m.nombre), 0))
                            for m in machines if m.origen == "docker"]
        # Empates (habrá muchos a 0): la máquina más reciente (id mayor) primero.
        top_writeups = sorted(machine_writeups, key=lambda t: (-t[1], -t[0].id))[:5]
        bottom_writeups = sorted(machine_writeups, key=lambda t: (t[1], -t[0].id))[:5]

        writeup_stats = {
            "total": len(writeups),
            "top_machines": {
                "labels": [m.nombre for m, _ in top_writeups],
                "values": [n for _, n in top_writeups],
            },
            "bottom_machines": {
                "labels": [m.nombre for m, _ in bottom_writeups],
                "values": [n for _, n in bottom_writeups],
            },
            "by_tipo": _distribution_by_field(writeups, "tipo"),
            "by_year": _distribution_by_year(writeups, lambda w: w.created_at),
            "by_month": _distribution_by_month(writeups, lambda w: w.created_at),
        }

        user_stats = {
            "total": len(users),
            "by_role": _distribution_by_field(users, "role"),
            "by_year": _distribution_by_year(users, lambda u: u.created_at),
            "by_month": _distribution_by_month(users, lambda u: u.created_at),
        }

        top_machines = sorted(machines, key=lambda m: m.descargas or 0, reverse=True)[:5]
        # Menos descargadas: orden ascendente; a igualdad de descargas, la más
        # reciente (id mayor) primero, para que el desempate sea estable.
        bottom_machines = sorted(machines, key=lambda m: (m.descargas or 0, -m.id))[:5]
        download_stats = {
            "total": sum(m.descargas or 0 for m in machines),
            "mes_actual": len([d for d in downloads_all if d.created_at and d.created_at >= month_start]),
            "rango_label": filtro_label,
            "total_en_rango": len(downloads_filtered),
            "by_day": _bucketize(downloads_filtered, lambda d: d.created_at, start, end),
            # Listas paralelas (no dict): tojson ordena las claves alfabéticamente
            # y rompería el orden del ranking.
            "top_machines": {
                "labels": [m.nombre for m in top_machines],
                "values": [m.descargas or 0 for m in top_machines],
            },
            "bottom_machines": {
                "labels": [m.nombre for m in bottom_machines],
                "values": [m.descargas or 0 for m in bottom_machines],
            },
        }

        certificate_stats = {
            "total": len(certificates),
            "by_year": _distribution_by_year(certificates, lambda c: c.created_at),
            "by_month": _distribution_by_month(certificates, lambda c: c.created_at),
            "solicitudes_mes_actual": len([c for c in cert_requests_all if c.created_at and c.created_at >= month_start]),
            "solicitudes_en_rango": len(cert_requests_filtered),
            "solicitudes_by_day": _bucketize(cert_requests_filtered, lambda r: r.created_at, start, end),
        }

        completed_stats = {
            "total": len(completed),
            "by_year": _distribution_by_year(completed, lambda c: c.completed_at),
            "by_month": _distribution_by_month(completed, lambda c: c.completed_at),
        }

        rating_stats = {
            "total": len(ratings),
            "avg_dificultad": _average([r.dificultad_score for r in ratings]),
            "avg_aprendizaje": _average([r.aprendizaje_score for r in ratings]),
            "avg_recomendaria": _average([r.recomendaria_score for r in ratings]),
            "avg_diversion": _average([r.diversion_score for r in ratings]),
        }

        pending_stats = {
            "total": len(pending_submissions),
            "by_estado": _distribution_by_field(pending_submissions, "estado"),
            "by_year": _distribution_by_year(pending_submissions, lambda p: p.submitted_at),
            "by_month": _distribution_by_month(pending_submissions, lambda p: p.submitted_at),
        }

        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/estadisticas.html",
            {
                "machine_stats": machine_stats,
                "writeup_stats": writeup_stats,
                "user_stats": user_stats,
                "download_stats": download_stats,
                "visit_stats": visit_stats,
                "outbound_stats": outbound_stats,
                "certificate_stats": certificate_stats,
                "completed_stats": completed_stats,
                "rating_stats": rating_stats,
                "pending_stats": pending_stats,
                "filtro": filtro,
                "session": session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )
