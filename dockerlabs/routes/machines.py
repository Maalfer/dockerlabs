import os
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel

from dockerlabs.discord_notify import notify_new_machine
from dockerlabs.maquinas import recalcular_ranking_creadores
from dockerlabs.models import Category, CompletedMachine, Machine, MachineDownloadLog, User


class AddMaquinaRequest(BaseModel):
    nombre: str
    dificultad: Optional[str] = ""
    autor: str
    fecha: str
    descripcion: str
    link_descarga: str
    imagen: Optional[str] = ""
    destino: Optional[str] = "docker"
    categoria: Optional[str] = ""


# Imagen de portada por defecto cuando no hay logo subido (logo_path)
_DEFAULT_IMAGEN = "dockerlabs/images/logos/logo.png"
# Directorio base del proyecto (.../dockerlabs) para validar rutas estáticas
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _sanitize_imagen(value: Optional[str]) -> str:
    """Normaliza el campo `imagen` (fallback de portada).

    El logo real de una máquina se sirve desde `logo_path`; `imagen` solo es el
    fallback estático. El formulario a veces envía basura ('undefined', 'null',
    un nombre suelto inexistente como 'gotham.png', etc.), lo que provocaba que
    la portada cayera al logo genérico sin que se notara el dato corrupto.

    Solo se conserva el valor si apunta a un fichero que existe bajo `static/`;
    en cualquier otro caso se devuelve la imagen por defecto.
    """
    v = (value or "").strip()
    if not v or v.lower() in ("undefined", "null", "none", "false"):
        return _DEFAULT_IMAGEN
    # Evitar path traversal / rutas absolutas
    if ".." in v or v.startswith("/") or "\\" in v:
        return _DEFAULT_IMAGEN
    candidate = os.path.join(_BASE_DIR, "static", v)
    if os.path.isfile(candidate):
        return v
    return _DEFAULT_IMAGEN


def _difficulty_to_color_clase(dificultad: str):
    d = dificultad.strip().lower()
    if "muy" in d:
        return "muy-facil", "Muy Fácil", "#43959b"
    elif "facil" in d or "fácil" in d:
        return "facil", "Fácil", "#8bc34a"
    elif "medio" in d:
        return "medio", "Medio", "#e0a553"
    else:
        return "dificil", "Difícil", "#d83c31"


