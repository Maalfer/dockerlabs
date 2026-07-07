import json
import math
from datetime import datetime

import secrets
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import or_

from dockerlabs.models import (Category, Machine, MachineClaim, MachineEditRequest,
    NameClaim, PendingMachineSubmission, UsernameChangeRequest,
    User, Writeup, WriteupEditRequest)


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

    @pages_router.get("/peticiones", response_class=HTMLResponse)
    def peticiones_page(request: Request, session: dict = Depends(get_session)):
        ok, redirect = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return redirect

        claims = MachineClaim.query.order_by(MachineClaim.id.desc()).all()

        username_requests = UsernameChangeRequest.query.order_by(UsernameChangeRequest.id.desc()).all()
        username_change_requests = []
        for r in username_requests:
            user = User.query.get(r.user_id)
            username_change_requests.append({
                "id": r.id,
                "user_id": r.user_id,
                "old_username": r.old_username,
                "requested_username": r.requested_username,
                "reason": r.reason,
                "contacto_opcional": r.contacto_opcional,
                "estado": r.estado,
                "created_at": r.created_at,
                "processed_by": r.processed_by,
                "processed_at": r.processed_at,
                "decision_reason": r.decision_reason,
                "user_email": user.email if user else None,
                "conflict_count": getattr(r, 'conflict_count', None),
                "conflict_examples": getattr(r, 'conflict_examples', None),
            })

        machine_edits = MachineEditRequest.query.order_by(MachineEditRequest.id.desc()).all()
        machine_edit_requests = []
        for r in machine_edits:
            try:
                nuevos = json.loads(r.nuevos_datos) if r.nuevos_datos else {}
            except Exception:
                nuevos = {}
            machine_edit_requests.append({
                "id": r.id,
                "machine_id": r.machine_id,
                "origen": r.origen,
                "autor": r.autor,
                "nuevos": nuevos,
                "estado": r.estado,
                "fecha": r.fecha,
            })

        name_claims = NameClaim.query.order_by(NameClaim.id.desc()).all()
        peticiones_nombres = []
        for p in name_claims:
            user = User.query.filter_by(username=p.username).first()
            peticiones_nombres.append({
                "id": p.id,
                "username": p.username,
                "email": p.email,
                "nombre_solicitado": p.nombre_solicitado,
                "nombre_actual": p.nombre_actual,
                "motivo": p.motivo,
                "estado": p.estado,
                "created_at": p.created_at,
            })

        writeup_edits = WriteupEditRequest.query.order_by(WriteupEditRequest.id.desc()).all()
        edit_requests = []
        for r in writeup_edits:
            edit_requests.append({
                "id": r.id,
                "writeup_id": r.writeup_id,
                "user_id": r.user_id,
                "username": r.username,
                "maquina_actual": r.maquina_original,
                "autor_actual": r.autor_original,
                "url_actual": r.url_original,
                "tipo_actual": r.tipo_original,
                "maquina_nueva": r.maquina_nueva,
                "autor_nuevo": r.autor_nuevo,
                "url_nueva": r.url_nueva,
                "tipo_nuevo": r.tipo_nuevo,
                "estado": r.estado,
                "created_at": r.created_at,
            })

        current_user_role = session.get("role", "")
        csrf_token = session.get("csrf_token") or secrets.token_urlsafe(32)

        return templates.TemplateResponse(
            request,
            "dockerlabs/admin/peticiones.html",
            {
                "claims": claims,
                "username_change_requests": username_change_requests,
                "machine_edit_requests": machine_edit_requests,
                "peticiones_nombres": peticiones_nombres,
                "edit_requests": edit_requests,
                "session": session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "csrf_token_value": csrf_token,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.get("/estadisticas", response_class=HTMLResponse)
    def estadisticas_page(request: Request, session: dict = Depends(get_session)):
        machines = Machine.query.all()
        writeups = Writeup.query.all()
        users = User.query.all()

        machine_stats = {
            "total": len(machines),
            "by_dificultad": _distribution_by_field(machines, "dificultad"),
            "by_origen": _distribution_by_field(machines, "origen"),
            "by_year": _distribution_by_year(machines, lambda m: _parse_date_flexible(m.fecha)),
            "by_month": _distribution_by_month(machines, lambda m: _parse_date_flexible(m.fecha)),
        }

        writeup_stats = {
            "total": len(writeups),
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

        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/estadisticas.html",
            {"machine_stats": machine_stats, "writeup_stats": writeup_stats, "user_stats": user_stats, "session": session, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )
