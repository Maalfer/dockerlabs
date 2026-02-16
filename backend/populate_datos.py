import random
import string
from datetime import datetime, timedelta
from dockerlabs.app import app
from dockerlabs.extensions import db
from sqlalchemy import func
from dockerlabs.models import (
    User, Machine, Category, Writeup, PendingWriteup, WriteupReport, 
    WriteupEditRequest, MachineClaim, CompletedMachine, Rating, Mensajeria,
    WriteupRanking, CreatorRanking
)
from werkzeug.security import generate_password_hash

# Configuración
NUM_USERS = 50
NUM_DOCKER_MACHINES = 180
NUM_BUNKER_MACHINES = 50
NUM_WRITEUPS = 200
NUM_PENDING_WRITEUPS = 20
NUM_REPORTS = 15
NUM_CLAIMS = 10
NUM_COMPLETED = 300
NUM_RATINGS = 400
NUM_MESSAGES = 100

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

def generate_random_datetime():
    start_date = datetime(2023, 1, 1)
    end_date = datetime.now()
    return start_date + timedelta(days=random.randint(0, (end_date - start_date).days), seconds=random.randint(0, 86400))

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
                recovery_pin_created_at=datetime.utcnow(),
                biography=f"Biografía de {user_data['username']}. Amante de la ciberseguridad.",
                linkedin_url=f"https://linkedin.com/in/{user_data['username']}",
                github_url=f"https://github.com/{user_data['username']}",
                youtube_url=f"https://youtube.com/c/{user_data['username']}"
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
        
        if not Writeup.query.filter_by(maquina=machine.nombre, autor=autor, url=url).first():
            new_writeup = Writeup(
                maquina=machine.nombre,
                autor=autor,
                url=url,
                tipo=tipo,
                created_at=generate_random_datetime()
            )
            db.session.add(new_writeup)
    
    db.session.commit()
    print("Writeups generados.")

def populate_pending_writeups():
    print(f"Generando {NUM_PENDING_WRITEUPS} writeups pendientes...")
    machines = Machine.query.all()
    if not machines: return

    for i in range(NUM_PENDING_WRITEUPS):
        machine = random.choice(machines)
        autor = f"Newbie_{generate_random_string(4)}"
        tipo = random.choice(["texto", "video"])
        url = f"https://blog.com/{autor}/{machine.nombre}"
        
        new_pending = PendingWriteup(
            maquina=machine.nombre,
            autor=autor,
            url=url,
            tipo=tipo,
            created_at=generate_random_datetime()
        )
        db.session.add(new_pending)
    
    db.session.commit()
    print("Writeups pendientes generados.")

def populate_writeup_reports():
    print(f"Generando {NUM_REPORTS} reportes de writeups...")
    writeups = Writeup.query.all()
    users = User.query.all()
    if not writeups or not users: return

    for i in range(NUM_REPORTS):
        writeup = random.choice(writeups)
        reporter = random.choice(users)
        reason = random.choice(["Enlace caído", "Contenido inapropiado", "No corresponde a la máquina", "Spam"])
        
        report = WriteupReport(
            writeup_id=writeup.id,
            reporter_id=reporter.id,
            reason=reason,
            created_at=generate_random_datetime()
        )
        db.session.add(report)
    
    db.session.commit()
    print("Reportes generados.")

def populate_machine_claims():
    print(f"Generando {NUM_CLAIMS} reclamaciones de máquina...")
    machines = Machine.query.all()
    users = User.query.all()
    if not machines or not users: return

    for i in range(NUM_CLAIMS):
        machine = random.choice(machines)
        user = random.choice(users)
        
        claim = MachineClaim(
            user_id=user.id,
            username=user.username,
            maquina_nombre=machine.nombre,
            contacto=user.email,
            prueba="https://imgur.com/proof.png",
            estado="pendiente",
            created_at=generate_random_datetime()
        )
        db.session.add(claim)
    
    db.session.commit()
    print("Reclamaciones generadas.")

