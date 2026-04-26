import os
from dockerlabs.app import app
from dockerlabs.models import Machine
from dockerlabs.extensions import db

images_map = {
    "Profetas": "profetas.png",
    "RootedPingu": "RootedPingu.png",
    "Internal": "Internal.png",
    "CuentaAtrás": "CuentaAtras.jpg",
    "Flasky": "Flasky.jpg",
    "SECorNOTsec": "SECorNOTsec.jpg",
    "2shell": "2shell.png", # Maybe?
    "Autoescuela": "Autoescuela.jpg" # Maybe?
}

ext_to_mime = {
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
    '.png': 'image/png', '.gif': 'image/gif',
    '.webp': 'image/webp', '.svg': 'image/svg+xml'
}

with app.app_context():
    for name, filename in images_map.items():
        if os.path.exists(filename):
            print(f"Updating {name} with {filename}...")
            machine = Machine.query.filter_by(nombre=name).first()
            if machine:
                with open(filename, 'rb') as f:
                    logo_bytes = f.read()
                
                _, fext = os.path.splitext(filename)
                mime = ext_to_mime.get(fext.lower(), 'image/jpeg')
                
                machine.logo_data = logo_bytes
                machine.logo_mime = mime
                machine.imagen = f"dockerlabs/images/logos/{filename}"
                db.session.commit()
                print(f"  [OK] Successfully updated {name}.")
            else:
                print(f"  [ERROR] Machine {name} not found in DB.")
        else:
            print(f"[MISSING] Image file {filename} not found in root dir.")
