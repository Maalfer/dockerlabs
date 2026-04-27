import os
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from sqlalchemy import func

from dockerlabs.models import Team, TeamMember, TeamInvitation, TeamJoinRequest, User, WriteupRanking

# Constants
MAX_TEAM_MEMBERS = 5
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
TEAM_IMAGES_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'database', 'almacenamiento', 'equipos')


def ensure_team_images_dir():
    """Ensure the team images directory exists."""
    os.makedirs(TEAM_IMAGES_DIR, exist_ok=True)


# Pydantic Models
class CreateTeamRequest(BaseModel):
    nombre: str


class InviteUserRequest(BaseModel):
    team_id: int
    username: str


class RespondInvitationRequest(BaseModel):
    invitation_id: int
    accept: bool


class JoinTeamRequest(BaseModel):
    team_id: int


class RespondJoinRequest(BaseModel):
    request_id: int
    accept: bool


class RemoveMemberRequest(BaseModel):
    team_id: int
    user_id: int


class TeamResponse(BaseModel):
    id: int
    nombre: str
    imagen_url: Optional[str]
    member_count: int
    max_members: int
    puntos: int
    created_at: str


class TeamDetailResponse(BaseModel):
    id: int
    nombre: str
    imagen_url: Optional[str]
    created_at: str
    created_by: str
    members: List[dict]
    puntos: int