def populate_completed_machines():
    print(f"Generando {NUM_COMPLETED} máquinas completadas...")
    machines = Machine.query.all()
    users = User.query.all()
    
    for i in range(NUM_COMPLETED):
        machine = random.choice(machines)
        user = random.choice(users)
        
        # Check uniqueness
        if not CompletedMachine.query.filter_by(user_id=user.id, machine_name=machine.nombre).first():
            completed = CompletedMachine(
                user_id=user.id,
                machine_name=machine.nombre,
                completed_at=generate_random_datetime()
            )
            db.session.add(completed)
    
    db.session.commit()
    print("Máquinas completadas generadas.")

def populate_ratings():
    print(f"Generando {NUM_RATINGS} valoraciones...")
    machines = Machine.query.all()
    users = User.query.all()
    
    for i in range(NUM_RATINGS):
        machine = random.choice(machines)
        user = random.choice(users)
        
        if not Rating.query.filter_by(usuario_id=user.id, maquina_nombre=machine.nombre).first():
            rating = Rating(
                usuario_id=user.id,
                maquina_nombre=machine.nombre,
                dificultad_score=random.randint(1, 5),
                aprendizaje_score=random.randint(1, 5),
                recomendaria_score=random.randint(1, 5),
                diversion_score=random.randint(1, 5),
                fecha=generate_random_datetime()
            )
            db.session.add(rating)
    
    db.session.commit()
    print("Valoraciones generadas.")

def populate_messages():
    print(f"Generando {NUM_MESSAGES} mensajes...")
    users = User.query.all()
    if len(users) < 2: return

    for i in range(NUM_MESSAGES):
        sender = random.choice(users)
        receiver = random.choice(users)
        while receiver.id == sender.id:
            receiver = random.choice(users)
        
        msg = Mensajeria(
            sender_id=sender.id,
            receiver_id=receiver.id,
            content=f"Hola {receiver.username}, ¿cómo vas con la máquina?",
            timestamp=generate_random_datetime(),
            read=random.choice([True, False])
        )
        db.session.add(msg)
    
    db.session.commit()
    print("Mensajes generados.")

def populate_rankings():
    print("Calculando y poblando rankings...")
    
    # 1. Ranking Creadores
    try:
        # Contar máquinas por autor en tabla Machine
        results = db.session.query(Machine.autor, func.count(Machine.id)).filter(Machine.origen == 'docker').group_by(Machine.autor).all()
        
        CreatorRanking.query.delete()
        for autor, count in results:
            nombre = (autor or "").strip()
            if not nombre: continue
            entry = CreatorRanking(nombre=nombre, maquinas=count)
            db.session.add(entry)
        db.session.commit()
        print("Ranking de creadores actualizado.")
    except Exception as e:
        print(f"Error actualizando ranking creadores: {e}")
        db.session.rollback()

    # 2. Ranking Writeups
    try:
        puntos_por_dificultad = {
            "muy fácil": 1, "muy facil": 1,
            "fácil": 2, "facil": 2,
            "medio": 3,
            "difícil": 4, "dificil": 4,
        }

        # Unir Writeup con Machine para obtener dificultad
        results = db.session.query(Writeup.autor, Machine.dificultad).join(Machine, Writeup.maquina == Machine.nombre).all()
        
        ranking = {}
        for autor, dificultad in results:
            if not autor: continue
            dificultad_lower = (dificultad or "").strip().lower()
            puntos = puntos_por_dificultad.get(dificultad_lower, 1)
            ranking[autor] = ranking.get(autor, 0) + puntos

        WriteupRanking.query.delete()
        for autor, puntos in ranking.items():
            entry = WriteupRanking(nombre=autor, puntos=puntos)
            db.session.add(entry)
        db.session.commit()
        print("Ranking de writeups actualizado.")
    except Exception as e:
        print(f"Error actualizando ranking writeups: {e}")
        db.session.rollback()

if __name__ == "__main__":
    with app.app_context():
        print("Iniciando población MASIVA y COMPLETA de datos...")
        try:
            # Crear tablas si no existen (útil para primera ejecución)
            db.create_all()
            
            populate_users()
            populate_machines()
            populate_writeups()
            populate_pending_writeups()
            populate_writeup_reports()
            populate_machine_claims()
            populate_completed_machines()
            populate_ratings()
            populate_messages()
            populate_rankings() # CALCULAR RANKINGS AL FINAL
            
            print("Población MASIVA finalizada con éxito.")
        except Exception as e:
            db.session.rollback()
            print(f"Error durante la población: {e}")
            import traceback
            traceback.print_exc()
