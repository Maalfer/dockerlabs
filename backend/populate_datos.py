import random
import string
from datetime import datetime, timedelta
from dockerlabs.app import app
from dockerlabs.extensions import db
from dockerlabs.models import User, Machine, Category, Writeup
from werkzeug.security import generate_password_hash

# Configuración
NUM_USERS = 50
NUM_DOCKER_MACHINES = 180
NUM_BUNKER_MACHINES = 50
NUM_WRITEUPS = 200

# Datos aleatorios
DIFICULTADES = ["Muy Fácil", "Fácil", "Medio", "Difícil"]
CLASES = ["Linux"]
COLORES = {
    "Muy Fácil": "#43959b",
    "Fácil": "#8bc34a",
    "Medio": "#e0a553",
    "Difícil": "#d83c31"
}
AUTORES = ["ElPingüino", "L0ck3r", "TheArchitect", "CyberPunk", "NetRunner", "RootAdmin", "GhostInShell", "Neo", "Trinity", "Morpheus"]
CATEGORIAS = ["Iniciación", "Active Directory", "Pivoting", "WebApp", "Forensic", "Crypto", "Reversing", "Pwn", "Mobile", "Cloud"]
ROLES = ["jugador", "jugador", "jugador", "moderador", "admin"] # Más probabilidad de jugador

def generate_random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_random_date():
    start_date = datetime(2023, 1, 1)
    end_date = datetime.now()
    random_date = start_date + timedelta(days=random.randint(0, (end_date - start_date).days))
    return random_date.strftime("%d/%m/%Y")

def populate_users():
    print(f"Generando {NUM_USERS} usuarios...")
    
    # Usuarios fijos
    fixed_users = [
        {"username": "admin", "email": "admin@dockerlabs.es", "role": "admin"},
        {"username": "moderador", "email": "moderador@dockerlabs.es", "role": "moderador"},
        {"username": "jugador", "email": "jugador@dockerlabs.es", "role": "jugador"}
    ]

    for user_data in fixed_users:
        if not User.query.filter_by(username=user_data["username"]).first():
            new_user = User(
                username=user_data["username"],
                email=user_data["email"],
                password_hash=generate_password_hash(user_data["username"]), # Password is same as username
                role=user_data["role"],
                recovery_pin_plain="123456",
                recovery_pin_hash=generate_password_hash("123456"),
                recovery_pin_created_at=datetime.utcnow()
            )
            db.session.add(new_user)
    
    # Usuarios aleatorios
    for i in range(NUM_USERS):
        username = f"user_{generate_random_string(5)}"
        email = f"{username}@example.com"
        role = random.choice(ROLES)
        
        if not User.query.filter_by(username=username).first():
            new_user = User(
                username=username,
                email=email,
                password_hash=generate_password_hash("password123"),
                role=role,
                recovery_pin_plain="123456",
                recovery_pin_hash=generate_password_hash("123456"),
                recovery_pin_created_at=datetime.utcnow()
            )
            db.session.add(new_user)
    
    db.session.commit()
    print("Usuarios generados.")

def populate_machines():
    print(f"Generando máquinas...")
    
    # Mapping difficulty to class
    difficulty_to_class = {
        "Muy Fácil": "muy-facil",
        "Fácil": "facil",
        "Medio": "medio",
        "Difícil": "dificil"
    }

    # --- DockerLabs ---
    print(f"  - {NUM_DOCKER_MACHINES} máquinas DockerLabs...")
    for i in range(NUM_DOCKER_MACHINES):
        nombre = f"Docker_{generate_random_string(6)}"
        dificultad = random.choice(DIFICULTADES)
        clase = difficulty_to_class[dificultad]
        color = COLORES[dificultad]
        autor = random.choice(AUTORES)
        fecha = generate_random_date()
        categoria = random.choice(CATEGORIAS)
        
        if not Machine.query.filter_by(nombre=nombre).first():
            new_machine = Machine(
                nombre=nombre,
                dificultad=dificultad,
                clase=clase,
                color=color,
                autor=autor,
                enlace_autor=f"https://github.com/{autor}",
                fecha=fecha,
                imagen="logo.png",
                descripcion=f"Máquina {dificultad} de Linux creada por {autor}. Entorno Docker.",
                link_descarga=f"https://dockerlabs.es/machines/{nombre.lower()}.zip",
                posicion="izquierda" if i % 2 == 0 else "derecha",
                origen="docker",
                guest_access=False
            )
            db.session.add(new_machine)
            db.session.flush()
            
            new_category = Category(
                machine_id=new_machine.id,
                origen="docker",
                categoria=categoria
            )
            db.session.add(new_category)

    # --- BunkerLabs ---
    print(f"  - {NUM_BUNKER_MACHINES} máquinas BunkerLabs...")
    for i in range(NUM_BUNKER_MACHINES):
        nombre = f"Bunker_{generate_random_string(6)}"
        dificultad = random.choice(DIFICULTADES)
        clase = difficulty_to_class[dificultad]
        color = COLORES[dificultad]
        autor = random.choice(AUTORES)
        fecha = generate_random_date()
        categoria = random.choice(CATEGORIAS)
        pin = f"{random.randint(1000, 9999)}"
        
        if not Machine.query.filter_by(nombre=nombre).first():
            new_machine = Machine(
                nombre=nombre,
                dificultad=dificultad,
                clase=clase,
                color=color,
                autor=autor,
                enlace_autor=f"https://linkedin.com/in/{autor}",
                fecha=fecha,
                imagen="logo.png",
                descripcion=f"Máquina {dificultad} de Linux en entorno real (Bunker). PIN: {pin}",
                link_descarga=f"http://192.168.1.{random.randint(10, 250)}",
                posicion="izquierda" if i % 2 == 0 else "derecha",
                origen="bunker",
                pin=pin,
                guest_access=random.choice([True, False])
            )
            db.session.add(new_machine)
            db.session.flush()
            
            new_category = Category(
                machine_id=new_machine.id,
                origen="bunker",
                categoria=categoria
            )
            db.session.add(new_category)

    db.session.commit()
    print("Máquinas generadas.")

def populate_writeups():
    print(f"Generando {NUM_WRITEUPS} writeups...")
    machines = Machine.query.all()
    if not machines:
        print("No hay máquinas para generar writeups.")
        return

    for i in range(NUM_WRITEUPS):
        machine = random.choice(machines)
        autor = f"Writeuper_{generate_random_string(4)}"
        tipo = random.choice(["texto", "video"])
        url = f"https://writeups.com/{autor}/{machine.nombre}" if tipo == "texto" else f"https://youtube.com/watch?v={generate_random_string(11)}"
        
        # Check uniqueness manually or rely on try-except if using flush, but query is safer here
        # Constraint is (maquina, autor, url)
        if not Writeup.query.filter_by(maquina=machine.nombre, autor=autor, url=url).first():
            new_writeup = Writeup(
                maquina=machine.nombre,
                autor=autor,
                url=url,
                tipo=tipo,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 365))
            )
            db.session.add(new_writeup)
    
    db.session.commit()
    print("Writeups generados.")

if __name__ == "__main__":
    with app.app_context():
        print("Iniciando población MASIVA de datos...")
        try:
            populate_users()
            populate_machines()
            populate_writeups()
            print("Población MASIVA finalizada con éxito.")
        except Exception as e:
            db.session.rollback()
            print(f"Error durante la población: {e}")
            import traceback
            traceback.print_exc()