def register_equipos_routes(api_router, get_flask_session, verify_csrf_token, alchemy_db):
    """Register all team-related API routes."""

    def get_current_user_id(flask_session: dict) -> Optional[int]:
        return flask_session.get('user_id')

    @api_router.get("/equipos/ranking")
    def api_ranking_equipos(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Get team ranking based on total points from members' writeups."""
        teams = Team.query.all()

        team_list = []
        for team in teams:
            member_count = TeamMember.query.filter_by(team_id=team.id).count()
            if member_count == 0:
                continue

            # Calculate total points from team members
            members = TeamMember.query.filter_by(team_id=team.id).all()
            total_puntos = 0
            for member in members:
                user = User.query.get(member.user_id)
                if user:
                    ranking = WriteupRanking.query.filter(
                        func.lower(WriteupRanking.nombre) == func.lower(user.username)
                    ).first()
                    if ranking:
                        total_puntos += ranking.puntos

            team_list.append({
                'id': team.id,
                'nombre': team.nombre,
                'imagen_url': f"/api/equipos/{team.id}/imagen" if team.imagen_path else None,
                'member_count': member_count,
                'max_members': MAX_TEAM_MEMBERS,
                'puntos': total_puntos,
                'created_at': team.created_at.isoformat() if team.created_at else None
            })

        # Sort by points descending
        team_list.sort(key=lambda x: x['puntos'], reverse=True)

        return {"success": True, "equipos": team_list}

    @api_router.get("/equipos")
    def api_list_equipos(request: Request, flask_session: dict = Depends(get_flask_session)):
        """List all teams with member counts."""
        teams = Team.query.all()

        team_list = []
        for team in teams:
            member_count = TeamMember.query.filter_by(team_id=team.id).count()
            team_list.append({
                'id': team.id,
                'nombre': team.nombre,
                'imagen_url': f"/api/equipos/{team.id}/imagen" if team.imagen_path else None,
                'member_count': member_count,
                'max_members': MAX_TEAM_MEMBERS,
                'is_full': member_count >= MAX_TEAM_MEMBERS,
                'created_at': team.created_at.isoformat() if team.created_at else None
            })

        return {"success": True, "equipos": team_list}

    @api_router.get("/equipos/{team_id}")
    def api_get_equipo(team_id: int, request: Request, flask_session: dict = Depends(get_flask_session)):
        """Get detailed information about a team."""
        team = Team.query.get(team_id)
        if not team:
            return JSONResponse(status_code=404, content={"success": False, "message": "Equipo no encontrado"})

        # Get members with their details
        members = []
        total_puntos = 0
        team_members = TeamMember.query.filter_by(team_id=team_id).all()

        for tm in team_members:
            user = User.query.get(tm.user_id)
            if user:
                # Get user writeup points
                ranking = WriteupRanking.query.filter(
                    func.lower(WriteupRanking.nombre) == func.lower(user.username)
                ).first()
                puntos = ranking.puntos if ranking else 0
                total_puntos += puntos

                members.append({
                    'user_id': user.id,
                    'username': user.username,
                    'joined_at': tm.joined_at.isoformat() if tm.joined_at else None,
                    'puntos': puntos,
                    'profile_image_url': f"/img/perfil/{user.id}"
                })

        creator = User.query.get(team.created_by)

        return {
            "success": True,
            "team": {
                'id': team.id,
                'nombre': team.nombre,
                'imagen_url': f"/api/equipos/{team.id}/imagen" if team.imagen_path else None,
                'created_at': team.created_at.isoformat() if team.created_at else None,
                'created_by': creator.username if creator else 'Desconocido',
                'members': members,
                'puntos': total_puntos,
                'member_count': len(members),
                'max_members': MAX_TEAM_MEMBERS
            }
        }

    @api_router.get("/equipos/{team_id}/imagen")
    def api_get_equipo_imagen(team_id: int, request: Request):
        """Get team image."""
        team = Team.query.get(team_id)
        if not team or not team.imagen_path:
            # Return default image
            default_path = os.path.join(os.path.dirname(__file__), '..', '..', 'static', 'dockerlabs', 'images', 'balu.webp')
            if os.path.exists(default_path):
                return FileResponse(default_path)
            return JSONResponse(status_code=404, content={"success": False, "message": "Imagen no encontrada"})

        if os.path.exists(team.imagen_path):
            return FileResponse(team.imagen_path)

        return JSONResponse(status_code=404, content={"success": False, "message": "Imagen no encontrada"})

    @api_router.post("/equipos/crear")
    async def api_crear_equipo(
        request: Request,
        nombre: str = Form(...),
        imagen: Optional[UploadFile] = File(None),
        flask_session: dict = Depends(get_flask_session)
    ):
        """Create a new team."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        # Check if user already belongs to a team
        existing_membership = TeamMember.query.filter_by(user_id=user_id).first()
        if existing_membership:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Ya perteneces a un equipo. Debes salir de tu equipo actual primero."}
            )

        # Validate team name
        nombre = nombre.strip()
        if not nombre or len(nombre) < 3 or len(nombre) > 50:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "El nombre del equipo debe tener entre 3 y 50 caracteres"}
            )

        # Check if team name already exists
        existing = Team.query.filter(func.lower(Team.nombre) == func.lower(nombre)).first()
        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Ya existe un equipo con ese nombre"}
            )

        # Create team
        team = Team(nombre=nombre, created_by=user_id)
        alchemy_db.session.add(team)
        alchemy_db.session.flush()  # Get the team ID

        # Handle image upload
        imagen_path = None
        if imagen and imagen.filename:
            file_ext = os.path.splitext(imagen.filename)[1].lower()
            if file_ext not in ALLOWED_IMAGE_EXTENSIONS:
                alchemy_db.session.rollback()
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Formato de imagen no válido. Use: jpg, png, gif, webp"}
                )

            ensure_team_images_dir()
            unique_filename = f"team_{team.id}_{uuid.uuid4().hex}{file_ext}"
            imagen_path = os.path.join(TEAM_IMAGES_DIR, unique_filename)

            try:
                content = await imagen.read()
                with open(imagen_path, 'wb') as f:
                    f.write(content)
                team.imagen_path = imagen_path
            except Exception as e:
                alchemy_db.session.rollback()
                return JSONResponse(
                    status_code=500,
                    content={"success": False, "message": f"Error al guardar la imagen: {str(e)}"}
                )

        # Add creator as first member
        member = TeamMember(team_id=team.id, user_id=user_id)
        alchemy_db.session.add(member)

        try:
            alchemy_db.session.commit()
            return {
                "success": True,
                "message": "Equipo creado exitosamente",
                "team": {
                    'id': team.id,
                    'nombre': team.nombre,
                    'imagen_url': f"/api/equipos/{team.id}/imagen" if team.imagen_path else None
                }
            }
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Error al crear el equipo: {str(e)}"}
            )

    @api_router.post("/equipos/{team_id}/invitar")
    def api_invitar_usuario(
        team_id: int,
        request_data: InviteUserRequest,
        request: Request,
        flask_session: dict = Depends(get_flask_session)
    ):
        """Invite a user to join the team."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        # Check if user is team member
        membership = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
        if not membership:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "No eres miembro de este equipo"}
            )

        team = Team.query.get(team_id)
        if not team:
            return JSONResponse(status_code=404, content={"success": False, "message": "Equipo no encontrado"})

        # Check team capacity
        member_count = TeamMember.query.filter_by(team_id=team_id).count()
        if member_count >= MAX_TEAM_MEMBERS:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": f"El equipo ya tiene el máximo de {MAX_TEAM_MEMBERS} miembros"}
            )

        # Find invited user
        invited_user = User.query.filter(
            func.lower(User.username) == func.lower(request_data.username.strip())
        ).first()

        if not invited_user:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Usuario no encontrado"}
            )

        if invited_user.id == user_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "No puedes invitarte a ti mismo"}
            )

        # Check if user already belongs to the team
        existing_member = TeamMember.query.filter_by(team_id=team_id, user_id=invited_user.id).first()
        if existing_member:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "El usuario ya es miembro del equipo"}
            )

        # Check if user already belongs to another team
        other_membership = TeamMember.query.filter_by(user_id=invited_user.id).first()
        if other_membership:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "El usuario ya pertenece a otro equipo"}
            )

        # Check for existing pending invitation
        existing_inv = TeamInvitation.query.filter_by(
            team_id=team_id,
            invited_user_id=invited_user.id,
            status='pending'
        ).first()

        if existing_inv:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Ya existe una invitación pendiente para este usuario"}
            )

        # Create invitation
        invitation = TeamInvitation(
            team_id=team_id,
            invited_by=user_id,
            invited_user_id=invited_user.id
        )
        alchemy_db.session.add(invitation)

        try:
            alchemy_db.session.commit()
            return {
                "success": True,
                "message": f"Invitación enviada a {invited_user.username}",
                "invitation_id": invitation.id
            }
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Error al enviar invitación: {str(e)}"}
            )

    @api_router.post("/equipos/invitaciones/responder")
    def api_responder_invitacion(
        request_data: RespondInvitationRequest,
        request: Request,
        flask_session: dict = Depends(get_flask_session)
    ):
        """Accept or reject a team invitation."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        invitation = TeamInvitation.query.filter_by(
            id=request_data.invitation_id,
            invited_user_id=user_id,
            status='pending'
        ).first()

        if not invitation:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Invitación no encontrada"}
            )

        if request_data.accept:
            # Check if user already belongs to a team
            existing = TeamMember.query.filter_by(user_id=user_id).first()
            if existing:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "Ya perteneces a un equipo"}
                )

            # Check team capacity
            member_count = TeamMember.query.filter_by(team_id=invitation.team_id).count()
            if member_count >= MAX_TEAM_MEMBERS:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "El equipo ya está completo"}
                )

            # Add user to team
            member = TeamMember(team_id=invitation.team_id, user_id=user_id)
            alchemy_db.session.add(member)
            invitation.status = 'accepted'
            invitation.responded_at = datetime.utcnow()
            message = "Te has unido al equipo"
        else:
            invitation.status = 'rejected'
            invitation.responded_at = datetime.utcnow()
            message = "Invitación rechazada"

        try:
            alchemy_db.session.commit()
            return {"success": True, "message": message}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Error al procesar la invitación: {str(e)}"}
            )

    @api_router.get("/equipos/invitaciones/mis-invitaciones")
    def api_mis_invitaciones(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Get pending invitations for current user."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        invitations = TeamInvitation.query.filter_by(
            invited_user_id=user_id,
            status='pending'
        ).order_by(TeamInvitation.created_at.desc()).all()

        result = []
        for inv in invitations:
            team = Team.query.get(inv.team_id)
            inviter = User.query.get(inv.invited_by)
            member_count = TeamMember.query.filter_by(team_id=inv.team_id).count()

            if team:
                result.append({
                    'id': inv.id,
                    'team': {
                        'id': team.id,
                        'nombre': team.nombre,
                        'imagen_url': f"/api/equipos/{team.id}/imagen" if team.imagen_path else None,
                        'member_count': member_count,
                        'max_members': MAX_TEAM_MEMBERS
                    },
                    'invited_by': inviter.username if inviter else 'Desconocido',
                    'created_at': inv.created_at.isoformat() if inv.created_at else None
                })

        return {"success": True, "invitaciones": result}

    @api_router.post("/equipos/{team_id}/solicitar-unirse")
    def api_solicitar_unirse(
        team_id: int,
        request: Request,
        flask_session: dict = Depends(get_flask_session)
    ):
        """Request to join a team."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        # Check if user already belongs to a team
        existing = TeamMember.query.filter_by(user_id=user_id).first()
        if existing:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Ya perteneces a un equipo"}
            )

        team = Team.query.get(team_id)
        if not team:
            return JSONResponse(status_code=404, content={"success": False, "message": "Equipo no encontrado"})

        # Check team capacity
        member_count = TeamMember.query.filter_by(team_id=team_id).count()
        if member_count >= MAX_TEAM_MEMBERS:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "El equipo ya está completo"}
            )

        # Check for existing pending request
        existing_req = TeamJoinRequest.query.filter_by(
            team_id=team_id,
            user_id=user_id,
            status='pending'
        ).first()

        if existing_req:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "Ya tienes una solicitud pendiente para este equipo"}
            )

        # Create join request
        join_request = TeamJoinRequest(team_id=team_id, user_id=user_id)
        alchemy_db.session.add(join_request)

        try:
            alchemy_db.session.commit()
            return {
                "success": True,
                "message": "Solicitud enviada. Espera a que un miembro del equipo la acepte.",
                "request_id": join_request.id
            }
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Error al enviar solicitud: {str(e)}"}
            )

    @api_router.get("/equipos/{team_id}/solicitudes")
    def api_get_solicitudes(team_id: int, request: Request, flask_session: dict = Depends(get_flask_session)):
        """Get pending join requests for a team (team members only)."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        # Check if user is team member
        membership = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
        if not membership:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "No eres miembro de este equipo"}
            )

        requests = TeamJoinRequest.query.filter_by(team_id=team_id, status='pending').all()

        result = []
        for req in requests:
            user = User.query.get(req.user_id)
            if user:
                ranking = WriteupRanking.query.filter(
                    func.lower(WriteupRanking.nombre) == func.lower(user.username)
                ).first()
                result.append({
                    'id': req.id,
                    'user': {
                        'id': user.id,
                        'username': user.username,
                        'profile_image_url': f"/img/perfil/{user.id}",
                        'puntos': ranking.puntos if ranking else 0
                    },
                    'created_at': req.created_at.isoformat() if req.created_at else None
                })

        return {"success": True, "solicitudes": result}

    @api_router.post("/equipos/solicitudes/responder")
    def api_responder_solicitud(
        request_data: RespondJoinRequest,
        request: Request,
        flask_session: dict = Depends(get_flask_session)
    ):
        """Accept or reject a join request (team members only)."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        join_request = TeamJoinRequest.query.filter_by(
            id=request_data.request_id,
            status='pending'
        ).first()

        if not join_request:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Solicitud no encontrada"}
            )

        # Check if current user is team member
        membership = TeamMember.query.filter_by(
            team_id=join_request.team_id,
            user_id=user_id
        ).first()

        if not membership:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "No tienes permisos para responder esta solicitud"}
            )

        if request_data.accept:
            # Check team capacity
            member_count = TeamMember.query.filter_by(team_id=join_request.team_id).count()
            if member_count >= MAX_TEAM_MEMBERS:
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "El equipo ya está completo"}
                )

            # Check if user is already in a team (might have joined another while waiting)
            existing = TeamMember.query.filter_by(user_id=join_request.user_id).first()
            if existing:
                join_request.status = 'rejected'
                join_request.responded_at = datetime.utcnow()
                alchemy_db.session.commit()
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "message": "El usuario ya pertenece a otro equipo"}
                )

            # Add user to team
            member = TeamMember(team_id=join_request.team_id, user_id=join_request.user_id)
            alchemy_db.session.add(member)
            join_request.status = 'accepted'
            join_request.responded_at = datetime.utcnow()
            message = "Usuario añadido al equipo"
        else:
            join_request.status = 'rejected'
            join_request.responded_at = datetime.utcnow()
            message = "Solicitud rechazada"

        try:
            alchemy_db.session.commit()
            return {"success": True, "message": message}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Error al procesar la solicitud: {str(e)}"}
            )

    @api_router.post("/equipos/{team_id}/eliminar-miembro")
    def api_eliminar_miembro(
        team_id: int,
        request_data: RemoveMemberRequest,
        request: Request,
        flask_session: dict = Depends(get_flask_session)
    ):
        """Remove a member from the team (any team member can remove others)."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        # Check if requester is team member
        membership = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
        if not membership:
            return JSONResponse(
                status_code=403,
                content={"success": False, "message": "No eres miembro de este equipo"}
            )

        # Cannot remove yourself through this endpoint (use leave team instead)
        if request_data.user_id == user_id:
            return JSONResponse(
                status_code=400,
                content={"success": False, "message": "No puedes eliminarte a ti mismo. Usa 'Salir del equipo'."}
            )

        # Find member to remove
        member_to_remove = TeamMember.query.filter_by(
            team_id=team_id,
            user_id=request_data.user_id
        ).first()

        if not member_to_remove:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "Miembro no encontrado"}
            )

        alchemy_db.session.delete(member_to_remove)

        try:
            alchemy_db.session.commit()
            return {"success": True, "message": "Miembro eliminado del equipo"}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Error al eliminar miembro: {str(e)}"}
            )

    @api_router.post("/equipos/{team_id}/salir")
    def api_salir_equipo(team_id: int, request: Request, flask_session: dict = Depends(get_flask_session)):
        """Leave a team. If last member, the team is deleted."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        membership = TeamMember.query.filter_by(team_id=team_id, user_id=user_id).first()
        if not membership:
            return JSONResponse(
                status_code=404,
                content={"success": False, "message": "No eres miembro de este equipo"}
            )

        team = Team.query.get(team_id)
        member_count = TeamMember.query.filter_by(team_id=team_id).count()

        # Remove membership
        alchemy_db.session.delete(membership)

        # If last member, delete the team
        if member_count <= 1:
            if team:
                # Delete team image if exists
                if team.imagen_path and os.path.exists(team.imagen_path):
                    try:
                        os.remove(team.imagen_path)
                    except:
                        pass
                alchemy_db.session.delete(team)
            message = "Has salido del equipo. El equipo ha sido eliminado."
        else:
            message = "Has salido del equipo"

        try:
            alchemy_db.session.commit()
            return {"success": True, "message": message}
        except Exception as e:
            alchemy_db.session.rollback()
            return JSONResponse(
                status_code=500,
                content={"success": False, "message": f"Error al salir del equipo: {str(e)}"}
            )

    @api_router.get("/equipos/mi-equipo/info")
    def api_mi_equipo(request: Request, flask_session: dict = Depends(get_flask_session)):
        """Get current user's team info if they belong to one."""
        user_id = get_current_user_id(flask_session)
        if not user_id:
            return JSONResponse(status_code=401, content={"success": False, "message": "Debes iniciar sesión"})

        membership = TeamMember.query.filter_by(user_id=user_id).first()
        if not membership:
            return {"success": True, "tiene_equipo": False}

        team = Team.query.get(membership.team_id)
        if not team:
            return {"success": True, "tiene_equipo": False}

        # Get members
        members = []
        total_puntos = 0
        team_members = TeamMember.query.filter_by(team_id=team.id).all()

        for tm in team_members:
            user = User.query.get(tm.user_id)
            if user:
                ranking = WriteupRanking.query.filter(
                    func.lower(WriteupRanking.nombre) == func.lower(user.username)
                ).first()
                puntos = ranking.puntos if ranking else 0
                total_puntos += puntos

                members.append({
                    'user_id': user.id,
                    'username': user.username,
                    'is_me': user.id == user_id,
                    'joined_at': tm.joined_at.isoformat() if tm.joined_at else None,
                    'puntos': puntos,
                    'profile_image_url': f"/img/perfil/{user.id}"
                })

        creator = User.query.get(team.created_by)

        return {
            "success": True,
            "tiene_equipo": True,
            "team": {
                'id': team.id,
                'nombre': team.nombre,
                'imagen_url': f"/api/equipos/{team.id}/imagen" if team.imagen_path else None,
                'created_at': team.created_at.isoformat() if team.created_at else None,
                'created_by': creator.username if creator else 'Desconocido',
                'members': members,
                'puntos': total_puntos,
                'member_count': len(members),
                'max_members': MAX_TEAM_MEMBERS
            }
        }

