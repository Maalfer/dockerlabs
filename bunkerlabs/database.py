from dockerlabs.extensions import db as alchemy_db
from .models import BunkerUser, BunkerMachine, BunkerAccessToken, BunkerSolve

def init_bunker_db():
           
    alchemy_db.create_all(bind_key='bunker')
