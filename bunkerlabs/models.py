from dockerlabs.extensions import db
from datetime import datetime

class BunkerUser(db.Model):
    __bind_key__ = 'bunker'
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password_hash = db.Column(db.String, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class BunkerMachine(db.Model):
    __bind_key__ = 'bunker'
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
    pin = db.Column(db.String, nullable=True)
    guest_access = db.Column(db.Boolean, default=False)                          

    __table_args__ = (
        db.Index('idx_maquinas_autor', 'autor'),
        db.Index('idx_maquinas_dificultad', 'dificultad'),
    )

class BunkerAccessToken(db.Model):
    __bind_key__ = 'bunker'
    __tablename__ = 'bunker_access_tokens'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    token = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Integer, nullable=False, default=1)
    puntos = db.Column(db.Integer, nullable=False, default=0)
    last_accessed = db.Column(db.DateTime, nullable=True)                     

class BunkerSolve(db.Model):
                                                                   
    __bind_key__ = 'bunker'
    __tablename__ = 'bunker_solves'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)                                
    machine_id = db.Column(db.Integer, nullable=False)                    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('user_id', 'machine_id', name='unique_user_machine_solve'),
        db.Index('idx_bunker_solves_user', 'user_id'),
        db.Index('idx_bunker_solves_machine', 'machine_id'),
    )

class BunkerAccessLog(db.Model):
    __bind_key__ = 'bunker'
    __tablename__ = 'bunker_access_logs'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('bunker_access_tokens.id'), nullable=False)
    user_nombre = db.Column(db.String, nullable=False)
    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional: Relationship if needed
    # token = db.relationship('BunkerAccessToken', backref=db.backref('logs', lazy=True))

class BunkerWriteup(db.Model):
    """Writeups para máquinas de Entornos Reales en BunkerLabs"""
    __bind_key__ = 'bunker'
    __tablename__ = 'bunker_writeups'

    id = db.Column(db.Integer, primary_key=True)
    maquina = db.Column(db.String, nullable=False)
    autor = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    tipo = db.Column(db.String, nullable=False)  # 'texto' o 'video'
    locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.UniqueConstraint('maquina', 'autor', 'url', name='unique_bunker_writeup'),
        db.Index('idx_bunker_writeups_maquina', 'maquina'),
    )

    def __repr__(self):
        return f'<BunkerWriteup {self.maquina} by {self.autor}>'
