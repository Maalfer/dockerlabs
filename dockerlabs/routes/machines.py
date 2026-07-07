import json
import os
import secrets
import time
from datetime import datetime
from typing import Optional

from fastapi import Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from werkzeug.utils import secure_filename

from dockerlabs.maquinas import recalcular_ranking_creadores
from dockerlabs.models import Category, CompletedMachine, Machine, MachineClaim, MachineEditRequest, User


class ActualizarMaquinaRequest(BaseModel):
    id: int
    origen: str
    nombre: str
    dificultad: str
    autor: str
    enlace_autor: Optional[str] = ""
    fecha: str
    imagen: Optional[str] = ""
    descripcion: str
    link_descarga: str
    categoria: Optional[str] = ""


class ReclamarMaquinaRequest(BaseModel):
    maquina_nombre: str
    contacto: str
    prueba: str


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

        if role not in ("admin", "moderador"):
            if role == "jugador" and maquina.autor == username:
                nuevos_datos = json.dumps(
                    {
                        "nombre": nombre,
                        "dificultad": dificultad_texto,
                        "clase": clase,
                        "color": color,
                        "autor": autor,
                        "enlace_autor": enlace_autor,
                        "fecha": fecha,
                        "imagen": imagen,
                        "descripcion": descripcion,
                        "link_descarga": link_descarga,
                    }
                )
                try:
                    edit_req = MachineEditRequest(
                        machine_id=id,
                        origen=origen,
                        autor=username,
                        nuevos_datos=nuevos_datos,
                        estado="pendiente",
                    )
                    db.session.add(edit_req)
                    db.session.commit()
                    return {"success": True, "message": "Solicitud de edición enviada para revisión"}
                except Exception as e:
                    db.session.rollback()
                    return JSONResponse(status_code=500, content={"error": str(e)})
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        try:
            maquina.nombre = nombre
            maquina.dificultad = dificultad_texto
            maquina.clase = clase
            maquina.color = color
            maquina.autor = autor
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
            redirect_url = "/bunkerlabs" if data.destino == "bunker" else "/"
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

    @api_router.post("/empezar/add")
    async def api_add_empezar(
        request: Request,
        nombre: str = Form(...),
        script: UploadFile = File(...),
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        """Crea un lab de la sección 'Empezar de 0' (origen='empezar').

        Solo pide nombre + el .py. El resto de campos NOT NULL del modelo se
        rellenan con valores por defecto. El .py se guarda en disco y la ruta
        queda en Machine.script_path; se sirve como descarga directa.
        """
        role = session.get("role", "")
        user_id = session.get("user_id")
        if not user_id or role not in ("admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        nombre = (nombre or "").strip()
        if not nombre:
            return JSONResponse(status_code=400, content={"error": "El nombre es obligatorio"})

        if not script or not script.filename:
            return JSONResponse(status_code=400, content={"error": "Debes subir un archivo .py"})
        safe_name = secure_filename(script.filename)
        if not safe_name.lower().endswith(".py"):
            return JSONResponse(status_code=400, content={"error": "El archivo debe tener extensión .py"})

        content = await script.read()
        if not content:
            return JSONResponse(status_code=400, content={"error": "El archivo está vacío"})
        if len(content) > 1 * 1024 * 1024:
            return JSONResponse(status_code=400, content={"error": "El .py es demasiado grande (máx 1 MB)"})
        try:
            content.decode("utf-8")
        except UnicodeDecodeError:
            return JSONResponse(status_code=400, content={"error": "El .py debe ser texto UTF-8 válido"})

        if Machine.query.filter_by(nombre=nombre).first():
            return JSONResponse(status_code=400, content={"error": "Ya existe una máquina con ese nombre"})

        autor = (session.get("username") or "").strip() or "DockerLabs"
        fecha = datetime.now().strftime("%d/%m/%Y")

        try:
            new_lab = Machine(
                nombre=nombre,
                dificultad="Iniciación",
                clase="empezar",
                color="#43959b",
                autor=autor,
                enlace_autor="",
                fecha=fecha,
                imagen=_DEFAULT_IMAGEN,
                descripcion="",
                link_descarga="",
                origen="empezar",
            )
            db.session.add(new_lab)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

        scripts_dir = os.path.join(_BASE_DIR, "uploads", "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        ts = int(time.time())
        final_filename = f"empezar_{new_lab.id}_{ts}.py"
        file_path = os.path.join(scripts_dir, final_filename)
        try:
            with open(file_path, "wb") as f:
                f.write(content)
            new_lab.script_path = f"uploads/scripts/{final_filename}"
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": f"No se pudo guardar el script: {e}"})

        return {"success": True, "message": "Lab de iniciación creado correctamente", "machine_id": new_lab.id}

    @api_router.post("/reclamar-maquina")
    async def api_reclamar_maquina(
        request: Request,
        data: ReclamarMaquinaRequest,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        user_id = session.get("user_id")
        username = (session.get("username") or "").strip()
        role = session.get("role", "")
        if not user_id or role not in ("jugador", "admin", "moderador"):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        try:
            db.session.add(
                MachineClaim(
                    user_id=user_id,
                    username=username,
                    maquina_nombre=data.maquina_nombre,
                    contacto=data.contacto,
                    prueba=data.prueba,
                    estado="pendiente",
                )
            )
            db.session.commit()
            return {"success": True, "message": "Reclamación enviada correctamente"}
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/claims/{claim_id}/approve")
    async def api_approve_claim(
        request: Request,
        claim_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, _ = require_auth_and_role(session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            maquina = Machine.query.filter_by(nombre=claim.maquina_nombre).first()
            if maquina:
                maquina.autor = claim.username
            claim.estado = "aprobada"
            db.session.commit()
            recalcular_ranking_creadores()
            return {"success": True}
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/claims/{claim_id}/reject")
    async def api_reject_claim(
        request: Request,
        claim_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, _ = require_auth_and_role(session, ["admin"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            db.session.delete(claim)
            db.session.commit()
            return {"success": True}
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

    @api_router.post("/claims/{claim_id}/revert")
    async def api_revert_claim(
        request: Request,
        claim_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, _ = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        claim = MachineClaim.query.get(claim_id)
        if not claim:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        claim.estado = "pendiente"
        db.session.commit()
        return {"success": True}

    @api_router.post("/machine-edit-requests/{request_id}/approve")
    async def api_approve_machine_edit(
        request: Request,
        request_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, _ = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        try:
            nuevos = json.loads(req.nuevos_datos)
        except Exception:
            nuevos = {}
        maquina = Machine.query.get(req.machine_id)
        if maquina:
            for field in (
                "nombre",
                "dificultad",
                "clase",
                "color",
                "autor",
                "enlace_autor",
                "fecha",
                "imagen",
                "descripcion",
                "link_descarga",
            ):
                val = nuevos.get(field)
                if field == "imagen":
                    setattr(maquina, field, _sanitize_imagen(val))
                elif val:
                    setattr(maquina, field, val)
            db.session.commit()
            if req.origen == "docker":
                recalcular_ranking_creadores()
        req.estado = "aprobada"
        db.session.commit()
        return {"success": True}

    @api_router.post("/machine-edit-requests/{request_id}/reject")
    async def api_reject_machine_edit(
        request: Request,
        request_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, _ = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        req.estado = "rechazada"
        db.session.commit()
        return {"success": True}

    @api_router.post("/machine-edit-requests/{request_id}/revert")
    async def api_revert_machine_edit(
        request: Request,
        request_id: int,
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token),
    ):
        ok, _ = require_auth_and_role(session, ["admin", "moderador"])
        if not ok:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
        req = MachineEditRequest.query.get(request_id)
        if not req:
            return JSONResponse(status_code=404, content={"error": "No encontrada"})
        req.estado = "pendiente"
        db.session.commit()
        return {"success": True}

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

