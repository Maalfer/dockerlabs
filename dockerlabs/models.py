from .extensions import db
from datetime import datetime
from sqlalchemy.orm import deferred
from sqlalchemy import func

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='jugador')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Identificador público del perfil (`/u/<slug>`). Lo asignan y mantienen
    # sincronizado con `username` los eventos de dockerlabs/slugs.py.
    slug = db.Column(db.String(64), unique=True, nullable=True)

    biography = db.Column(db.Text)
    nombre_diploma = db.Column(db.String(100), nullable=True)
    linkedin_url = db.Column(db.String(512))
    github_url = db.Column(db.String(512))
    youtube_url = db.Column(db.String(512))

    # Imagen de perfil almacenada en archivo (nuevo sistema)
    profile_image_path = db.Column(db.String(255), nullable=True)
    # Mantener compatibilidad con datos antiguos en BD
    profile_image_data = deferred(db.Column(db.LargeBinary, nullable=True))
    profile_image_mime = deferred(db.Column(db.String(50), nullable=True))

    __table_args__ = (
        db.Index('idx_users_username', 'username'),
        db.Index('idx_users_email', 'email'),
        db.Index('idx_users_role', 'role'),
    )

    __repr__ = lambda self: f'<User {self.username}>'

class Certificate(db.Model):
    """Certificado de finalización ya emitido, con su PDF archivado en disco.

    Se crea al generar el diploma desde `/api/certificado/<maquina>`; el PDF
    persiste en `uploads/certificados/` para servirlo después sin re-renderizar.
    """
    __tablename__ = 'certificados'

    id = db.Column(db.Integer, primary_key=True)
    # Único: solo son 24 bits de hash y las colisiones ocurren de verdad.
    # allocate_cert_id() elige el primer candidato libre del digest.
    cert_id = db.Column(db.String(16), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    username = db.Column(db.String(64), nullable=False)
    machine_name = db.Column(db.String(191), nullable=False)
    pdf_path = db.Column(db.String(255), nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('certificados', cascade='all, delete-orphan'))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'machine_name', name='idx_certificados_uniq'),
        db.Index('idx_certificados_user_id', 'user_id'),
    )

    def __repr__(self):
        return f'<Certificate {self.cert_id} {self.username}/{self.machine_name}>'

class Machine(db.Model):
    __tablename__ = 'maquinas'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, unique=True, nullable=False)
    dificultad = db.Column(db.String, nullable=False)
    clase = db.Column(db.String, nullable=False)
    color = db.Column(db.String, nullable=False)
    autor = db.Column(db.String, nullable=False)
    enlace_autor = db.Column(db.String, nullable=False)
    fecha = db.Column(db.String, nullable=False)
    imagen = db.Column(db.String, nullable=False)
    descripcion = db.Column(db.Text, nullable=False)
    link_descarga = db.Column(db.String, nullable=False)
    guest_access = db.Column(db.Boolean, default=False)
    origen = db.Column(db.String, nullable=False, default='docker')

    # Logo almacenado en archivo (nuevo sistema)
    logo_path = db.Column(db.String(255), nullable=True)
    # Mantener compatibilidad con datos antiguos en BD
    logo_data = deferred(db.Column(db.LargeBinary, nullable=True))
    logo_mime = deferred(db.Column(db.String(50), nullable=True))

    # Script .py de los labs de la sección "Empezar de 0" (origen='empezar')
    script_path = db.Column(db.String(255), nullable=True)

    __table_args__ = (
        db.Index('idx_maquinas_autor', 'autor'),
        db.Index('idx_maquinas_dificultad', 'dificultad'),
    )

    def __repr__(self):
        return f'<Machine {self.nombre}>'

class Category(db.Model):
    __tablename__ = 'categorias'

    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, nullable=False)
    origen = db.Column(db.String, nullable=False)
    categoria = db.Column(db.String, nullable=False)
    
    __table_args__ = (db.UniqueConstraint('machine_id', 'origen'),)

    def __repr__(self):
        return f'<Category {self.categoria} for {self.origen}:{self.machine_id}>'

class Writeup(db.Model):
    __tablename__ = 'writeups_subidos'

    id = db.Column(db.Integer, primary_key=True)
    maquina = db.Column(db.String, nullable=False)
    autor = db.Column(db.String, nullable=False)
    url = db.Column(db.String(2048), nullable=False)
    tipo = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_writeups_maquina', 'maquina'),
        db.Index('idx_writeups_autor', 'autor'),
        db.Index('idx_writeups_tipo', 'tipo'),
        db.Index('idx_writeups_created_at', 'created_at'),
    )

    def __repr__(self):
        return f'<Writeup {self.maquina} by {self.autor}>'

class PendingWriteup(db.Model):
    __tablename__ = 'writeups_recibidos'

    id = db.Column(db.Integer, primary_key=True)
    maquina = db.Column(db.String, nullable=False)
    autor = db.Column(db.String, nullable=False)
    url = db.Column(db.String(2048), nullable=False)
    tipo = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PendingWriteup {self.maquina} by {self.autor}>'

