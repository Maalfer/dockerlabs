from .extensions import db as alchemy_db
from .models import User, Machine, Category, Mensajeria
from bunkerlabs.models import BunkerAccessToken, BunkerSolve, BunkerAccessLog, BunkerWriteup

def init_db():
    alchemy_db.create_all()

