# DockerLabs – Guía de desarrollo

> ## ⚠️ Despliegue: el VPS es la FUENTE DE VERDAD
> Desde **2026-06-16** se abandonó el push-deploy de GitHub Actions. El código en
> producción se edita **directamente en el VPS** (`/var/www/dockerlabs/`) y se aplica
> con `sudo systemctl restart dockerlabs`. **No** despliegues con `git pull`: GitHub
> `main` está desactualizado. Detalles completos en **`DEPLOYMENT.md`**.

## Stack

- **Backend:** FastAPI + Uvicorn (4 workers), Python 3.11
- **Base de datos:** MariaDB via PyMySQL, ORM SQLAlchemy
- **Templates:** Jinja2 (server-side rendering)
- **Frontend:** Vanilla JS, Bootstrap 5, Fetch API
- **Servidor web:** Apache como reverse proxy (puerto 443 → uvicorn :9090)
- **Servicio:** `systemctl restart dockerlabs`

## Estructura del proyecto

```
asgi.py                  # Punto de entrada ASGI, middlewares
dockerlabs/
  routers.py             # Router principal: modelos Pydantic, auth, perfil, admin
  database.py            # Engine SQLAlchemy, scoped_session por request
  extensions.py          # DBFacade: wrapper de SQLAlchemy compatible con modelos
  models.py              # Todos los modelos ORM
  auth.py                # Helpers de imagen de perfil
  maquinas.py            # recalcular_ranking_creadores()
  writeups.py            # recalcular_ranking_writeups()
  slugs.py               # Slug público de perfil (/u/<slug>), sincronizado con username
  validators.py          # Validación de inputs (nombres, URLs, imágenes)
  image_utils.py         # Conversión a WebP
  email.py               # Envío de correos (Postfix local)
  routes/
    machines.py          # CRUD máquinas, claims, machine-edit-requests
    pages_core.py        # Páginas públicas principales
    pages_admin.py       # Panel de administración
    writeups.py          # Gestión de writeups y ranking
    notifications.py     # Sistema de notificaciones
    bunkerlabs_pages.py  # Páginas de BunkerLabs
    bunker_api.py        # API endpoints de BunkerLabs
    images.py            # Servicio de imágenes (perfil, logos)
    certificados.py      # Certificados de usuario (render PNG + archivado del PDF)
    public_profile.py    # API pública JSON del perfil: GET /u/<slug>
    pending_admin.py     # Revisión de envíos pendientes
bunkerlabs/              # Módulos propios de BunkerLabs
static/                  # Assets estáticos (JS, CSS, imágenes)
templates/               # Plantillas Jinja2
uploads/ # Ficheros en disco (perfiles, logos y certificados PDF)
```

## Sesiones y autenticación

Las sesiones usan `itsdangerous.URLSafeTimedSerializer` con la clave almacenada en la tabla `session_config`. La cookie se llama `session`.

```python
# Inyectar sesión en un endpoint:
def mi_endpoint(request: Request, session: dict = Depends(get_session)):
    user_id = session.get('user_id')
    role    = session.get('role', '')
```

La clave `get_session` está definida en `routers.py` y se pasa a todos los módulos de rutas. No hay Flask en ninguna parte.

## CSRF

Token HMAC stateless derivado del `_id` de sesión. Se verifica via:

```python
csrf_ok: bool = Depends(verify_csrf_token)
```

El token va en el header `X-CSRFToken` (o campo de formulario `csrf_token`).

## Base de datos

```python
# Usar la sesión en cualquier endpoint o función:
from dockerlabs.extensions import db

db.session.add(objeto)
db.session.commit()
db.session.rollback()

# Queries:
User.query.filter_by(username='foo').first()
db.session.query(Machine).filter(...).all()
```

La sesión se limpia automáticamente al final de cada request por `DBSessionMiddleware` en `asgi.py`.

## Registro de nuevas rutas

Los módulos de `routes/` exportan una función `register_*_routes(api_router, pages_router, ...)`. Se registran al final de `routers.py`:

```python
from dockerlabs.routes.mi_modulo import register_mi_modulo_routes
register_mi_modulo_routes(
    api_router=api_router,
    pages_router=pages_router,
    get_session=get_session,
    verify_csrf_token=verify_csrf_token,
    db=db,
    templates=templates,
)
```

## Templates Jinja2

Variables globales disponibles en todos los templates:

| Variable | Descripción |
|----------|-------------|
| `url_for(endpoint, **kwargs)` | Genera URLs por nombre de endpoint |
| `static_v(filename)` | URL estática con cache-busting por mtime |
| `get_profile_image_url(user_id=)` | URL de imagen de perfil |
| `current_year` | Año actual |

Contexto mínimo que debe pasar cada página HTML:

```python
templates.TemplateResponse("plantilla.html", {
    "request": request,
    "session": session,
    "current_user_role": session.get("role", ""),
    "csrf_token_value": session.get("csrf_token", ""),
    "g": {"csp_nonce": request.state.csp_nonce},
})
```

## Perfil público (`/u/<slug>`)

Cada usuario tiene un `slug` único derivado de su `username` (`El Pingüino de
Mario` → `el-pinguino-de-mario`). Lo asignan los eventos `before_insert` /
`before_update` de `slugs.py`, así que cualquier alta o renombrado de un `User`
lo mantiene al día sin intervención del código llamante.

`GET /u/<slug>` devuelve JSON puro y público (sin sesión) con el perfil, las
máquinas resueltas, las máquinas creadas, los writeups publicados y los
certificados. También acepta el `username` literal como alias del slug.

## Certificados

`GET /api/certificado/<maquina>` renderiza el diploma y, **en cada generación**,
archiva una copia en PDF en `uploads/certificados/user_<id>/<CERT_ID>-<maquina>.pdf`
y la registra en la tabla `certificados`. Acepta `?formato=png` (por defecto) o
`?formato=pdf`.

El PDF archivado se sirve luego de forma pública en
`GET /api/certificado/pdf/<CERT_ID>`, que es el enlace que expone `/u/<slug>` en
cada certificado con `generado: true`.

El `cert_id` (`DL-XXXXXX`) es determinista: `sha256("<username>:<maquina>")[:6]`.

## Almacenamiento de imágenes

- **Perfiles:** `uploads/perfiles/user_{id}_{ts}.webp`
- **Logos:** `uploads/logos/{docker|bunker}_{machine_id}_{ts}.webp`
- Servidas por los endpoints `/img/perfil/<id>` y `/img/maquina/<id>`

## DockerLabs vs BunkerLabs

| | DockerLabs | BunkerLabs |
|--|--|--|
| `origen` | `"docker"` | `"bunker"` |
| URL base | `/` | `/bunkerlabs` |
| Acceso | Público | PIN o invitación |
| Dificultades | Muy Fácil · Fácil · Medio · Difícil | + Real |

## Seguridad

1. CSRF obligatorio en todos los endpoints de escritura
2. `validators.py` para validar inputs en endpoints públicos
3. `secure_filename()` en uploads de ficheros
4. Imágenes verificadas con PIL antes de guardar
5. Límites: 5 MB perfiles, 2 MB logos
6. Scripts inline en templates requieren `nonce="{{ g.csp_nonce }}"`
7. Rate limit: 300 req/min por IP en el middleware ASGI (excluye `/static/`)

## Comandos útiles

```bash
sudo systemctl restart dockerlabs   # Reiniciar el servicio
sudo journalctl -u dockerlabs -f    # Ver logs en tiempo real
mysqldump -u dockerlabs -p'...' dockerlabs > backup.sql   # Backup BD
```
