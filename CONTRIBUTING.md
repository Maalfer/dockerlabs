# 👷Como contribuir en DockerLabs
*Desde el equipo de desarrollo de DockerLabs agradecemos tus ganas de colaborar🐋🩵*
# Índice
- [Antes de empezar](#antes-de-empezar)
- [Mejores prácticas y recomendaciones](#mejores-prácticas-y-recomendaciones)
- [Desplegar DockerLabs en local](#desplegar-dockerlabs-en-local)
    - [Dependencias](#dependencias)
    - [Configurar y desplegar DockerLabs](#configurar-y-desplegar-dockerlabs)
- [Reportar vulnerabilidades (VDP)](#reportar-vulnerabilidades-vdp)
# Antes de empezar
> [!IMPORTANT]
> DockerLabs está migrando a React. Cualquier cambio indicado para la versión actual se trasladará al nuevo DockerLabs. Si quiere visualizar el proyecto en React puede ir a [DockerLabs React](https://github.com/Maalfer/dockerlabs/tree/migrar-react)
# Mejores prácticas y recomendaciones

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

# ¿Qué ocurre después de abrir una Pull Request?
El equipo de Desarrollo de DockerLabs revisará detalladamente todos los cambios sugeridos y seguirá la siguiente metodología:
1. ¿Es necesario en la plataforma?

# Reportar vulnerabilidades (VDP)
Si encuentra una falla de seguridad en nuestra plataforma, puede reportarla en nuestro programa VDP en la plataforma [Secur0](https://secur0.com/):
https://app.secur0.com/vulnerability-disclosure/Dockerlabs