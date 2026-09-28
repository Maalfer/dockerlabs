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
