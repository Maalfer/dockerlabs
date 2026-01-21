from .extensions import db as alchemy_db
from .models import User, Machine, Category, Mensajeria

def init_db():
           
    alchemy_db.create_all()
