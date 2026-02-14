from asgiref.wsgi import WsgiToAsgi
from dockerlabs.app import app as flask_app

application = WsgiToAsgi(flask_app)
app = application
