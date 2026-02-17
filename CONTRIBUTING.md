# 👷Como contribuir en DockerLabs
*Desde el equipo de desarrollo de DockerLabs agradecemos tus ganas de colaborar🐋🩵*
# Índice
- [Antes de empezar](#antes-de-empezar)
- [Mejores prácticas y recomendaciones](#mejores-prácticas-y-recomendaciones)
- [Desplegar DockerLabs en local](#desplegar-dockerlabs-en-local)
    - [Dependencias](#dependencias)
    - [Configurar y desplegar DockerLabs](#configurar-y-desplegar-dockerlabs)
        - [Activar servicio de memcached](#activar-servicio-de-memcached)
        - [.env](#env)
        - [Desplegar DockerLabs](#desplegar-dockerlabs)
- [¿Qué ocurre después de abrir una Pull Request?](#qué-ocurre-después-de-abrir-una-pull-request)
- [Reportar vulnerabilidades (VDP)](#reportar-vulnerabilidades-vdp)

# Antes de empezar
> [!IMPORTANT]
> DockerLabs está migrando a React. Cualquier cambio indicado para la versión actual se trasladará al nuevo DockerLabs. Si quiere visualizar el proyecto en React puede ir a [DockerLabs React](https://github.com/Maalfer/dockerlabs/tree/migrar-react)

# Mejores prácticas y recomendaciones
Para realizar cambios seguros y que no ocasionen problemas con la plataforma, recomendamos:

- Probar las nuevas integraciones a la plataforma -> Comprueba que funciona debidamente y que no ocasiona ningún problema con otras funciones de la plataforma. *(Si tienes dudas puede realizar la Pull Request y el equipo de desarrollo debaterá sobre los cambios.)*


# Desplegar DockerLabs en local

## Dependencias
Para desplegar DockerLabs requeriremos de las siguientes dependencias: `memcached,flask,flask_httpauth,flask-limiter,flask-sqlalchemy,flask-login,pymemcache,pillow,python-dotenv,uvicorn,asgiref,flasgger,gunicorn`

Para instalar `memcached` podremos hacerlo mediante `apt`:
```bash
sudo apt install memcached
```

Para instalar las dependencias en Python, el repositorio de DockerLabs deja un [requeriments.txt](/requirements.txt) donde están indicadas todas las dependencias que hacen funcionar la plataforma. Para instalarlas:
> [!WARNING]
> Se recomienda hacerlo en un entorno virtual de Python. Para desplegar uno:
> ```bash
>python3 -m venv venv
>```
```bash
pip3 install -r requeriments.txt
```

## Configurar y desplegar DockerLabs
Ya tengamos las dependencias instaladas vamos a configurar correctamente la aplicación para poder desplegarla.
### Activar servicio de memcached
DockerLabs emplea `memcached` para el sistema de caché y rate limit. Así que requiere estar en marcha. Podemos emplear `service` o `systemctl`:

```bash
service start memcached
```

### .env
En el repositorio verás que ofrecemos un `.env.example`, donde contiene la `SECRET_KEY`. Podremos usar la que se da de ejemplo o crear una clave a nuestro gusto. El archivo debe llamarse `.env`.

### Desplegar DockerLabs
Una vez todo preparado podemos lanzar DockerLabs, para ello ejecutaremos el script [run.py](/run.py):

```bash
(venv) root@b3e19df7fedc:~/dockerlabs# python3 run.py 
INFO:     Will watch for changes in these directories: ['/root/dockerlabs']
INFO:     Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)
INFO:     Started reloader process [29] using StatReload
WARNING: SECRET_KEY not set. Using a temporary generated key.
INFO:     Started server process [31]
INFO:     Waiting for application startup.
INFO:     ASGI 'lifespan' protocol appears unsupported.
INFO:     Application startup complete.
```

Si quiere relleno en la plataforma *(máquinas,usuarios,writeups...)* puede emplear el script [populate_datos.py](/populate_datos.py).

# ¿Qué ocurre después de abrir una Pull Request?
El equipo de Desarrollo de DockerLabs revisará detalladamente todos los cambios sugeridos. Todo cambio innecesario será rechazado.

Aceptamos y agradecemos cambios. Pero hazlo con cabeza, evita dejar fallos de seguridad abiertos o conflictos en el código.

# Reportar vulnerabilidades (VDP)
Si encuentra una falla de seguridad en nuestra plataforma, puede reportarla en nuestro programa VDP en la plataforma [Secur0](https://secur0.com/):

- https://app.secur0.com/vulnerability-disclosure/Dockerlabs