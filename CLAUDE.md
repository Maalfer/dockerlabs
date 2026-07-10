# DockerLabs – Guía de desarrollo

> ## ⚠️ Despliegue: el VPS es la FUENTE DE VERDAD
> Desde **2026-06-16** se abandonó el push-deploy de GitHub Actions. El código en
> producción se edita **directamente en el VPS** (`/var/www/dockerlabs/`) y se aplica
> con `sudo systemctl restart dockerlabs`. **No** despliegues con `git pull`: GitHub
> `main` está desactualizado. Detalles completos en **`DEPLOYMENT.md`**.

> ## 🔒 API pública estable — NO romper
> `GET /u/<slug>`, `GET /api/certificado/{pdf,imagen,verificar}/<CERT_ID>` y
> `GET /img/{maquina,perfil}/<id>` son una **API pública consumida por otras
> aplicaciones**, sin autenticación. Sus rutas, campos, tipos y formatos son un
> **contrato**: no los renombres, cambies ni elimines. Puedes añadir campos;
> quitar o cambiar los existentes rompe a los consumidores. Contrato completo en
> **`API_PUBLICA.md`** — léelo antes de tocar `routes/public_profile.py` o
> `routes/certificados.py`.

## Stack

- **Backend:** FastAPI + Uvicorn (4 workers), Python 3.11
- **Base de datos:** MariaDB via PyMySQL, ORM SQLAlchemy
- **Templates:** Jinja2 (server-side rendering)
- **Frontend:** Vanilla JS, Bootstrap 5, Fetch API
- **Servidor web:** nginx como reverse proxy (puerto 443 → uvicorn :9090)
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

> Contrato estable en **`API_PUBLICA.md`**: no renombres ni quites campos.

`GET /u/<slug>` devuelve JSON puro y público (sin sesión): perfil, `progreso`
sobre el catálogo de DockerLabs (total, hechas, porcentaje y desglose por
dificultad), las máquinas resueltas y las creadas con su ficha completa y su
`logo_url`, los writeups y los certificados con `pdf_url` e `imagen_url`. Cada
máquina resuelta incluye además su `writeup_url` y su `certificado` si existen.
También acepta el `username` literal como alias del slug.

De las máquinas de BunkerLabs solo se expone que fueron resueltas (nombre,
dificultad y logo); nunca su `descripcion` ni su `descarga`, y no cuentan para
el porcentaje de progreso.

El desglose por dificultad agrupa por `Machine.clase`, no por `Machine.dificultad`:
esta última está sin normalizar en la base ('Fácil' y 'Facil' conviven).

Carga el catálogo y las categorías por lotes; no añadas consultas por máquina.

## Certificados

> **API pública, contrato estable — ver `API_PUBLICA.md`.** No cambies rutas ni
> campos de los endpoints de certificados/perfil: hay apps externas leyéndolos.

**BunkerLabs no tiene certificados.** Solo se emiten diplomas para máquinas de
`CERT_ORIGENES = ('docker', 'empezar')`; el candado está en `machine_certificable()`
(usado por `ensure_certificate`, la disponibilidad, la generación y
`mis-certificados`). No emitas ni expongas certificados de máquinas con
`origen == 'bunker'`.

Un certificado **existe en cuanto el usuario tiene un writeup publicado** de una
máquina de DockerLabs: no hay que pedirlo. `ensure_certificate()` renderiza el diploma y
archiva el PDF en `uploads/certificados/user_<id>/<CERT_ID>-<maquina>.pdf`,
registrándolo en la tabla `certificados`. Se invoca automáticamente al aprobar
un writeup, así que `/u/<slug>` siempre lo encuentra ya hecho.

Junto al PDF se archiva el diploma como WebP (`.webp`, ~85 KB). Ambos se
sirven públicos: `GET /api/certificado/pdf/<CERT_ID>` y
`GET /api/certificado/imagen/<CERT_ID>` (este último, `inline`, para verlo o
incrustarlo). `GET /api/certificado/<maquina>` sigue descargando un PNG
(`?formato=png`, por defecto) o el PDF (`?formato=pdf`).

No guardes el diploma como PNG ni lo sirvas con `optimize=True`: pesa 1 MB y
comprimirlo tarda ~13 s, tiempo de sobra para que el navegador abandone la
descarga. El PNG que se descarga usa `compress_level=1` (0,45 s).

El `cert_id` (`DL-XXXXXX`) son 24 bits de `sha256("<username>:<maquina>")` y es
ÚNICO en la tabla. Como 24 bits colisionan de verdad con miles de certificados,
`allocate_cert_id()` elige el primer candidato libre del digest (ventanas de 6
hex) y mantiene estable el ID de los ya emitidos. No uses `certificate_id()`
para leer el ID definitivo: lee `Certificate.cert_id`. `fix_cert_id_collisions.py`
repara duplicados heredados. La fecha impresa es la del writeup, no la de
renderizado, para que regenerar un diploma no lo cambie.

Como el `cert_id` depende del nombre de usuario y el diploma lleva impreso el
`nombre_diploma`, ambos cambios reemiten los PDFs vía `sync_user_certificates()`.
Al borrar un writeup se retira el diploma con `revoke_certificate_safe()`.

`author_matches_user()` decide de quién es un writeup: coincidencia exacta, y la
insensible a mayúsculas solo cuando no hay dos cuentas homónimas (existen
`oscar` y `Oscar`). Usa **siempre** esa función; el backfill la comparte.

`backfill_certificados.py` emite los que falten y retira los sobrantes. Es
idempotente (`--force` re-renderiza, `--dry-run` solo cuenta).

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
7. Rate limit: 300 req/min por IP en el middleware ASGI (excluye `/static/`, `/img/`, `/database/`). Los diccionarios de rate-limit se purgan al superar 10.000 claves, para que rotar la IP de origen no agote la memoria del worker.
8. El `rol` viaja firmado en la cookie (30 días, sin almacén de sesiones). `get_session` lo revalida contra la BD cuando la cookie afirma `admin`/`moderador`, de modo que degradar o borrar a un privilegiado surte efecto al instante.
9. Las respuestas `/img/` llevan una CSP `sandbox` en vigor: un SVG subido como logo no ejecuta scripts al abrirlo como documento.

## Comandos útiles

```bash
sudo systemctl restart dockerlabs   # Reiniciar el servicio
sudo journalctl -u dockerlabs -f    # Ver logs en tiempo real
mysqldump -u dockerlabs -p'...' dockerlabs > backup.sql   # Backup BD
```
