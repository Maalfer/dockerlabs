# 👷Como contribuir en DockerLabs
*Desde el equipo de desarrollo de DockerLabs agradecemos tus ganas de colaborar🐋🩵*
# Índice
- [Antes de empezar](#antes-de-empezar)
- [Mejores prácticas y recomendaciones](#mejores-prácticas-y-recomendaciones)
- [Desplegar DockerLabs en local](#desplegar-dockerlabs-en-local)
    - [Dependencias](#dependencias)
    - [Configurar y desplegar DockerLabs](#configurar-y-desplegar-dockerlabs)
        - [Desplegar DockerLabs](#desplegar-dockerlabs)
- [¿Qué ocurre después de abrir una Pull Request?](#qué-ocurre-después-de-abrir-una-pull-request)
- [Versionado y cómo publicar un release](#versionado-y-cómo-publicar-un-release)
- [Reportar vulnerabilidades (VDP)](#reportar-vulnerabilidades-vdp)

# Antes de empezar

Si encuentras un fallo, repórtalo en [Issues](https://github.com/Maalfer/dockerlabs/issues).

# Mejores prácticas y recomendaciones
Para realizar cambios seguros y que no ocasionen problemas con la plataforma, recomendamos:

- **Probar nuevas integraciones en la plataforma**  
  Verifica que la funcionalidad opere correctamente y que no genere conflictos con otras partes del sistema.  
  *(Si tienes dudas, puedes realizar la Pull Request igualmente y el equipo de desarrollo debatirá los cambios.)*

- **Documentar detalladamente los cambios en las Pull Request**  
  Explicar claramente las modificaciones realizadas nos ayudará a comprender mejor la funcionalidad propuesta.  
  Una buena documentación también puede agilizar la revisión, evitando la necesidad de analizar el código en profundidad.


# Desplegar DockerLabs en local

## Dependencias
DockerLabs es FastAPI + Uvicorn sobre MariaDB. El repositorio deja un
[requirements.txt](/requirements.txt) con todas las dependencias exactas que
hacen funcionar la plataforma — no las dupliques aquí, instala directamente
desde ese fichero para no tener dos listas que puedan divergir.

El rate limiting no depende de memcached ni de ningún servicio externo: es un
middleware ASGI en memoria (ver `agent.md`), pensado para funcionar detrás de
Cloudflare.

> [!WARNING]
> Se recomienda hacerlo en un entorno virtual de Python. Para desplegar uno:
> ```bash
>python3 -m venv venv
>```
```bash
pip3 install -r requirements.txt
```

## Configurar y desplegar DockerLabs
Ya tengamos las dependencias instaladas vamos a configurar correctamente la aplicación para poder desplegarla.

También necesitas una base de datos MariaDB/MySQL accesible y un fichero
`.env` con al menos `DATABASE_URL` y `SECRET_KEY` (usa `.env.example` como
plantilla). Si prefieres no instalar nada de esto a mano, usa directamente
**Docker Compose** (ver `README.md`).

### Desplegar DockerLabs
Una vez todo preparado podemos lanzar DockerLabs, para ello ejecutaremos el script [run.py](/run.py):

```bash
(venv) root@b3e19df7fedc:~/dockerlabs# python3 run.py 
INFO:     Will watch for changes in these directories: ['/root/dockerlabs']
INFO:     Uvicorn running on http://0.0.0.0:5000 (Press CTRL+C to quit)
INFO:     Started reloader process [29]
INFO:     Waiting for application startup.
INFO:     Started server process [31]
INFO:     Waiting for application startup.
INFO:     ASGI 'lifespan' protocol appears unsupported.
INFO:     Application startup complete.
```

# ¿Qué ocurre después de abrir una Pull Request?

El equipo de desarrollo de DockerLabs revisará detalladamente todos los cambios propuestos. Aquellos cambios que se consideren innecesarios o que puedan generar problemas serán rechazados.

Valoramos y agradecemos todas las contribuciones. Sin embargo, te pedimos que revises cuidadosamente tus cambios para evitar introducir vulnerabilidades de seguridad o conflictos en el código.

# Versionado y cómo publicar un release

DockerLabs sigue [Versionado Semántico](https://semver.org/lang/es/)
(`MAJOR.MINOR.PATCH`) desde la `v2.0.0`. La fuente única de verdad es el
fichero [`VERSION`](VERSION) en la raíz: todo lo demás (footer, meta tag,
`GET /api/version`, badge del README) lo lee de ahí, así que nunca hay que
tocar nada más que ese fichero y el `CHANGELOG.md`.

Para publicar una nueva versión:

1. Decide el número según el impacto del cambio:
   - **PATCH** (`2.0.1`): corrección de bug o de seguridad, sin romper nada.
   - **MINOR** (`2.1.0`): funcionalidad nueva, compatible con lo anterior.
   - **MAJOR** (`3.0.0`): rompe la API pública (`API_PUBLICA.md`) o cambia
     el comportamiento de autenticación/sesión de forma incompatible.
2. Actualiza el fichero `VERSION` con el número nuevo (sin prefijo `v`).
3. Añade una entrada en `CHANGELOG.md` bajo `## [X.Y.Z] - AAAA-MM-DD`,
   describiendo los cambios (`Added`/`Changed`/`Fixed`/`Security`). Si la
   entrada corrige una vulnerabilidad con advisory público, referencia su
   GHSA/CVE.
4. Haz commit de ambos ficheros y etiqueta el commit:
   ```bash
   git tag -a vX.Y.Z -m vX.Y.Z
   git push origin main --tags
   ```
5. (Opcional) Crea el [Release en GitHub](https://github.com/Maalfer/dockerlabs/releases/new)
   a partir del tag, pegando la entrada correspondiente del `CHANGELOG.md`.
6. Despliega el código nuevo en el VPS y reinicia `dockerlabs.service`; la
   web, el footer y `/api/version` reflejan la nueva versión de inmediato.

# Reportar vulnerabilidades (VDP)

Si encuentras una vulnerabilidad de seguridad en nuestra plataforma, puedes reportarla a través de nuestro programa VDP en Secur0:

- https://app.secur0.com/vulnerability-disclosure/Dockerlabs
