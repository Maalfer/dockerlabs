from dockerlabs.extensions import db
from datetime import datetime

# Note: BunkerUser and BunkerMachine removed - use dockerlabs.models.User and Machine instead
# Machine model now includes pin and guest_access fields for bunker functionality

class BunkerAccessToken(db.Model):
    __tablename__ = 'bunker_access_tokens'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String, nullable=False)
    token = db.Column(db.String, unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activo = db.Column(db.Integer, nullable=False, default=1)
    puntos = db.Column(db.Integer, nullable=False, default=0)
    last_accessed = db.Column(db.DateTime, nullable=True)                     

class BunkerAccessLog(db.Model):
    __tablename__ = 'bunker_access_logs'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('bunker_access_tokens.id'), nullable=False)
    user_nombre = db.Column(db.String, nullable=False)
    accessed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Optional: Relationship if needed
    # token = db.relationship('BunkerAccessToken', backref=db.backref('logs', lazy=True))

class BunkerWriteup(db.Model):
    """Writeups para máquinas de Entornos Reales en BunkerLabs"""
    __tablename__ = 'bunker_writeups'

    id = db.Column(db.Integer, primary_key=True)
    maquina = db.Column(db.String, nullable=False)
    autor = db.Column(db.String, nullable=False)
    url = db.Column(db.String, nullable=False)
    tipo = db.Column(db.String, nullable=False)  # 'texto' o 'video'
    locked = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_bunker_writeups_maquina', 'maquina'),
    )

    def __repr__(self):
        return f'<BunkerWriteup {self.maquina} by {self.autor}>'


class BunkerResource(db.Model):
    """Recursos compartidos en BunkerLabs (documentos, enlaces, etc.)"""
    __tablename__ = 'bunker_resources'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    url = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BunkerResource {self.titulo}>'
