from .extensions import db
from datetime import datetime
from flask_login import UserMixin

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='jugador')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    recovery_pin_hash = db.Column(db.String(128))
    recovery_pin_plain = db.Column(db.String(20))
    recovery_pin_created_at = db.Column(db.DateTime)
    biography = db.Column(db.Text)
    linkedin_url = db.Column(db.String(255))
    github_url = db.Column(db.String(255))
    youtube_url = db.Column(db.String(255))

    __repr__ = lambda self: f'<User {self.username}>'

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
    posicion = db.Column(db.String, nullable=False, default='izquierda')

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
    url = db.Column(db.String, nullable=False)
    tipo = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('maquina', 'autor', 'url'),)

    def __repr__(self):
        return f'<Writeup {self.maquina} by {self.autor}>'

class PendingWriteup(db.Model):
    __tablename__ = 'writeups_recibidos'

    id = db.Column(db.Integer, primary_key=True)
    maquina = db.Column(db.String, nullable=False)
    autor = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    tipo = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PendingWriteup {self.maquina} by {self.autor}>'

class WriteupRanking(db.Model):
    __tablename__ = 'ranking_writeups'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, unique=True, nullable=False)
    puntos = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<WriteupRanking {self.nombre}: {self.puntos}>'

class WriteupReport(db.Model):
    __tablename__ = 'writeup_reports'

    id = db.Column(db.Integer, primary_key=True)
    writeup_id = db.Column(db.Integer, db.ForeignKey('writeups_subidos.id', ondelete='CASCADE'), nullable=False)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=False)
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
    url_original = db.Column(db.String, nullable=False)
    tipo_original = db.Column(db.String, nullable=False)
    
    maquina_nueva = db.Column(db.String, nullable=False)
    autor_nuevo = db.Column(db.String, nullable=False)
    url_nueva = db.Column(db.String, nullable=False)
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
    nuevos_datos = db.Column(db.String, nullable=False)
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


class Mensajeria(db.Model):
    __tablename__ = 'mensajeria'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    receiver_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    read = db.Column(db.Boolean, default=False)
    deleted_by_sender = db.Column(db.Boolean, default=False)
    deleted_by_receiver = db.Column(db.Boolean, default=False)

    sender = db.relationship('User', foreign_keys=[sender_id], backref=db.backref('sent_messages', lazy='dynamic'))
    receiver = db.relationship('User', foreign_keys=[receiver_id], backref=db.backref('received_messages', lazy='dynamic'))

    def __repr__(self):
        return f'<Message {self.id} from {self.sender_id} to {self.receiver_id}>'