def register_machine_routes(
    api_router,
    pages_router,
    get_session,
    verify_csrf_token,
    require_auth_and_role,
    encode_session_cookie,
    templates,
    db,
    url_for,
):
    @api_router.post("/gestion-maquinas/actualizar")
    async def api_actualizar_maquina(
        request: Request,
        id: int = Form(...),
        origen: str = Form(...),
        nombre: str = Form(...),
        dificultad: str = Form(...),
        autor: str = Form(...),
        enlace_autor: str = Form(""),
        fecha: str = Form(...),
        imagen: str = Form(""),
        descripcion: str = Form(...),
        link_descarga: str = Form(...),
        categoria: str = Form(""),
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        role = session.get("role", "")
        username = (session.get("username") or "").strip()
        user_id = session.get("user_id")

        if not user_id:
            return JSONResponse(status_code=401, content={"error": "No autenticado"})
        if origen not in ("docker", "bunker"):
            return JSONResponse(status_code=400, content={"error": "Origen inválido"})

        clase, dificultad_texto, color = _difficulty_to_color_clase(dificultad)

        maquina = Machine.query.get(id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})

        is_privileged = role in ("admin", "moderador")
        if not is_privileged:
            if not (role == "jugador" and maquina.autor == username):
                return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        # Fix de seguridad (auditoria VDP): un jugador editando su propia
        # maquina escribia estos campos directamente en produccion sin
        # ninguna validacion, permitiendo XSS almacenado (nombre/enlaces/
        # descripcion se renderizan sin escapar en la home y en el listado
        # de writeups) y mass assignment del autor (reasignar la autoria a
        # cualquier usuario, manipulando el ranking publico de creadores).
        from dockerlabs import validators

        _dangerous_chars = set('<>"\'`')
        if any(c in _dangerous_chars for c in nombre) or any(ord(c) < 32 for c in nombre):
            return JSONResponse(status_code=400, content={"error": "El nombre de la máquina contiene caracteres no permitidos"})

        ok, err = validators.validate_url(link_descarga)
        if not ok:
            return JSONResponse(status_code=400, content={"error": f"Link de descarga: {err}"})

        if enlace_autor:
            ok, err = validators.validate_url(enlace_autor)
            if not ok:
                return JSONResponse(status_code=400, content={"error": f"Enlace autor: {err}"})

        descripcion = validators.sanitize_text(descripcion)

        # El autor solo lo puede reasignar un admin/moderador: un jugador no
        # puede cambiar la autoria (y por tanto el ranking publico) de su
        # propia maquina editandola.
        nuevo_autor = autor if is_privileged else maquina.autor

        try:
            maquina.nombre = nombre
            maquina.dificultad = dificultad_texto
            maquina.clase = clase
            maquina.color = color
            maquina.autor = nuevo_autor
            maquina.enlace_autor = enlace_autor or ""
            maquina.fecha = fecha
            maquina.imagen = _sanitize_imagen(imagen)
            maquina.descripcion = descripcion
            maquina.link_descarga = link_descarga
            db.session.commit()

            cat_obj = Category.query.filter_by(machine_id=id, origen=origen).first()
            if categoria:
                if cat_obj:
                    cat_obj.categoria = categoria
                else:
                    db.session.add(Category(machine_id=id, origen=origen, categoria=categoria))
            else:
                if cat_obj:
                    db.session.delete(cat_obj)
            db.session.commit()

            if origen == "docker":
                recalcular_ranking_creadores()

            return {"success": True, "message": "Máquina actualizada correctamente"}
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/gestion-maquinas/eliminar")
    async def api_eliminar_maquina(
        request: Request,
        id: int = Form(...),
        origen: str = Form(...),
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        role = session.get("role", "")
        user_id = session.get("user_id")
        if not user_id or role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        if origen not in ("docker", "bunker"):
            return JSONResponse(status_code=400, content={"error": "Origen inválido"})

        maquina = Machine.query.get(id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})
        try:
            db.session.delete(maquina)
            db.session.commit()
            if origen == "docker":
                recalcular_ranking_creadores()
            return {"success": True, "message": "Máquina eliminada correctamente"}
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @pages_router.get("/add-maquina", response_class=HTMLResponse)
    def add_maquina_page_get(request: Request, session: dict = Depends(get_session)):
        ok, redir = require_auth_and_role(session, ["admin"])
        if not ok:
            return redir
        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/add-maquina.html",
            {"error": None, "session": session, "url_for": url_for, "current_user_role": current_user_role, "g": {"csp_nonce": secrets.token_urlsafe(32)}},
        )

    @api_router.post("/add-maquina")
    async def api_add_maquina(
        request: Request,
        data: AddMaquinaRequest,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        role = session.get("role", "")
        user_id = session.get("user_id")
        if not user_id or role != "admin":
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        if not User.query.filter_by(username=data.autor).first():
            return JSONResponse(status_code=400, content={"error": "El autor no es un usuario registrado"})

        try:
            fecha = datetime.strptime(data.fecha, "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            return JSONResponse(status_code=400, content={"error": "Formato de fecha inválido (YYYY-MM-DD)"})

        user_obj = User.query.get(user_id)
        enlace_autor = ""
        if user_obj:
            enlace_autor = user_obj.youtube_url or user_obj.github_url or user_obj.linkedin_url or ""

        imagen = _sanitize_imagen(data.imagen)

        clase, dificultad_texto, color = _difficulty_to_color_clase(data.dificultad)

        try:
            new_machine = Machine(
                nombre=data.nombre,
                dificultad=dificultad_texto,
                clase=clase,
                color=color,
                autor=data.autor,
                enlace_autor=enlace_autor,
                fecha=fecha,
                imagen=imagen,
                descripcion=data.descripcion,
                link_descarga=data.link_descarga,
                origen=data.destino or "docker",
            )
            db.session.add(new_machine)
            db.session.commit()
            if data.destino == "docker":
                recalcular_ranking_creadores()
            await notify_new_machine(new_machine)
            redirect_url = {
                "bunker": "/bunkerlabs",
            }.get(data.destino, "/")
            return {
                "success": True,
                "message": "Máquina añadida correctamente",
                "redirect_url": redirect_url,
                "machine_id": new_machine.id,
                "origen": new_machine.origen,
            }
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @pages_router.get("/maquinas-hechas", response_class=HTMLResponse)
    def maquinas_hechas_page(request: Request, session: dict = Depends(get_session)):
        user_id = session.get("user_id")
        if not user_id:
            return RedirectResponse(url="/login", status_code=302)

        results = (
            db.session.query(
                CompletedMachine.machine_name,
                CompletedMachine.completed_at,
                Machine.id,
                Machine.dificultad,
                Machine.color,
                Machine.imagen,
                Machine.clase,
                Machine.autor,
            )
            .outerjoin(Machine, CompletedMachine.machine_name == Machine.nombre)
            .filter(CompletedMachine.user_id == user_id)
            .order_by(CompletedMachine.completed_at.desc())
            .all()
        )

        completed_machines = []
        for row in results:
            completed_machines.append(
                {
                    "machine_name": row.machine_name,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "machine_id": row.id,
                    "machine_logo_url": f"/img/maquina/{row.id}" if row.id else "/static/dockerlabs/images/logos/logo.png",
                    "dificultad": row.dificultad,
                    "color": row.color,
                    "imagen": row.imagen,
                    "clase": row.clase,
                    "autor": row.autor,
                }
            )

        total_machines = Machine.query.filter_by(origen="docker").count()
        completed_count = len(completed_machines)
        completion_percentage = round((completed_count / total_machines * 100), 1) if total_machines > 0 else 0

        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/user/maquinas_hechas.html",
            {
                "completed_machines": completed_machines,
                "total_machines": total_machines,
                "completed_count": completed_count,
                "completion_percentage": completion_percentage,
                "session": session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

    @pages_router.get("/maquinas/{machine_id}/descargar", response_class=HTMLResponse)
    def descargar_maquina_page(machine_id: int, request: Request, session: dict = Depends(get_session)):
        maquina = Machine.query.get(machine_id)
        if not maquina:
            raise HTTPException(status_code=404)
        if maquina.origen == "bunker":
            return RedirectResponse(url=f"/bunkerlabs/maquinas/{maquina.id}/descargar", status_code=302)
        if maquina.origen != "docker":
            raise HTTPException(status_code=404)

        maquina.descargas = (maquina.descargas or 0) + 1
        db.session.add(MachineDownloadLog(machine_id=maquina.id))
        db.session.commit()

        current_user_role = session.get("role", "")
        return templates.TemplateResponse(
            request,
            "dockerlabs/info/descargar.html",
            {
                "maquina": maquina,
                "session": session,
                "url_for": url_for,
                "current_user_role": current_user_role,
                "g": {"csp_nonce": secrets.token_urlsafe(32)},
            },
        )

