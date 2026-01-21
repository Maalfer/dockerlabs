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
