<div align="center">
  <img src="static/dockerlabs/images/repo/portada.png" alt="DockerLabs Banner" width="100%">

  # DockerLabs
  
  **La Plataforma Definitiva para Entrenar tus Habilidades de Hacking Ético**

  [![Version](https://img.shields.io/github/v/tag/Maalfer/dockerlabs?style=for-the-badge&label=version&color=blue)](CHANGELOG.md)
  [![GitHub Stars](https://img.shields.io/github/stars/Maalfer/dockerlabs?style=for-the-badge&color=yellow)](https://github.com/Maalfer/dockerlabs/stargazers)
  [![GitHub Forks](https://img.shields.io/github/forks/Maalfer/dockerlabs?style=for-the-badge&color=orange)](https://github.com/Maalfer/dockerlabs/network/members)
  [![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
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
  <img src="static/dockerlabs/images/repo/presentacionmaquina.webp" alt="Presentación Máquina" width="80%" style="border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <p><em>Interfaz moderna para la gestión de máquinas y writeups</em></p>
</div>

---

## 🛠️ Tecnologías

Un stack robusto y moderno para garantizar rendimiento y escalabilidad.

<div align="center">
  <img src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI">
  <img src="https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white" alt="Docker">
  <img src="https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5">
  <img src="https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white" alt="CSS3">
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" alt="Javascript">
</div>

---

## 🔖 Versionado

DockerLabs sigue [Versionado Semántico](https://semver.org/lang/es/)
(`MAJOR.MINOR.PATCH`) a partir de la `v2.0.0`. Cada release queda
etiquetada en git y documentada en [`CHANGELOG.md`](CHANGELOG.md).

La versión desplegada se puede consultar en tres sitios, siempre
consistentes entre sí porque leen del mismo fichero [`VERSION`](VERSION):

- El pie de página de https://dockerlabs.es
- La etiqueta `<meta name="application-version">` del `<head>`
- El endpoint público `GET /api/version` → `{"version": "2.0.1"}`

Este versionado permite, además, referenciar rangos de versiones
afectadas/corregidas en los avisos de seguridad (ver
[`SECURITY.md`](SECURITY.md)) y solicitar identificadores **CVE** para
vulnerabilidades confirmadas.

---

## 💻 Instalación manual (sin Docker)

Si prefieres no depender de Docker, necesitas Python 3.13 y una base de
datos MariaDB/MySQL accesible.

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/Maalfer/dockerlabs.git
    cd dockerlabs
    ```

2.  **Entorno virtual y dependencias:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Configura el entorno:** copia `.env.example` a `.env` y rellena al
    menos `DATABASE_URL` (tu MariaDB) y `SECRET_KEY`.

4.  **Arranca la app:**
    ```bash
    python3 run.py        # desarrollo: puerto 5000, con autorecarga
    # o, en modo más parecido a producción:
    venv/bin/uvicorn asgi:app --host 0.0.0.0 --port 8000
    ```
    El esquema de la base de datos se crea solo en el primer arranque.

> [!TIP]
> Si quieres la vía más rápida y reproducible (sin instalar Python ni
> MariaDB a mano), usa **Docker Compose** — sección más abajo.

<div align="center">
  <img src="static/dockerlabs/images/repo/lanzar_maquina.png" alt="Lanzar Máquina" width="70%" style="border-radius: 8px;">
</div>

---

## ⚙️ Producción y tareas de administración

En producción, DockerLabs corre detrás de un reverse proxy (nginx o
Apache) con TLS, con la app servida vía `uvicorn` gestionado por systemd
y MariaDB como base de datos — el mismo proceso que arranca el paso 4 de
arriba, solo que supervisado por el sistema en vez de a mano.

### Rate Limiting (Cloudflare)

El sistema de limitación de peticiones (Rate Limit) está configurado para funcionar con **Cloudflare**, proporcionando protección a nivel de red sin necesidad de servicios adicionales como memcached.

### Convertir un usuario en admin

Regístrate normalmente desde la web y, con acceso a la base de datos:

```bash
mysql -u <usuario> -p dockerlabs \
  -e "UPDATE users SET role='admin' WHERE username='TU_USUARIO';"
```

(con Docker Compose, el comando equivalente está en esa sección, más abajo).

---

## 🐳 Despliegue con Docker Compose (recomendado)

La forma más rápida de levantar DockerLabs, en local o en tu propio
servidor: un solo comando levanta la app y su base de datos MariaDB.

1.  **Clona el repositorio y copia la configuración:**
    ```bash
    git clone https://github.com/Maalfer/dockerlabs.git
    cd dockerlabs
    cp .env.example .env
    ```

2.  **Edita `.env`**: como mínimo cambia `DB_PASSWORD`, `DB_ROOT_PASSWORD`
    y `SECRET_KEY` (genera esta última con
    `python3 -c "import secrets; print(secrets.token_hex(32))"`). El resto
    (SMTP, Discord) es opcional — sin SMTP configurado el registro de
    usuarios funciona igual, solo sin verificación por email.

3.  **Levanta los contenedores:**
    ```bash
    docker compose up -d --build
    ```
    La primera vez crea el esquema de la base de datos automáticamente.
    La app queda disponible en `http://localhost:8000` (o el puerto que
    hayas puesto en `APP_PORT`).

4.  **Conviértete en admin** (regístrate primero desde la web con tu
    usuario, luego):
    ```bash
    docker compose exec db mariadb -u dockerlabs -p dockerlabs \
      -e "UPDATE users SET role='admin' WHERE username='TU_USUARIO';"
    ```
    (pide la contraseña de `DB_PASSWORD` del `.env`).

Los datos (imágenes subidas y base de datos) persisten en volúmenes
Docker (`uploads_data`, `db_data`) entre reinicios. Para pararlo:
`docker compose down` (añade `-v` solo si además quieres borrar los datos).

## 👷Como contribuir en DockerLabs
En [CONTRIBUTING.md](/CONTRIBUTING.md) indicamos todos los detalles para poder contribuir en [DockerLabs](https://dockerlabs.es).

---

<div align="center">
  <h2>🌟 Historia de Estrellas</h2>
  <img src="https://api.star-history.com/svg?repos=Maalfer/dockerlabs&type=Date" alt="Star History Chart" width="100%">
</div>