class WriteupRanking(db.Model):
    __tablename__ = 'ranking_writeups'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, unique=True, nullable=False)
    puntos = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', foreign_keys=[nombre], primaryjoin=lambda: func.lower(User.username) == func.lower(WriteupRanking.nombre))

    def __repr__(self):
        return f'<WriteupRanking {self.nombre}: {self.puntos}>'

class WriteupReport(db.Model):
    __tablename__ = 'writeup_reports'

    id = db.Column(db.Integer, primary_key=True)
    writeup_id = db.Column(db.Integer, db.ForeignKey('writeups_subidos.id', ondelete='CASCADE'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    writeup = db.relationship('Writeup', backref=db.backref('reports', cascade='all, delete-orphan'))
    reporter = db.relationship('User', backref='reported_writeups')

    def __repr__(self):
        return f'<WriteupReport {self.id} for Writeup {self.writeup_id}>'

class WriteupEditRequest(db.Model):
    __tablename__ = 'writeup_edit_requests'

    id = db.Column(db.Integer, primary_key=True)
    writeup_id = db.Column(db.Integer, nullable=False)                                                                                        
    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String, nullable=False)
    
    maquina_original = db.Column(db.String, nullable=False)
    autor_original = db.Column(db.String, nullable=False)
    url_original = db.Column(db.String(2048), nullable=False)
    tipo_original = db.Column(db.String, nullable=False)

    maquina_nueva = db.Column(db.String, nullable=False)
    autor_nuevo = db.Column(db.String, nullable=False)
    url_nueva = db.Column(db.String(2048), nullable=False)
    tipo_nuevo = db.Column(db.String, nullable=False)
    
    estado = db.Column(db.String, nullable=False, default='pendiente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<WriteupEditRequest {self.id} for {self.writeup_id}>'

class CreatorRanking(db.Model):
    __tablename__ = 'ranking_creadores'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, unique=True, nullable=False)
    maquinas = db.Column(db.Integer, nullable=False)

    user = db.relationship('User', foreign_keys=[nombre], primaryjoin=lambda: func.lower(User.username) == func.lower(CreatorRanking.nombre))

class MachineClaim(db.Model):
    __tablename__ = 'maquina_claims'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String, nullable=False)
    maquina_nombre = db.Column(db.String, nullable=False)
    contacto = db.Column(db.String, nullable=False)
    prueba = db.Column(db.String, nullable=False)
    estado = db.Column(db.String, nullable=False, default='pendiente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class NameClaim(db.Model):
    __tablename__ = 'nombre_claims'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    nombre_solicitado = db.Column(db.String, nullable=False)
    nombre_actual = db.Column(db.String, nullable=False)
    motivo = db.Column(db.String, nullable=False)
    estado = db.Column(db.String, nullable=False, default='pendiente')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class MachineEditRequest(db.Model):
    __tablename__ = 'machine_edit_requests'
    id = db.Column(db.Integer, primary_key=True)

    machine_id = db.Column(db.Integer, nullable=False) 
    origen = db.Column(db.String, nullable=False)
    autor = db.Column(db.String, nullable=False)
    nuevos_datos = db.Column(db.Text, nullable=False)
    estado = db.Column(db.String, nullable=False, default='pendiente')
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class UsernameChangeRequest(db.Model):
    __tablename__ = 'username_change_requests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    old_username = db.Column(db.String, nullable=False)
    requested_username = db.Column(db.String, nullable=False)
    reason = db.Column(db.String)
    contacto_opcional = db.Column(db.String)
    estado = db.Column(db.String, nullable=False, default='pendiente')

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    processed_by = db.Column(db.Integer)
    processed_at = db.Column(db.DateTime)           
    decision_reason = db.Column(db.String)

class Rating(db.Model):
    __tablename__ = 'puntuaciones'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False)
    maquina_nombre = db.Column(db.String, nullable=False)
    dificultad_score = db.Column(db.Integer)
    aprendizaje_score = db.Column(db.Integer)
    recomendaria_score = db.Column(db.Integer)
    diversion_score = db.Column(db.Integer)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('usuario_id', 'maquina_nombre', name='idx_puntuaciones_uniq'),
    )

