<div align="center">
  <img src="static/images/repo/portada.png" alt="DockerLabs Banner" width="100%">

  # DockerLabs
  
  **La Plataforma Definitiva para Entrenar tus Habilidades de Hacking Ético**

  [![GitHub Stars](https://img.shields.io/github/stars/Maalfer/dockerlabs?style=for-the-badge&color=yellow)](https://github.com/Maalfer/dockerlabs/stargazers)
  [![GitHub Forks](https://img.shields.io/github/forks/Maalfer/dockerlabs?style=for-the-badge&color=orange)](https://github.com/Maalfer/dockerlabs/network/members)
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
  [![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)

  <br>

  <p align="center">
    <strong>DockerLabs</strong> facilita el despliegue de laboratorios vulnerables en segundos usando el poder de los contenedores Docker. <br>
    Ligero, rápido y diseñado para la comunidad.
  </p>
</div>

---

## 🚀 ¿Qué es DockerLabs?

DockerLabs es una plataforma web open-source que permite a los usuarios **desplegar, practicar y aprender** ciberseguridad sin las complicaciones de configurar máquinas virtuales pesadas. Con un solo clic, puedes lanzar entornos vulnerables aislados, listos para ser explotados.

Olvídate de descargas de 4GB. DockerLabs levanta máquinas en milisegundos.

---

## ✨ Características Principales

| 🐳 **Eficiencia Docker** | 🎯 **Máquinas Variadas** | 🤝 **Comunidad** |
| :--- | :--- | :--- |
| Entornos ultraligeros que consumen recursos mínimos. Levanta 10 laboratorios donde antes solo cabía una VM. | Desde máquinas *Very Easy* hasta retos *Hard*. Filtra por dificultad, fecha, creador y mucho más. | Sube tus propios **Writeups**, valora las máquinas y compite en el ranking global. |

<div align="center">
  <img src="static/images/repo/presentacionmaquina.webp" alt="Presentación Máquina" width="80%" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <p><em>Interfaz moderna para la gestión de máquinas y writeups</em></p>
</div>

---

## 🛠️ Tecnologías

Un stack robusto y moderno para garantizar rendimiento y escalabilidad.

<div align="center">
  <img src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue" alt="Python">
  <img src="https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  <img src="https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5">
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="Javascript">
</div>

---

## 💻 Instalación y Despliegue Local

¡Empieza en minutos!

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/Maalfer/dockerlabs.git
    cd dockerlabs
    ```

2.  **Configura el entorno:**
    Crea un entorno virtual e instala las dependencias.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configura las variables de entorno:**
    ```bash
    cp .env.example .env
    # Edita .env con tu SECRET_KEY
    ```

4.  **Ejecuta la aplicación:**
    ```bash
    python3 app.py
    ```

<div align="center">
  <img src="static/images/repo/lanzar_maquina.png" alt="Lanzar Máquina" width="70%" style="border-radius: 8px;">
</div>

---

> [!NOTE]
> **Información crítica de despliegue a continuación.**

## ⚙️ DESPLIEGUE NORMAL (Producción)

Para desplegar dockerlabs en producción con Apache, estos son los permisos necesarios:

```bash
sudo chown -R www-data:www-data /var/www/dockerlabs
sudo find /var/www/dockerlabs -type d -exec chmod 755 {} \;
sudo find /var/www/dockerlabs -type f -exec chmod 644 {} \;
sudo chmod 775 /var/www/dockerlabs
sudo chmod 664 /var/www/dockerlabs/bunkerlabs.db
sudo chmod 664 /var/www/dockerlabs/dockerlabs.db
sudo chmod +x /var/www/dockerlabs/venv/bin/uvicorn
sudo systemctl restart dockerlabs.service
```

### Rate Limiting (Memcached)

Para el funcionamiento correcto del sistema de limitación de peticiones (Rate Limit), es necesario tener **memcached** activado:

```bash
sudo apt install memcached
sudo systemctl enable memcached
sudo systemctl start memcached
```

### Auditoría Local (Admin)

Si queremos auditar dockerlabs en local con un usuario que tenga rol de admin, debemos añadir en el `app.py` el siguiente endpoint y después visitar dicha ruta:

```python
@app.route('/make-me-admin')
def make_me_admin():
    user_id = session.get('user_id')
    if not user_id:
        return "Debes iniciar sesión para convertirte en admin.", 401
    db = get_db()
    db.execute(
        "UPDATE users SET role = 'admin' WHERE id = ?",
        (user_id,)
    )
    db.commit()

    return "Ahora eres admin."
```

### 🧪 Poblar Datos de Prueba

Para facilitar el desarrollo y pruebas locales, hemos incluido un script que **crea automáticamente máquinas, usuarios, writeups y valoraciones de prueba**. Este script es especialmente útil cuando quieres probar funcionalidades sin tener que crear manualmente los datos.

**¿Qué crea el script?**

- **5 máquinas** con diferentes niveles de dificultad:
  - TestVeryEasy (Muy Fácil)
  - TestEasy (Fácil)
  - TestMedium (Medio)
  - TestHard (Difícil)
  - TestInsane (Difícil)

- **3 usuarios** con roles distintos:
  - `admin_test` / `Admin123!` (Rol: admin)
  - `creator_test` / `Creator123!` (Rol: creador)
  - `player_test` / `Player123!` (Rol: jugador)

- **11 writeups** de ejemplo (tanto texto como video) distribuidos entre las máquinas

- **10 valoraciones** realistas con diferentes puntuaciones por criterio (dificultad, aprendizaje, recomendación, diversión)

**Uso:**

```bash
# Asegúrate de tener el entorno virtual activado
source venv/bin/activate

# Ejecuta el script
python3 populate_test_data.py
```

El script detectará automáticamente si los datos ya existen y evitará duplicados.

> [!TIP]
> Este script es ideal para entornos de desarrollo. **No lo ejecutes en producción** a menos que sepas exactamente lo que estás haciendo.

<details>
<summary><strong>📄 Ver código completo del script</strong></summary>

```python
#!/usr/bin/env python3
"""
Script para poblar DockerLabs con datos de prueba.
Crea máquinas de diferentes dificultades y usuarios con distintos roles.

Uso:
    python3 populate_test_data.py
"""

import os
import sys

# Añadir el directorio raíz al path para importar los módulos de dockerlabs
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dockerlabs.extensions import db
from dockerlabs.models import User, Machine, Category
from werkzeug.security import generate_password_hash
from datetime import datetime, UTC

def create_test_users():
    """Crea 3 usuarios de prueba con diferentes roles."""
    print("🔐 Creando usuarios de prueba...")
    
    users_data = [
        {
            'username': 'admin_test',
            'email': 'admin@dockerlabs.test',
            'password': 'Admin123!',
            'role': 'admin'
        },
        {
            'username': 'creator_test',
            'email': 'creator@dockerlabs.test',
            'password': 'Creator123!',
            'role': 'creador'
        },
        {
            'username': 'player_test',
            'email': 'player@dockerlabs.test',
            'password': 'Player123!',
            'role': 'jugador'
        }
    ]
    
    created_users = []
    for user_data in users_data:
        # Verificar si el usuario ya existe
        existing_user = User.query.filter_by(username=user_data['username']).first()
        if existing_user:
            print(f"  ⚠️  Usuario '{user_data['username']}' ya existe, saltando...")
            continue
        
        user = User(
            username=user_data['username'],
            email=user_data['email'],
            password_hash=generate_password_hash(user_data['password']),
            role=user_data['role'],
            created_at=datetime.now(UTC)
        )
        db.session.add(user)
        created_users.append(user_data)
        print(f"  ✅ Usuario creado: {user_data['username']} ({user_data['role']})")
    
    db.session.commit()
    
    if created_users:
        print("\n📋 Credenciales de los usuarios creados:")
        for user_data in created_users:
            print(f"  🔑 {user_data['username']}: {user_data['password']} (Rol: {user_data['role']})")
    
    return len(created_users)

def create_test_machines():
    """Crea máquinas de prueba con diferentes dificultades."""
    print("\n🖥️  Creando máquinas de prueba...")
    
    machines_data = [
        {
            'nombre': 'TestVeryEasy',
            'dificultad': 'Muy Fácil',
            'clase': 'muy-facil',
            'color': '#43959b',
            'autor': 'admin_test',
            'enlace_autor': 'https://github.com/admin_test',
            'fecha': '15/01/2026',
            'imagen': 'logos/logo.png',
            'descripcion': 'Máquina de prueba de nivel muy fácil ideal para principiantes. Incluye vulnerabilidades básicas de enumeración y explotación.',
            'link_descarga': 'https://github.com/Maalfer/dockerlabs',
            'posicion': 'izquierda',
            'categoria': 'Enumeración'
        },
        {
            'nombre': 'TestEasy',
            'dificultad': 'Fácil',
            'clase': 'facil',
            'color': '#8bc34a',
            'autor': 'creator_test',
            'enlace_autor': 'https://github.com/creator_test',
            'fecha': '20/01/2026',
            'imagen': 'logos/logo.png',
            'descripcion': 'Máquina de prueba de nivel fácil. Requiere conocimientos básicos de reconocimiento web y escalada de privilegios.',
            'link_descarga': 'https://github.com/Maalfer/dockerlabs',
            'posicion': 'derecha',
            'categoria': 'Web'
        },
        {
            'nombre': 'TestMedium',
            'dificultad': 'Medio',
            'clase': 'medio',
            'color': '#e0a553',
            'autor': 'admin_test',
            'enlace_autor': 'https://github.com/admin_test',
            'fecha': '25/01/2026',
            'imagen': 'logos/logo.png',
            'descripcion': 'Máquina de prueba de dificultad media. Combina técnicas de reconocimiento, explotación web y escalada de privilegios.',
            'link_descarga': 'https://github.com/Maalfer/dockerlabs',
            'posicion': 'izquierda',
            'categoria': 'SQLi'
        },
        {
            'nombre': 'TestHard',
            'dificultad': 'Difícil',
            'clase': 'dificil',
            'color': '#d83c31',
            'autor': 'creator_test',
            'enlace_autor': 'https://github.com/creator_test',
            'fecha': '30/01/2026',
            'imagen': 'logos/logo.png',
            'descripcion': 'Máquina de prueba avanzada. Requiere conocimientos profundos de seguridad y técnicas avanzadas de explotación.',
            'link_descarga': 'https://github.com/Maalfer/dockerlabs',
            'posicion': 'derecha',
            'categoria': 'Pivoting'
        },
        {
            'nombre': 'TestInsane',
            'dificultad': 'Difícil',
            'clase': 'dificil',
            'color': '#d83c31',
            'autor': 'admin_test',
            'enlace_autor': 'https://github.com/admin_test',
            'fecha': '01/02/2026',
            'imagen': 'logos/logo.png',
            'descripcion': 'Máquina de prueba extremadamente difícil. Solo para expertos en pentesting y hacking ético.',
            'link_descarga': 'https://github.com/Maalfer/dockerlabs',
            'posicion': 'izquierda',
            'categoria': 'Kernel'
        }
    ]
    
    created_machines = 0
    for machine_data in machines_data:
        # Verificar si la máquina ya existe
        existing_machine = Machine.query.filter_by(nombre=machine_data['nombre']).first()
        if existing_machine:
            print(f"  ⚠️  Máquina '{machine_data['nombre']}' ya existe, saltando...")
            continue
        
        # Extraer categoría antes de crear la máquina
        categoria = machine_data.pop('categoria')
        
        # Crear la máquina
        machine = Machine(**machine_data)
        db.session.add(machine)
        db.session.flush()  # Para obtener el ID de la máquina
        
        # Crear la categoría asociada
        category = Category(
            machine_id=machine.id,
            origen='dockerlabs',
            categoria=categoria
        )
        db.session.add(category)
        
        created_machines += 1
        print(f"  ✅ Máquina creada: {machine_data['nombre']} ({machine_data['dificultad']})")
    
    db.session.commit()
    return created_machines

def create_test_writeups():
    """Crea writeups de prueba para las máquinas."""
    print("\n📝 Creando writeups de prueba...")
    
    from dockerlabs.models import Writeup
    
    writeups_data = [
        # TestVeryEasy
        {
            'maquina': 'TestVeryEasy',
            'autor': 'admin_test',
            'url': 'https://github.com/admin_test/writeups/TestVeryEasy',
            'tipo': 'texto'
        },
        {
            'maquina': 'TestVeryEasy',
            'autor': 'player_test',
            'url': 'https://www.youtube.com/watch?v=TestVeryEasy',
            'tipo': 'video'
        },
        # TestEasy
        {
            'maquina': 'TestEasy',
            'autor': 'creator_test',
            'url': 'https://github.com/creator_test/writeups/TestEasy',
            'tipo': 'texto'
        },
        {
            'maquina': 'TestEasy',
            'autor': 'admin_test',
            'url': 'https://www.youtube.com/watch?v=TestEasy',
            'tipo': 'video'
        },
        # TestMedium
        {
            'maquina': 'TestMedium',
            'autor': 'admin_test',
            'url': 'https://github.com/admin_test/writeups/TestMedium',
            'tipo': 'texto'
        },
        {
            'maquina': 'TestMedium',
            'autor': 'player_test',
            'url': 'https://medium.com/@player_test/testmedium-writeup',
            'tipo': 'texto'
        },
        # TestHard
        {
            'maquina': 'TestHard',
            'autor': 'creator_test',
            'url': 'https://github.com/creator_test/writeups/TestHard',
            'tipo': 'texto'
        },
        {
            'maquina': 'TestHard',
            'autor': 'admin_test',
            'url': 'https://www.youtube.com/watch?v=TestHard',
            'tipo': 'video'
        },
        # TestInsane
        {
            'maquina': 'TestInsane',
            'autor': 'admin_test',
            'url': 'https://github.com/admin_test/writeups/TestInsane',
            'tipo': 'texto'
        },
        {
            'maquina': 'TestInsane',
            'autor': 'creator_test',
            'url': 'https://www.youtube.com/watch?v=TestInsane',
            'tipo': 'video'
        },
        {
            'maquina': 'TestInsane',
            'autor': 'player_test',
            'url': 'https://blog.player-test.com/testinsane-complete-guide',
            'tipo': 'texto'
        }
    ]
    
    created_writeups = 0
    for writeup_data in writeups_data:
        # Verificar si el writeup ya existe
        existing_writeup = Writeup.query.filter_by(
            maquina=writeup_data['maquina'],
            autor=writeup_data['autor'],
            url=writeup_data['url']
        ).first()
        
        if existing_writeup:
            print(f"  ⚠️  Writeup de '{writeup_data['autor']}' para '{writeup_data['maquina']}' ya existe, saltando...")
            continue
        
        writeup = Writeup(
            maquina=writeup_data['maquina'],
            autor=writeup_data['autor'],
            url=writeup_data['url'],
            tipo=writeup_data['tipo'],
            created_at=datetime.now(UTC)
        )
        db.session.add(writeup)
        created_writeups += 1
        tipo_emoji = "📄" if writeup_data['tipo'] == 'texto' else "🎥"
        print(f"  ✅ Writeup creado: {tipo_emoji} {writeup_data['autor']} → {writeup_data['maquina']}")
    
    db.session.commit()
    return created_writeups

def create_test_ratings():
    """Crea valoraciones de prueba para las máquinas."""
    print("\n⭐ Creando valoraciones de prueba...")
    
    from dockerlabs.models import Rating
    
    # Valoraciones distribuidas entre usuarios y máquinas
    ratings_data = [
        # TestVeryEasy - Puntuaciones altas (fácil)
        {
            'usuario': 'player_test',
            'maquina': 'TestVeryEasy',
            'dificultad_score': 5,
            'aprendizaje_score': 4,
            'recomendaria_score': 5,
            'diversion_score': 4
        },
        {
            'usuario': 'creator_test',
            'maquina': 'TestVeryEasy',
            'dificultad_score': 5,
            'aprendizaje_score': 5,
            'recomendaria_score': 5,
            'diversion_score': 5
        },
        # TestEasy
        {
            'usuario': 'admin_test',
            'maquina': 'TestEasy',
            'dificultad_score': 4,
            'aprendizaje_score': 4,
            'recomendaria_score': 4,
            'diversion_score': 4
        },
        {
            'usuario': 'player_test',
            'maquina': 'TestEasy',
            'dificultad_score': 5,
            'aprendizaje_score': 5,
            'recomendaria_score': 5,
            'diversion_score': 4
        },
        # TestMedium
        {
            'usuario': 'creator_test',
            'maquina': 'TestMedium',
            'dificultad_score': 4,
            'aprendizaje_score': 5,
            'recomendaria_score': 4,
            'diversion_score': 4
        },
        {
            'usuario': 'admin_test',
            'maquina': 'TestMedium',
            'dificultad_score': 3,
            'aprendizaje_score': 4,
            'recomendaria_score': 4,
            'diversion_score': 3
        },
        {
            'usuario': 'player_test',
            'maquina': 'TestMedium',
            'dificultad_score': 4,
            'aprendizaje_score': 5,
            'recomendaria_score': 5,
            'diversion_score': 5
        },
        # TestHard
        {
            'usuario': 'admin_test',
            'maquina': 'TestHard',
            'dificultad_score': 3,
            'aprendizaje_score': 5,
            'recomendaria_score': 4,
            'diversion_score': 5
        },
        {
            'usuario': 'creator_test',
            'maquina': 'TestHard',
            'dificultad_score': 4,
            'aprendizaje_score': 4,
            'recomendaria_score': 3,
            'diversion_score': 4
        },
        # TestInsane
        {
            'usuario': 'admin_test',
            'maquina': 'TestInsane',
            'dificultad_score': 2,
            'aprendizaje_score': 5,
            'recomendaria_score': 5,
            'diversion_score': 5
        }
    ]
    
    created_ratings = 0
    for rating_data in ratings_data:
        # Obtener el user_id del usuario
        from dockerlabs.models import User
        user = User.query.filter_by(username=rating_data['usuario']).first()
        if not user:
            print(f"  ⚠️  Usuario '{rating_data['usuario']}' no encontrado, saltando...")
            continue
        
        # Verificar si la valoración ya existe
        existing_rating = Rating.query.filter_by(
            usuario_id=user.id,
            maquina_nombre=rating_data['maquina']
        ).first()
        
        if existing_rating:
            print(f"  ⚠️  Valoración de '{rating_data['usuario']}' para '{rating_data['maquina']}' ya existe, saltando...")
            continue
        
        rating = Rating(
            usuario_id=user.id,
            maquina_nombre=rating_data['maquina'],
            dificultad_score=rating_data['dificultad_score'],
            aprendizaje_score=rating_data['aprendizaje_score'],
            recomendaria_score=rating_data['recomendaria_score'],
            diversion_score=rating_data['diversion_score'],
            fecha=datetime.now(UTC)
        )
        db.session.add(rating)
        created_ratings += 1
        avg_score = (rating_data['dificultad_score'] + rating_data['aprendizaje_score'] + 
                    rating_data['recomendaria_score'] + rating_data['diversion_score']) / 4
        print(f"  ✅ Valoración creada: {rating_data['usuario']} → {rating_data['maquina']} (⭐ {avg_score:.1f})")
    
    db.session.commit()
    return created_ratings

def main():
    """Función principal del script."""
    print("=" * 60)
    print("🐳 DockerLabs - Poblador de Datos de Prueba")
    print("=" * 60)
    
    # Importar la aplicación para tener el contexto de Flask
    from dockerlabs.app import app
    
    with app.app_context():
        try:
            # Crear usuarios
            users_created = create_test_users()
            
            # Crear máquinas
            machines_created = create_test_machines()
            
            # Crear writeups
            writeups_created = create_test_writeups()
            
            # Crear valoraciones
            ratings_created = create_test_ratings()
            
            print("\n" + "=" * 60)
            print("✨ ¡Proceso completado!")
            print(f"   • Usuarios creados: {users_created}")
            print(f"   • Máquinas creadas: {machines_created}")
            print(f"   • Writeups creados: {writeups_created}")
            print(f"   • Valoraciones creadas: {ratings_created}")
            print("=" * 60)
            
            if users_created > 0:
                print("\n💡 Ahora puedes iniciar sesión con cualquiera de los usuarios de prueba.")
            
        except Exception as e:
            print(f"\n❌ Error al poblar los datos: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

if __name__ == '__main__':
    main()
```

</details>

## 🐳 DESPLIEGUE EN DOCKER

Para construir una imagen de Docker y lanzar la aplicación contenizada, ejecutaremos los siguientes comandos:

```bash
docker build -t dockerlabs .
docker run -d -p 5000:5000 --name dockerlabs dockerlabs
```

---

<div align="center">
  <h2>🌟 Historia de Estrellas</h2>
  <img src="https://api.star-history.com/svg?repos=Maalfer/dockerlabs&type=Date" alt="Star History Chart" width="100%">
</div>
