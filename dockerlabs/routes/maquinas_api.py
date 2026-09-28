"""API de maquinas: acceso invitado, logo, valoraciones y completadas."""

import io
import os
import time
from datetime import datetime

from fastapi import Depends, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import func
from werkzeug.utils import secure_filename

from dockerlabs.extensions import db
from dockerlabs.models import User, Machine, CompletedMachine, Rating, Writeup


class RateMachineRequest(BaseModel):
    maquina_nombre: str
    dificultad_score: float
    aprendizaje_score: float
    recomendaria_score: float
    diversion_score: float

class ToggleCompletedRequest(BaseModel):
    machine_name: str


def register_maquinas_api_routes(api_router, get_session, verify_csrf_token, BASE_DIR):
    """Registra las rutas de este modulo en el router recibido."""

    @api_router.post("/gestion-maquinas/toggle-guest-access")
    def api_toggle_guest_access(
        request: Request,
        id: int = Form(...),
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token)
    ):
        caller_role = session.get('role', '')
        if caller_role not in ('admin', 'moderador'):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        maquina = Machine.query.get(id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})
        maquina.guest_access = not maquina.guest_access
        db.session.commit()
        return {"message": "Estado actualizado", "guest_access": maquina.guest_access}

    @api_router.get("/gestion-maquinas/machine-stats/{machine_id}")
    def api_gestion_machine_stats(
        request: Request,
        machine_id: int,
        session: dict = Depends(get_session),
    ):
        role = session.get('role', '')
        username = (session.get('username') or '').strip()
        if role not in ('admin', 'moderador', 'jugador'):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        maquina = Machine.query.get(machine_id)
        if not maquina:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})

        # Un jugador solo puede ver las estadisticas de sus propias maquinas
        # (mismo criterio de propiedad que el resto de este archivo).
        if role == 'jugador' and maquina.autor != username:
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        writeups_count = Writeup.query.filter_by(maquina=maquina.nombre).count()

        avg_result = db.session.query(
            func.avg(Rating.dificultad_score).label('avg_dificultad'),
            func.avg(Rating.aprendizaje_score).label('avg_aprendizaje'),
            func.avg(Rating.recomendaria_score).label('avg_recomendaria'),
            func.avg(Rating.diversion_score).label('avg_diversion'),
            func.count(Rating.id).label('count')
        ).filter_by(maquina_nombre=maquina.nombre).first()

        rating_count = avg_result.count if avg_result else 0
        rating_avg = 0
        if rating_count > 0:
            criteria_sum = ((avg_result.avg_dificultad or 0) + (avg_result.avg_aprendizaje or 0) +
                            (avg_result.avg_recomendaria or 0) + (avg_result.avg_diversion or 0))
            rating_avg = round(criteria_sum / 4, 1)

        return {
            "nombre": maquina.nombre,
            "writeups": writeups_count,
            "descargas": maquina.descargas or 0,
            "rating_avg": rating_avg,
            "rating_count": rating_count,
        }

    @api_router.post("/gestion-maquinas/upload-logo")
    async def api_upload_machine_logo(
        request: Request,
        logo: UploadFile = File(...),
        machine_id: int = Form(...),
        origen: str = Form(...),
        session: dict = Depends(get_session),
        csrf_ok: bool = Depends(verify_csrf_token)
    ):
        caller_role = session.get('role', '')
        username = (session.get('username') or '').strip()

        maq = Machine.query.get(machine_id)
        if not maq:
            return JSONResponse(status_code=404, content={"error": "Máquina no encontrada"})

        # El logo lo puede subir un admin/moderador o el propio creador de la
        # maquina (mismo criterio de propiedad que en gestion-maquinas/actualizar).
        is_privileged = caller_role in ('admin', 'moderador')
        if not is_privileged and not (caller_role == 'jugador' and maq.autor == username):
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})

        if not logo or not logo.filename:
            return JSONResponse(status_code=400, content={"error": "No se ha enviado ningún archivo"})
        if not logo.content_type.startswith('image/'):
            return JSONResponse(status_code=400, content={"error": "El archivo debe ser una imagen"})

        file_bytes = await logo.read()
        if len(file_bytes) > 2 * 1024 * 1024:
            return JSONResponse(status_code=400, content={"error": "La imagen es demasiado grande (máx 2MB)"})

        from dockerlabs import validators

        try:
            img = Image.open(io.BytesIO(file_bytes))
            img.verify()
        except Exception:
            return JSONResponse(status_code=400, content={"error": "La imagen enviada no es válida"})

        valid, err = validators.validate_image_content(io.BytesIO(file_bytes))
        if not valid:
            return JSONResponse(status_code=400, content={"error": f"Imagen inválida: {err}"})

        original_filename = secure_filename(logo.filename or '')
        _, ext = os.path.splitext(original_filename)
        ext = ext.lower()
        ALLOWED = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.avif'}
        if ext not in ALLOWED:
            return JSONResponse(status_code=400, content={"error": "Formato de imagen no permitido"})

        from dockerlabs.image_utils import to_webp

        try:
            save_bytes = to_webp(file_bytes, profile='logo')
        except Exception:
            return JSONResponse(status_code=400, content={"error": "No se pudo procesar la imagen"})
        logo_mime = 'image/webp'
        save_ext = '.webp'

        almacenamiento_dir = os.path.join(BASE_DIR, 'uploads', 'logos')
        os.makedirs(almacenamiento_dir, exist_ok=True)

        ts = int(time.time())
        prefix = 'bunker' if origen == 'bunker' else 'docker'
        final_filename = f"{prefix}_{machine_id}_{ts}{save_ext}"
        file_path = os.path.join(almacenamiento_dir, final_filename)

        try:
            with open(file_path, 'wb') as f:
                f.write(save_bytes)

            if maq.logo_path:
                old_path = os.path.join(BASE_DIR, maq.logo_path)
                if os.path.exists(old_path):
                    try:
                        os.remove(old_path)
                    except Exception:
                        pass

            maq.logo_path = f"uploads/logos/{final_filename}"
            maq.logo_data = None
            maq.logo_mime = logo_mime
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"error": str(e)})

        return {
            "message": "Logo subido correctamente",
            "filename": final_filename,
            "image_url": f"/img/maquina/{machine_id}?t={ts}"
        }

    @api_router.get("/get_users")
    def api_get_users(request: Request, session: dict = Depends(get_session)):
        caller_role = session.get('role', '')
        if caller_role != 'admin':
            return JSONResponse(status_code=403, content={"error": "Acceso denegado"})


        users = User.query.order_by(User.username.asc()).all()
        return {"users": [{"id": u.id, "username": u.username} for u in users]}

    @api_router.post("/rate_machine")
    def api_rate_machine(request: Request, data: RateMachineRequest, session: dict = Depends(get_session)):
        user_id = session.get('user_id')
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión para puntuar"})

        scores = [data.dificultad_score, data.aprendizaje_score, data.recomendaria_score, data.diversion_score]
        if any(s < 1 or s > 5 for s in scores):
            return JSONResponse(status_code=400, content={"success": False, "message": "Las puntuaciones deben estar entre 1 y 5"})

        try:
            existing = Rating.query.filter_by(usuario_id=user_id, maquina_nombre=data.maquina_nombre).first()
            if existing:
                existing.dificultad_score = data.dificultad_score
                existing.aprendizaje_score = data.aprendizaje_score
                existing.recomendaria_score = data.recomendaria_score
                existing.diversion_score = data.diversion_score
                existing.fecha = datetime.utcnow()
            else:
                new_rating = Rating(
                    usuario_id=user_id,
                    maquina_nombre=data.maquina_nombre,
                    dificultad_score=data.dificultad_score,
                    aprendizaje_score=data.aprendizaje_score,
                    recomendaria_score=data.recomendaria_score,
                    diversion_score=data.diversion_score
                )
                db.session.add(new_rating)
            db.session.commit()
            return {"success": True, "message": "Puntuación guardada correctamente"}
        except Exception as e:
            db.session.rollback()
            return JSONResponse(status_code=500, content={"success": False, "message": str(e)})

    @api_router.get("/get_machine_rating/{maquina_nombre}")
    def api_get_machine_rating(request: Request, maquina_nombre: str, session: dict = Depends(get_session)):
        avg_result = db.session.query(
            func.avg(Rating.dificultad_score).label('avg_dificultad'),
            func.avg(Rating.aprendizaje_score).label('avg_aprendizaje'),
            func.avg(Rating.recomendaria_score).label('avg_recomendaria'),
            func.avg(Rating.diversion_score).label('avg_diversion'),
            func.count(Rating.id).label('count')
        ).filter_by(maquina_nombre=maquina_nombre).first()

        user_id = session.get('user_id')
        user_rating = None
        if user_id:
            user_result = Rating.query.filter_by(usuario_id=user_id, maquina_nombre=maquina_nombre).first()
            if user_result:
                user_rating = {
                    'dificultad': user_result.dificultad_score,
                    'aprendizaje': user_result.aprendizaje_score,
                    'recomendaria': user_result.recomendaria_score,
                    'diversion': user_result.diversion_score
                }

        count = avg_result.count if avg_result else 0
        total_avg = 0
        if count > 0:
            criteria_sum = ((avg_result.avg_dificultad or 0) + (avg_result.avg_aprendizaje or 0) +
                            (avg_result.avg_recomendaria or 0) + (avg_result.avg_diversion or 0))
            total_avg = criteria_sum / 4

        return {
            'average': round(total_avg, 1),
            'count': count,
            'details': {
                'dificultad': round(avg_result.avg_dificultad or 0, 1) if count > 0 else 0,
                'aprendizaje': round(avg_result.avg_aprendizaje or 0, 1) if count > 0 else 0,
                'recomendaria': round(avg_result.avg_recomendaria or 0, 1) if count > 0 else 0,
                'diversion': round(avg_result.avg_diversion or 0, 1) if count > 0 else 0
            },
            'user_rating': user_rating
        }

    @api_router.get("/completed_machines/{machine_name}")
    def api_get_completed_machines(request: Request, machine_name: str, session: dict = Depends(get_session)):
        user_id = session.get('user_id')
        if not user_id:
            return JSONResponse(status_code=401, content={"error": "Not authenticated"})

        completed = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
        return {"completed": completed is not None}

    @api_router.post("/toggle_completed_machine")
    async def api_toggle_completed_machine(request: Request, data: ToggleCompletedRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
        user_id = session.get('user_id')
        if not user_id:
            return JSONResponse(status_code=401, content={"error": "Not authenticated", "success": False})

        machine_name = data.machine_name.strip()
        if not machine_name:
            return JSONResponse(status_code=400, content={"error": "Machine name required", "success": False})

        if not Machine.query.filter_by(nombre=machine_name).first():
            return JSONResponse(status_code=400, content={"error": "Máquina no válida", "success": False})

        existing = CompletedMachine.query.filter_by(user_id=user_id, machine_name=machine_name).first()
        if existing:
            db.session.delete(existing)
            db.session.commit()
            return {"success": True, "completed": False}
        else:
            new_comp = CompletedMachine(user_id=user_id, machine_name=machine_name)
            db.session.add(new_comp)
            db.session.commit()
            return {"success": True, "completed": True}
