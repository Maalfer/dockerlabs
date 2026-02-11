from dockerlabs.extensions import db
from dockerlabs.models import Machine
from flask import Flask
from dockerlabs import create_app

app = create_app()

with app.app_context():
    machines = Machine.query.limit(10).all()
    for m in machines:
        print(f"Machine: {m.nombre}, Imagen: {m.imagen}")
