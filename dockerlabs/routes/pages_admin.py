import math
from datetime import datetime, timedelta
from urllib.parse import urlencode

import secrets
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import func, or_

from dockerlabs.models import (Category, Certificate, CertificateRequestLog,
    CompletedMachine, Machine, MachineDownloadLog, PendingMachineSubmission,
    Rating, User, Writeup, PageVisitLog, OutboundClickLog)
from dockerlabs.tiempo import utcnow


_DIFICULTADES = ("Muy Fácil", "Fácil", "Medio", "Difícil")


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


def _bucketize(items, date_fn, start, end, peso_fn=None):
    """Agrupa `items` en buckets ordenados (con huecos rellenos a 0) usando la
    granularidad automática del rango. Claves: 'YYYY-MM-DD' (day),
    'YYYY-Www' con inicio ISO (week) o 'YYYY-MM' (month). Con `peso_fn`, cada
    elemento suma su peso (filas ya agregadas por día) en vez de 1."""
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
            counts[key] += peso_fn(item) if peso_fn else 1
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
    now = utcnow()
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
    now = utcnow()
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
    @pages_router.get("/gestion-usuarios", response_class=HTMLResponse)
    def gestion_usuarios_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return redirect

        qp = request.query_params

        def entero(nombre, defecto):
            try:
                return int(qp.get(nombre, defecto))
            except (TypeError, ValueError):
                return defecto

        ORDENES = {
            "recientes": "Últimos registros",
            "antiguos": "Registros más antiguos",
            "acceso": "Último acceso (más reciente)",
            "inactivos": "Más tiempo sin entrar",
            "nombre": "Nombre (A-Z)",
        }
        PERIODOS = {"hoy": 1, "7": 7, "30": 30, "90": 90}

        per_page = min(max(entero("per_page", 25), 5), 100)
        search = (qp.get("search") or "").strip()[:100]
        orden = qp.get("orden") if qp.get("orden") in ORDENES else "recientes"
        rol = qp.get("rol") if qp.get("rol") in ("admin", "moderador", "jugador") else ""
        registro = qp.get("registro") if qp.get("registro") in PERIODOS else ""
        acceso = qp.get("acceso") if qp.get("acceso") in (*PERIODOS, "nunca") else ""

        ahora = utcnow()
        query = User.query
        if search:
            patron = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            query = query.filter(or_(
                User.username.ilike(patron, escape="\\"),
                User.email.ilike(patron, escape="\\"),
                User.role.ilike(patron, escape="\\"),
            ))
        if rol:
            query = query.filter(User.role == rol)
        if registro:
            query = query.filter(User.created_at >= ahora - timedelta(days=PERIODOS[registro]))
        if acceso == "nunca":
            query = query.filter(User.last_seen_at.is_(None))
        elif acceso:
            query = query.filter(User.last_seen_at >= ahora - timedelta(days=PERIODOS[acceso]))

        total = query.count()
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = min(max(entero("page", 1), 1), total_pages)

        # Quien no tiene último acceso registrado va siempre al final de esos dos órdenes.
        sin_acceso = User.last_seen_at.is_(None)
        criterio = {
            "recientes": (User.created_at.desc(), User.id.desc()),
            "antiguos": (User.created_at.asc(), User.id.asc()),
            "acceso": (sin_acceso.asc(), User.last_seen_at.desc(), User.id.desc()),
            "inactivos": (sin_acceso.asc(), User.last_seen_at.asc(), User.id.asc()),
            "nombre": (func.lower(User.username).asc(), User.id.asc()),
        }[orden]
        usuarios = query.order_by(*criterio).offset((page - 1) * per_page).limit(per_page).all()

        def hace(fecha):
            if not fecha:
                return ""
            seg = max(0, (ahora - fecha).total_seconds())
            if seg < 3600:
                return "hace un momento" if seg < 120 else f"hace {int(seg // 60)} min"
            if seg < 86400:
                return f"hace {int(seg // 3600)} h"
            dias = int(seg // 86400)
            if dias == 1:
                return "ayer"
            if dias < 60:
                return f"hace {dias} días"
            if dias < 730:
                return f"hace {dias // 30} meses"
            return f"hace {dias // 365} años"

        filas = [{"u": u, "registro_txt": hace(u.created_at), "acceso_txt": hace(u.last_seen_at)} for u in usuarios]

        semana = ahora - timedelta(days=7)
        resumen = {
            "total": User.query.count(),
            "nuevos": User.query.filter(User.created_at >= semana).count(),
            "activos": User.query.filter(User.last_seen_at >= semana).count(),
            "con_registro": User.query.filter(User.last_seen_at.isnot(None)).count(),
        }

        def listado_url(**cambios):
            """URL del listado conservando filtros; los valores por defecto se omiten."""
            params = {"search": search, "orden": orden, "rol": rol, "registro": registro,
                      "acceso": acceso, "per_page": per_page, "page": page}
            params.update(cambios)
            limpio = {
                k: v for k, v in params.items()
                if v not in ("", None)
                and not (k == "page" and v == 1)
                and not (k == "orden" and v == "recientes")
                and not (k == "per_page" and v == 25)
            }
            return "/gestion-usuarios" + ("?" + urlencode(limpio) if limpio else "")

        paginas, previa = [], 0
        for p in sorted({1, total_pages, *range(max(1, page - 1), min(total_pages, page + 1) + 1)}):
            if p - previa > 1:
                paginas.append(None)
            paginas.append(p)
            previa = p

        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        respuesta = templates.TemplateResponse(
            request,
            "dockerlabs/admin/gestion_usuarios.html",
            {
                "usuarios": usuarios,
                "filas": filas,
                "resumen": resumen,
                "session": session,
                "csrf_token_value": csrf_token,
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "paginas": paginas,
                "has_prev": page > 1,
                "has_next": page < total_pages,
                "inicio": (page - 1) * per_page + 1 if usuarios else 0,
                "fin": (page - 1) * per_page + len(usuarios),
                "search": search,
                "orden": orden,
                "ordenes": ORDENES,
                "rol": rol,
                "registro": registro,
                "acceso": acceso,
                "hay_filtros": bool(search or rol or registro or acceso),
                "listado_url": listado_url,
                "url_for": url_for,
                "current_user_role": session.get("role", ""),
            },
        )
        # Datos personales: que ni el navegador ni intermediarios los reutilicen sin revalidar.
        respuesta.headers["Cache-Control"] = "private, no-store"
        return respuesta

    @pages_router.get("/gestion-maquinas", response_class=HTMLResponse)
    def gestion_maquinas_page(
        request: Request,
        session: dict = Depends(get_session),
        page: int = 1,
        per_page: int = 20,
        search: str = "",
        plataforma: str = "docker",
        dificultad: str = "",
    ):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect

        current_username = session.get("username", "")
        role = session.get("role", "")

        # Parámetros saneados: una URL manipulada no debe provocar consultas enormes
        # ni listados vacíos por una plataforma o dificultad inventadas.
        search = (search or "").strip()[:100]
        plataforma = plataforma if plataforma in ("docker", "bunker") else "docker"
        dificultad = dificultad if dificultad in _DIFICULTADES else ""
        per_page = min(max(per_page, 5), 100)

        def build_query(origen):
            query = Machine.query.filter_by(origen=origen)
            if role not in ("admin", "moderador"):
                if current_username:
                    query = query.filter_by(autor=current_username)
                else:
                    return query.filter(False)
            if search:
                # Los comodines de LIKE del texto buscado se escapan: «100%» o «a_b»
                # se buscan literalmente.
                escapado = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                term = f"%{escapado}%"
                query = query.filter(or_(
                    Machine.nombre.ilike(term, escape="\\"),
                    Machine.autor.ilike(term, escape="\\"),
                    Machine.dificultad.ilike(term, escape="\\"),
                ))
            if dificultad:
                query = query.filter(Machine.dificultad == dificultad)
            return query.order_by(Machine.id.asc())

        totales = {"docker": build_query("docker").count(), "bunker": build_query("bunker").count()}
        total = totales[plataforma]
        total_pages = max(1, math.ceil(total / per_page))
        page = min(max(page, 1), total_pages)

        # Solo se lee y se pinta la plataforma activa: la otra se abre por su pestaña.
        maquinas = build_query(plataforma).limit(per_page).offset((page - 1) * per_page).all()

        ids = [m.id for m in maquinas]
        categorias = {}
        if ids:
            categorias = {
                c.machine_id: c.categoria
                for c in Category.query.filter(Category.origen == plataforma, Category.machine_id.in_(ids)).all()
            }

        # Campos largos o no editables en la tabla: viajan en un único JSON (no en
        # cientos de inputs ocultos) y el JS los reenvía tal cual al guardar.
        datos = {
            str(m.id): {
                "autor": m.autor,
                "enlace_autor": m.enlace_autor or "",
                "fecha": m.fecha or "",
                "imagen": m.imagen or "",
                "descripcion": m.descripcion or "",
                "link_descarga": m.link_descarga or "",
                "categoria": categorias.get(m.id, ""),
            }
            for m in maquinas
        }

        def listado_url(**cambios):
            """URL del listado conservando filtros; los valores por defecto se omiten."""
            params = {
                "plataforma": plataforma,
                "search": search,
                "dificultad": dificultad,
                "per_page": per_page if per_page != 20 else "",
                "page": page,
            }
            params.update(cambios)
            limpio = {
                k: v for k, v in params.items()
                if v not in ("", None)
                and not (k == "page" and v == 1)
                and not (k == "plataforma" and v == "docker")
            }
            return "/gestion-maquinas" + ("?" + urlencode(limpio) if limpio else "")

        def ventana_paginas(actual, ultima, vecinos=1):
            """[1, None, 4, 5, 6, None, 11]: None = puntos suspensivos."""
            paginas = sorted({1, ultima, *range(max(1, actual - vecinos), min(ultima, actual + vecinos) + 1)})
            salida, previa = [], 0
            for p in paginas:
                if p - previa > 1:
                    salida.append(None)
                salida.append(p)
                previa = p
            return salida

        inicio = (page - 1) * per_page + 1 if maquinas else 0
        fin = inicio + len(maquinas) - 1 if maquinas else 0

        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        respuesta = templates.TemplateResponse(
            request,
            "dockerlabs/admin/gestion_maquinas.html",
            {
                "maquinas": maquinas,
                "categorias": categorias,
                "datos": datos,
                "plataforma": plataforma,
                "docker_total": totales["docker"],
                "bunker_total": totales["bunker"],
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": total_pages,
                "paginas": ventana_paginas(page, total_pages),
                "inicio": inicio,
                "fin": fin,
                "search": search,
                "dificultad": dificultad,
                "dificultades": _DIFICULTADES,
                "listado_url": listado_url,
                "csrf_token_value": csrf_token,
                "url_for": url_for,
                "current_user_role": role,
                "session": session,
            },
        )
        # Datos de administración: que ni el navegador ni intermediarios los reutilicen sin revalidar.
        respuesta.headers["Cache-Control"] = "private, no-cache"
        return respuesta

    @pages_router.get("/pending-machines", response_class=HTMLResponse)
    def pending_machines_page(
        request: Request,
        estado: str = "pendiente",
        q: str = "",
        orden: str = "",
        page: str = "1",
        session: dict = Depends(get_session),
    ):
        """Cola de revisión de envíos. Por defecto solo los pendientes; los
        añadidos y rechazados quedan archivados en sus pestañas."""
        ok, redirect = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return redirect

        from dockerlabs.routes.pending_admin import contar_por_estado

        P = PendingMachineSubmission
        POR_PAGINA = 12
        if estado not in ("pendiente", "aprobado", "rechazado", "todas"):
            estado = "pendiente"
        q = (q or "").strip()[:100]
        # La cola se atiende por orden de llegada; el archivo, lo último revisado arriba.
        orden_defecto = "antiguas" if estado == "pendiente" else "recientes"
        if orden not in ("recientes", "antiguas", "nombre"):
            orden = orden_defecto
        try:
            pagina = max(1, int(page))
        except (TypeError, ValueError):
            pagina = 1

        consulta = P.query
        if estado != "todas":
            consulta = consulta.filter(P.estado == estado)
        if q:
            patron = "%" + q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            consulta = consulta.filter(or_(
                P.nombre.ilike(patron, escape="\\"),
                P.autor_solicitante.ilike(patron, escape="\\"),
                P.discord_user.ilike(patron, escape="\\"),
                P.descripcion.ilike(patron, escape="\\"),
                P.tags.ilike(patron, escape="\\"),
            ))
        total = consulta.count()
        total_pages = max(1, math.ceil(total / POR_PAGINA))
        pagina = min(pagina, total_pages)

        fecha_archivo = func.coalesce(P.reviewed_at, P.submitted_at)
        if orden == "nombre":
            criterio = (func.lower(P.nombre).asc(), P.id.asc())
        elif estado == "pendiente" or estado == "todas":
            criterio = (P.submitted_at.asc(), P.id.asc()) if orden == "antiguas" else (P.submitted_at.desc(), P.id.desc())
        else:
            criterio = (fecha_archivo.asc(), P.id.asc()) if orden == "antiguas" else (fecha_archivo.desc(), P.id.desc())
        envios = consulta.order_by(*criterio).offset((pagina - 1) * POR_PAGINA).limit(POR_PAGINA).all()

        # Pistas para revisar más rápido: ¿ya está publicada?, ¿se ha enviado dos veces?
        nombres = {(m.nombre or "").strip().lower() for m in envios if m.nombre}
        publicadas, repetidos = {}, {}
        if nombres:
            for mid, nombre, origen in db.session.query(Machine.id, Machine.nombre, Machine.origen).filter(
                    func.lower(func.trim(Machine.nombre)).in_(nombres)).all():
                publicadas[(nombre or "").strip().lower()] = {"id": mid, "origen": origen or "docker"}
            for clave, n in db.session.query(func.lower(func.trim(P.nombre)), func.count(P.id)).filter(
                    func.lower(func.trim(P.nombre)).in_(nombres)).group_by(func.lower(func.trim(P.nombre))).all():
                repetidos[clave] = n

        ahora = utcnow()

        def hace(fecha):
            if not fecha:
                return "", 0
            dias = max(0, (ahora - fecha).days)
            if dias == 0:
                horas = int((ahora - fecha).total_seconds() // 3600)
                return ("hace menos de una hora" if horas < 1 else f"hace {horas} h"), 0
            if dias == 1:
                return "ayer", 1
            if dias < 60:
                return f"hace {dias} días", dias
            return f"hace {dias // 30} meses", dias

        revisores = {}
        ids_rev = {m.reviewed_by for m in envios if m.reviewed_by}
        if ids_rev:
            revisores = dict(db.session.query(User.id, User.username).filter(User.id.in_(ids_rev)).all())

        items = []
        for m in envios:
            clave = (m.nombre or "").strip().lower()
            texto, dias = hace(m.submitted_at)
            items.append({
                "m": m,
                "publicada": publicadas.get(clave),
                "repetida": repetidos.get(clave, 1) > 1,
                "espera": texto,
                "dias": dias,
                "urgente": m.estado == "pendiente" and dias >= 14,
                "revisor": revisores.get(m.reviewed_by, ""),
            })

        def listado_url(**cambios):
            """URL de la cola conservando filtros; los valores por defecto se omiten."""
            params = {"estado": estado, "q": q, "orden": orden, "page": pagina}
            params.update(cambios)
            defecto_orden = "antiguas" if params["estado"] == "pendiente" else "recientes"
            limpio = {
                k: v for k, v in params.items()
                if v not in ("", None)
                and not (k == "page" and v == 1)
                and not (k == "estado" and v == "pendiente")
                and not (k == "orden" and v == defecto_orden)
            }
            return "/pending-machines" + ("?" + urlencode(limpio) if limpio else "")

        def ventana(actual, ultima, vecinos=1):
            paginas = sorted({1, ultima, *range(max(1, actual - vecinos), min(ultima, actual + vecinos) + 1)})
            salida, previa = [], 0
            for p in paginas:
                if p - previa > 1:
                    salida.append(None)
                salida.append(p)
                previa = p
            return salida

        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        respuesta = templates.TemplateResponse(
            request,
            "dockerlabs/admin/pending.html",
            {
                "items": items,
                "machines": envios,
                "counts": contar_por_estado(db),
                "estado": estado,
                "q": q,
                "orden": orden,
                "orden_defecto": orden_defecto,
                "page": pagina,
                "total": total,
                "total_pages": total_pages,
                "paginas": ventana(pagina, total_pages),
                "inicio": (pagina - 1) * POR_PAGINA + 1 if envios else 0,
                "fin": (pagina - 1) * POR_PAGINA + len(envios),
                "listado_url": listado_url,
                "session": session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
            },
        )
        respuesta.headers["Cache-Control"] = "private, no-cache"
        return respuesta

    @pages_router.get("/user-pending", response_class=HTMLResponse)
    def user_pending_page(request: Request, session: dict = Depends(get_session)):
        user_id = session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)
        current_user_role = session.get("role", "")
        username = session.get("username")
        machines = (
            PendingMachineSubmission.query
            .filter_by(autor_solicitante=username)
            .order_by(PendingMachineSubmission.submitted_at.desc())
            .all()
        )
        return templates.TemplateResponse(
            request,
            "dockerlabs/auth/user-pending.html",
            {"username": username, "machines": machines, "session": session, "url_for": url_for, "current_user_role": current_user_role},
        )


    @pages_router.get("/writeups-analisis", response_class=HTMLResponse)
    def writeups_analisis_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return redirect
        user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_analisis.html",
            {"user": user, "session": session, "csrf_token_value": csrf_token, "url_for": url_for, "current_user_role": current_user_role},
        )

    @pages_router.get("/writeups-recibidos", response_class=HTMLResponse)
    def writeups_recibidos_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect
        user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_recibidos.html",
            {"session": session, "user": user, "csrf_token_value": csrf_token, "url_for": url_for, "current_user_role": current_user_role},
        )

    @pages_router.get("/writeups-publicados", response_class=HTMLResponse)
    def writeups_publicados_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador", "jugador"])
        if not ok:
            return redirect
        user = db.session.get(User, session.get("user_id")) if session.get("user_id") else None
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/writeups_publicados.html",
            {"user": user, "session": session, "csrf_token_value": csrf_token, "url_for": url_for, "current_user_role": current_user_role},
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

        now = utcnow()
        month_start = datetime(now.year, now.month, 1)

        # Solo las columnas que se usan; las helpers acceden por atributo y
        # funcionan igual con estas filas que con objetos ORM completos.
        q = db.session.query
        machines = q(Machine.id, Machine.nombre, Machine.dificultad, Machine.origen, Machine.fecha, Machine.descargas).all()
        writeups = q(Writeup.maquina, Writeup.tipo, Writeup.created_at).all()
        users = q(User.role, User.created_at).all()
        certificates = q(Certificate.created_at).all()
        completed = q(CompletedMachine.completed_at).all()
        ratings = q(Rating.dificultad_score, Rating.aprendizaje_score, Rating.recomendaria_score, Rating.diversion_score).all()
        pending_submissions = q(PendingMachineSubmission.estado, PendingMachineSubmission.submitted_at).all()

        # Las tablas de registro crecen sin límite (una fila por visita,
        # descarga o clic): se agregan y filtran en SQL, nunca se cargan enteras.
        def primera_fecha(columna):
            return q(func.min(columna)).scalar()

        dl_min = primera_fecha(MachineDownloadLog.created_at)
        cr_min = primera_fecha(CertificateRequestLog.created_at)
        vi_min = primera_fecha(PageVisitLog.created_at)
        ob_min = primera_fecha(OutboundClickLog.created_at)
        minimos = [f for f in (dl_min, cr_min, vi_min, ob_min) if f]
        visible_min = min(minimos) if minimos else None

        resolved = _resolve_range(rango, desde, hasta, visible_min)
        start, end, active_rango = resolved["start"], resolved["end"], resolved["rango"]
        filtro_label = resolved["label"]

        def en_rango(*columnas):
            fecha = columnas[0]
            return q(*columnas).filter(fecha.isnot(None), fecha >= start, fecha <= end).all()

        def contar_desde(fecha, desde_cuando):
            return q(func.count()).select_from(fecha.class_).filter(fecha >= desde_cuando).scalar()

        def por_dia(fecha, *agregados):
            """Una fila por día del rango: (dia, agregados...)."""
            dia = func.date(fecha).label("dia")
            filas = q(dia, *agregados).filter(fecha.isnot(None), fecha >= start, fecha <= end).group_by(dia).all()
            return [(datetime(f.dia.year, f.dia.month, f.dia.day), *f[1:]) for f in filas]

        descargas_dia = por_dia(MachineDownloadLog.created_at, func.count())
        total_descargas = sum(n for _, n in descargas_dia)
        cert_requests_filtered = en_rango(CertificateRequestLog.created_at)

        visitas_dia = por_dia(PageVisitLog.created_at, func.count())
        dia_v = func.date(PageVisitLog.created_at)
        visitantes_dia = [(datetime(d.year, d.month, d.day), v) for d, v in
                          q(dia_v, PageVisitLog.visitor).filter(PageVisitLog.created_at.isnot(None), PageVisitLog.created_at >= start,
                                                               PageVisitLog.created_at <= end).distinct().all()]
        hoy = datetime(now.year, now.month, now.day)
        visitas_hoy, unicos_hoy = q(func.count(), func.count(func.distinct(PageVisitLog.visitor))).filter(
            PageVisitLog.created_at >= hoy, PageVisitLog.created_at < hoy + timedelta(days=1)).one()
        visit_stats = {
            "total_en_rango": sum(n for _, n in visitas_dia),
            "hoy": visitas_hoy,
            "unicos_hoy": unicos_hoy,
            "by_day": _bucketize(visitas_dia, lambda f: f[0], start, end, peso_fn=lambda f: f[1]),
            "unique_by_day": _bucketize_unique(visitantes_dia, lambda f: f[0], lambda f: f[1], start, end),
            "since": vi_min.strftime("%d/%m/%Y") if vi_min else None,
        }

        ob_filtered = en_rango(OutboundClickLog.created_at, OutboundClickLog.visitor, OutboundClickLog.destino, OutboundClickLog.origen)
        _by = {}
        for o in ob_filtered:
            _by.setdefault((o.destino, o.origen), []).append(o)
        outbound_stats = {
            "total_en_rango": len(ob_filtered),
            "unicos_en_rango": len({o.visitor for o in ob_filtered}),
            "newsletter": len([o for o in ob_filtered if o.destino == "newsletter"]),
            "academia": len([o for o in ob_filtered if o.destino in ("academia", "academia-bunker")]),
            "master": len([o for o in ob_filtered if o.destino == "master"]),
            "newsletter_by_day": _bucketize([o for o in ob_filtered if o.destino == "newsletter"], lambda o: o.created_at, start, end),
            "academia_by_day": _bucketize([o for o in ob_filtered if o.destino in ("academia", "academia-bunker")], lambda o: o.created_at, start, end),
            "master_by_day": _bucketize([o for o in ob_filtered if o.destino == "master"], lambda o: o.created_at, start, end),
            "por_origen": [{"destino": d, "origen": og, "clics": len(v), "unicos": len({x.visitor for x in v})}
                           for (d, og), v in sorted(_by.items(), key=lambda kv: -len(kv[1]))],
            "since": ob_min.strftime("%d/%m/%Y") if ob_min else None,
        }

        filtro = {
            "active": active_rango,
            "desde": desde,
            "hasta": hasta,
            "label": filtro_label,
            "total_descargas": total_descargas,
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
            "mes_actual": contar_desde(MachineDownloadLog.created_at, month_start),
            "rango_label": filtro_label,
            "total_en_rango": total_descargas,
            "by_day": _bucketize(descargas_dia, lambda f: f[0], start, end, peso_fn=lambda f: f[1]),
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
            "solicitudes_mes_actual": contar_desde(CertificateRequestLog.created_at, month_start),
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
            },
        )
