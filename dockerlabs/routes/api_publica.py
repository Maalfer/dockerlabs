"""Endpoints de la API publica: resumen, rankings y envio de maquinas."""

from datetime import datetime
from typing import List, Optional

from fastapi import Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func

from dockerlabs.extensions import db
from dockerlabs.models import (
    User,
    Machine,
    Writeup,
    PendingMachineSubmission,
    CreatorRanking,
    WriteupRanking,
)


class AutorRankingResponse(BaseModel):
    id: int
    nombre: str
    maquinas: int
    autor: str
    imagen: str

class WriteupRankingResponse(BaseModel):
    id: int
    nombre: str
    puntos: int
    imagen_url: str

class MaquinaInfoResponse(BaseModel):
    id: int
    nombre: str
    dificultad: str
    clase: str
    color: str
    autor: str
    enlace_autor: str
    fecha: str
    imagen: str
    descripcion: str
    link_descarga: str
    imagen_url: Optional[str] = None

class MetadataResponse(BaseModel):
    total_creadores: int
    total_puntos: int
    total_writeups: int

class WriteupBasicResponse(BaseModel):
    id: int
    maquina: str
    autor: str
    url: str
    tipo: str
    created_at: Optional[datetime] = None

class WriteupsCategoriaResponse(BaseModel):
    textos: List[WriteupBasicResponse]
    videos: List[WriteupBasicResponse]

class RankingCreadorBasic(BaseModel):
    id: int
    nombre: str
    maquinas: int

class RankingWriteupBasic(BaseModel):
    id: int
    nombre: str
    puntos: int

class ApiSummaryResponse(BaseModel):
    info_maquinas: List[MaquinaInfoResponse]
    maquinas: List[str]
    metadata: MetadataResponse
    ranking_creadores: List[RankingCreadorBasic]
    ranking_writeups: List[RankingWriteupBasic]
    writeups: WriteupsCategoriaResponse

class SubmitMachineRequest(BaseModel):
    nombre: str
    link_maquina: str
    dificultad: str
    discord_user: str
    categoria: Optional[str] = None
    tags: Optional[str] = None
    descripcion: Optional[str] = None
    notas: Optional[str] = None
    writeup_url: Optional[str] = None

class SubmitMachineResponse(BaseModel):
    success: Optional[bool] = None
    message: Optional[str] = None
    error: Optional[str] = None


def register_api_publica_routes(api_router, get_session, verify_csrf_token, get_fastapi_profile_image_url):
    """Registra las rutas de este modulo en el router recibido."""

    def resolver_usuarios_por_nombre(nombres):
        """Mapa nombre-en-minusculas -> User, resuelto de forma determinista.

        Hay usernames que solo se diferencian en mayusculas (Juan/juan, admin/admiN),
        asi que un JOIN por lower() es ambiguo: SQLAlchemy avisa con
        "Multiple rows returned with uselist=False" y elige uno al azar, con lo que
        el avatar mostrado puede ser el de la cuenta equivocada.

        Aqui se resuelve en una sola consulta y con criterio fijo: primero la
        coincidencia exacta de mayusculas y, si no la hay, el id mas bajo.
        """
        claves = {n.lower() for n in nombres if n}
        if not claves:
            return {}

        usuarios = db.session.query(User).filter(func.lower(User.username).in_(claves)).all()

        candidatos = {}
        for u in sorted(usuarios, key=lambda x: x.id):
            candidatos.setdefault((u.username or '').lower(), []).append(u)

        resultado = {}
        for nombre in nombres:
            if not nombre:
                continue
            clave = nombre.lower()
            posibles = candidatos.get(clave)
            if not posibles:
                continue
            exacto = next((u for u in posibles if u.username == nombre), None)
            resultado[clave] = exacto or posibles[0]
        return resultado

    @api_router.get("", response_model=ApiSummaryResponse)
    def api_summary(request: Request):
    
        maquinas_objs = Machine.query.filter_by(origen='docker').order_by(Machine.id.asc()).all()
        info_maquinas = []
        maquinas_names = []
        for m in maquinas_objs:
            d = {
                'id': m.id,
                'nombre': m.nombre,
                'dificultad': m.dificultad,
                'clase': m.clase,
                'color': m.color,
                'autor': m.autor,
                'enlace_autor': m.enlace_autor,
                'fecha': m.fecha,
                'imagen': m.imagen,
                'descripcion': m.descripcion,
                'link_descarga': m.link_descarga
            }
            if d['imagen']:
                d['imagen_url'] = f"/static/dockerlabs/{d['imagen']}"
            info_maquinas.append(d)
            maquinas_names.append(d['nombre'])

        creadores_objs = CreatorRanking.query.order_by(CreatorRanking.maquinas.desc(), func.lower(CreatorRanking.nombre).asc()).all()
        ranking_creadores = [{'id': r.id, 'nombre': r.nombre, 'maquinas': r.maquinas} for r in creadores_objs]

        ranking_w_objs = WriteupRanking.query.order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc()).all()
        ranking_writeups = [{'id': r.id, 'nombre': r.nombre, 'puntos': r.puntos} for r in ranking_w_objs]

        writeups_objs = Writeup.query.order_by(Writeup.created_at.desc()).all()
        writeups_textos = []
        writeups_videos = []
        for w in writeups_objs:
            d = {
                'id': w.id,
                'maquina': w.maquina,
                'autor': w.autor,
                'url': w.url,
                'tipo': w.tipo,
                'created_at': w.created_at
            }
            if w.tipo == 'texto':
                writeups_textos.append(d)
            else:
                writeups_videos.append(d)

        total_creadores = len(ranking_creadores)
        total_puntos = sum(r['puntos'] for r in ranking_writeups)
        total_writeups = len(writeups_objs)

        metadata = {
            "total_creadores": total_creadores,
            "total_puntos": total_puntos,
            "total_writeups": total_writeups
        }

        response = {
            "info_maquinas": info_maquinas,
            "maquinas": maquinas_names,
            "metadata": metadata,
            "ranking_creadores": ranking_creadores,
            "ranking_writeups": ranking_writeups,
            "writeups": {
                "textos": writeups_textos,
                "videos": writeups_videos
            }
        }

        return response

    @api_router.get("/ranking_autores", response_model=List[AutorRankingResponse])
    def api_ranking_autores(request: Request):
        results = db.session.query(CreatorRanking) \
            .order_by(CreatorRanking.maquinas.desc(), func.lower(CreatorRanking.nombre).asc()) \
            .all()

        usuarios = resolver_usuarios_por_nombre([c.nombre for c in results])

        response_list = []
        for creator in results:
            usuario = usuarios.get((creator.nombre or '').lower())
            response_list.append({
                'id': creator.id,
                'nombre': creator.nombre,
                'maquinas': creator.maquinas,
                'autor': creator.nombre,
                'imagen': get_fastapi_profile_image_url(
                    username=creator.nombre,
                    user_id=usuario.id if usuario else None,
                ),
            })

        return response_list

    @api_router.get("/ranking_writeups", response_model=List[WriteupRankingResponse])
    def api_ranking_writeups(request: Request):
        results = db.session.query(WriteupRanking) \
            .order_by(WriteupRanking.puntos.desc(), func.lower(WriteupRanking.nombre).asc()) \
            .all()

        usuarios = resolver_usuarios_por_nombre([r.nombre for r in results])

        response_list = []
        for rank in results:
            usuario = usuarios.get((rank.nombre or '').lower())
            response_list.append({
                'id': rank.id,
                'nombre': rank.nombre,
                'puntos': rank.puntos,
                'imagen_url': get_fastapi_profile_image_url(
                    username=rank.nombre,
                    user_id=usuario.id if usuario else None,
                ),
            })

        return response_list

    @api_router.post("/submit-machine", response_model=SubmitMachineResponse)
    async def api_submit_machine(request: Request, data: SubmitMachineRequest, session: dict = Depends(get_session), csrf_ok: bool = Depends(verify_csrf_token)):
        user_id = session.get('user_id')
        if not user_id:
            return JSONResponse(status_code=401, content={"error": "Debes iniciar sesión"})

        username = session.get("username")

        # Validacion de entrada ANTES de persistir. El nombre se renderiza en un
        # onclick de la cola de revision (contexto JS); rechazamos metacaracteres
        # HTML/JS y caracteres de control. Ademas validamos que las URLs no usen
        # esquemas peligrosos (javascript:, data:, ...).
        from dockerlabs import validators
        nombre_raw = (data.nombre or "").strip()
        _bad = set('<>"\'`\\')
        if not nombre_raw:
            return JSONResponse(status_code=400, content={"error": "El nombre de la maquina es obligatorio"})
        if len(nombre_raw) > 100:
            return JSONResponse(status_code=400, content={"error": "El nombre de la maquina es demasiado largo (maximo 100 caracteres)"})
        if any(c in _bad for c in nombre_raw) or any(ord(c) < 32 or ord(c) == 127 for c in nombre_raw):
            return JSONResponse(status_code=400, content={"error": "El nombre de la maquina contiene caracteres no permitidos"})
        for _campo, _valor in (("link_maquina", data.link_maquina), ("writeup_url", data.writeup_url)):
            if _valor and _valor.strip():
                _oku, _erru = validators.validate_url(_valor.strip())
                if not _oku:
                    return JSONResponse(status_code=400, content={"error": f"{_campo}: {_erru}"})

        sub = PendingMachineSubmission(
            nombre=nombre_raw,
            link_maquina=data.link_maquina,
            dificultad=data.dificultad,
            categoria=data.categoria,
            tags=data.tags,
            descripcion=data.descripcion,
            notas=data.notas,
            writeup_url=data.writeup_url,
            discord_user=data.discord_user,
            autor_solicitante=username,
            estado="pendiente"
        )
        db.session.add(sub)
        db.session.commit()

        return {"success": True, "message": "Máquina enviada y pendiente de revisión"}
