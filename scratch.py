from flask import Flask, session
from flask_login import LoginManager, UserMixin, login_user
import hashlib

app = Flask(__name__)
app.secret_key = "test_secret"
login_manager = LoginManager(app)

class User(UserMixin):
    def __init__(self, id):
        self.id = id

@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

with app.test_request_context():
    user = User("123")
    login_user(user)
    print("Flask-Login Session:", dict(session))