class CompletedMachine(db.Model):
    __tablename__ = 'maquinas_hechas'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    machine_name = db.Column(db.String, nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    __table_args__ = (
        db.UniqueConstraint('user_id', 'machine_name', name='idx_maquinas_hechas_uniq'),

        db.Index('idx_maquinas_hechas_user_id', 'user_id'),
    )
                           
    user = db.relationship('User', backref=db.backref('completed_machines_rel', cascade='all, delete-orphan'))

class PendingMachineSubmission(db.Model):
    __tablename__ = 'pending_machine_submissions'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    link_maquina = db.Column(db.String, nullable=False)
    dificultad = db.Column(db.String, nullable=False)
    categoria = db.Column(db.String)
    tags = db.Column(db.String)
    descripcion = db.Column(db.Text)
    notas = db.Column(db.Text)
    writeup_url = db.Column(db.String)
    discord_user = db.Column(db.String, nullable=False)
    autor_solicitante = db.Column(db.String)
    estado = db.Column(
        db.String,
        default="pendiente"
    )

    submitted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    reviewed_by = db.Column(db.Integer)
    reviewed_at = db.Column(db.DateTime)

class Notification(db.Model):
    __tablename__ = 'notificaciones'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    notification_type = db.Column(db.String(50), nullable=True)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_notifications', lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_notifications', lazy='dynamic'))

    __table_args__ = (
        db.Index('idx_notificaciones_sender_id', 'sender_id'),
        db.Index('idx_notificaciones_receiver_id', 'receiver_id'),
        db.Index('idx_notificaciones_created_at', 'created_at'),
        db.Index('idx_notificaciones_read', 'read'),
        db.Index('idx_notifications_type', 'notification_type'),
    )

    def __repr__(self):
        return f'<Notification {self.id}: {self.title}>'



class NotificationReaction(db.Model):
    __tablename__ = 'notification_reactions'
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('notificaciones.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    emoji = db.Column(db.String(10), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    notification = db.relationship('Notification', backref=db.backref('reactions', cascade='all, delete-orphan'))
    user = db.relationship('User', backref='notification_reactions')

    __table_args__ = (
        db.UniqueConstraint('notification_id', 'user_id', 'emoji', name='idx_notif_reaction_uniq'),
        db.Index('idx_notif_reactions_notification_id', 'notification_id'),
        db.Index('idx_notif_reactions_user_id', 'user_id'),
    )

    def __repr__(self):
        return f'<NotificationReaction notif={self.notification_id} user={self.user_id} emoji={self.emoji}>'

class NotificationRead(db.Model):
    """Estado 'leído' por usuario para notificaciones globales (broadcast).
    Las notificaciones dirigidas usan la columna Notification.read; las
    globales (receiver_id=NULL) comparten fila, así que el leído por-usuario
    se registra aquí."""
    __tablename__ = 'notification_reads'
    id = db.Column(db.Integer, primary_key=True)
    notification_id = db.Column(db.Integer, db.ForeignKey('notificaciones.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('notification_id', 'user_id', name='idx_notif_read_uniq'),
        db.Index('idx_notif_reads_user_id', 'user_id'),
    )


class SessionConfig(db.Model):
    """Almacena la clave secreta de sesión persistente en la base de datos."""
    __tablename__ = 'session_config'

    id = db.Column(db.Integer, primary_key=True)
    secret_key = db.Column(db.String(64), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def get_or_create_secret_key():
        """Obtiene la clave existente o genera una nueva si no existe."""
        config = SessionConfig.query.first()
        if not config:
            import secrets
            config = SessionConfig(secret_key=secrets.token_hex(32))
            db.session.add(config)
            db.session.commit()
        return config.secret_key

    def __repr__(self):
        return f'<SessionConfig id={self.id}>'



class EmailVerificationToken(db.Model):
    __tablename__ = 'email_verification_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    username = db.Column(db.String(32), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    __table_args__ = (
        db.Index('idx_email_verification_token', 'token'),
        db.Index('idx_email_verification_email', 'email'),
    )

    def __repr__(self):
        return f'<EmailVerificationToken for {self.username}>'


class PasswordResetToken(db.Model):
    __tablename__ = 'password_reset_tokens'

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(64), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False)

    user = db.relationship('User', backref=db.backref('reset_tokens', cascade='all, delete-orphan'))

    __table_args__ = (
        db.Index('idx_password_reset_token', 'token'),
        db.Index('idx_password_reset_user_id', 'user_id'),
    )

    def __repr__(self):
        return f'<PasswordResetToken for user_id={self.user_id}>'


class WriteupAnalysisResult(db.Model):
    __tablename__ = 'writeup_analysis_results'

    id = db.Column(db.Integer, primary_key=True)
    writeup_id = db.Column(db.Integer, nullable=False)
    maquina = db.Column(db.String(200))
    autor = db.Column(db.String(200))
    url = db.Column(db.String(2000))
    tipo = db.Column(db.String(50))
    status = db.Column(db.Integer, nullable=True)
    error = db.Column(db.String(200), nullable=True)
    dismissed = db.Column(db.Boolean, default=False, nullable=False)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_analysis_writeup_id', 'writeup_id'),
        db.Index('idx_analysis_dismissed', 'dismissed'),
    )

    def __repr__(self):
        return f'<WriteupAnalysisResult writeup_id={self.writeup_id} dismissed={self.dismissed}>'


# Mantiene `User.slug` sincronizado con `User.username` en cualquier alta o
# renombrado, sea cual sea el módulo que lo provoque.
from dockerlabs.slugs import register_slug_events

register_slug_events(User)
