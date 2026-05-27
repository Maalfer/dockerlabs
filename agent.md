# Dockerlabs - Agent Rules & Architecture Decisions

## 1. Almacenamiento de Imágenes Multimedia

Las imágenes de perfil y logotipos de máquinas se almacenan en el sistema de archivos bajo `database/almacenamiento/` con la siguiente estructura:

```
database/almacenamiento/
├── perfiles/          # Fotos de perfil de usuarios
└── logos/             # Logotipos de máquinas
```

### Control de Versiones (Git)

**IMPORTANTE:** La carpeta `database/almacenamiento/` y sus subcarpetas deben incluirse en el repositorio Git, **pero sin las imágenes**. Esto garantiza que la estructura de directorios exista al clonar el proyecto.

**Configuración en `.gitignore`:**
```gitignore
# Ignorar solo los archivos de imagen, no las carpetas
database/almacenamiento/**/*.jpg
database/almacenamiento/**/*.jpeg
database/almacenamiento/**/*.png
database/almacenamiento/**/*.gif
database/almacenamiento/**/*.webp
database/almacenamiento/**/*.svg
database/almacenamiento/**/*.bmp
database/almacenamiento/**/*.ico
```

**Archivos `.gitkeep`:** Usar archivos `.gitkeep` vacíos en cada subcarpeta para asegurar que Git trackee la estructura de directorios.

### Convenciones de Nombres (Estandarizadas)

| Tipo | Patrón | Ejemplo |
|------|--------|---------|
| Perfiles | `user_{user_id}_{timestamp}.{ext}` | `user_123_1699123456.jpg` |
| Logos DockerLabs | `docker_{machine_id}_{timestamp}.{ext}` | `docker_456_1699123456.png` |
| Logos BunkerLabs | `bunker_{machine_id}_{timestamp}.{ext}` | `bunker_789_1699123456.webp` |

- El `timestamp` permite múltiples versiones sin sobrescribir archivos anteriores
- Las extensiones permitidas: `.jpg`, `.jpeg`, `.png`, `.gif`, `.webp`, `.svg` (solo logos)
- **Compatibilidad legacy:** Se mantiene soporte para imágenes almacenadas como BLOB en la base de datos (`profile_image_data`, `logo_data`)

### Referencias en Base de Datos

- `User.profile_image_path` → `database/almacenamiento/perfiles/{filename}`
- `Machine.logo_path` → `database/almacenamiento/logos/{filename}`

## 2. Stack Tecnológico

### Backend (Arquitectura Híbrida FastAPI + Flask)

- **FastAPI:** Framework principal para endpoints API (`/api/*`) y páginas HTML
- **Flask:** Mantenido para compatibilidad con endpoints legacy (transición progresiva)
- **SQLAlchemy:** ORM para base de datos SQLite
- **Jinja2:** Motor de templates para renderizado HTML
- **SlowAPI:** Rate limiting compatible con FastAPI y sesiones Flask

### Estructura de Routers

```python
api_router = APIRouter(prefix="/api")      # Endpoints API REST
pages_router = APIRouter()                  # Páginas HTML (sin prefijo)
```

### Frontend

- **Vanilla JS:** Sin frameworks reactivos (React/Vue/Angular)
- **Bootstrap 5.3:** Framework CSS
- **Jinja2 Templates:** Renderizado server-side
- **Fetch API:** Para llamadas AJAX a endpoints

## 3. Autenticación y Seguridad

### Sesiones

- Sesiones Flask compatibles via `SecureCookieSessionInterface`
- `flask_session` inyectado en endpoints via `Depends(get_flask_session)`
- Cookie `session` con `httponly=True, samesite=lax`

### CSRF Tokens (Crítico)

**Generación y almacenamiento:**
```python
csrf_token = flask_session.get("csrf_token")
if not csrf_token:
    csrf_token = secrets.token_urlsafe(32)
    flask_session["csrf_token"] = csrf_token
```

**En templates:**
- Meta tag: `<meta name="csrf-token" content="{{ csrf_token_value }}">`
- Todas las páginas deben pasar `csrf_token_value` al contexto

**Validación en endpoints:**
- Header requerido: `X-CSRFToken` (o `X-CSRF-Token`)
- Validación via: `Depends(verify_csrf_token)`
- Para POST de formularios tradicionales, también se acepta campo `csrf_token`

### Contexto Requerido en Templates

Todas las páginas deben incluir en el contexto:
- `url_for`: Función para generar URLs
- `current_user_role`: Rol del usuario actual (string)
- `csrf_token_value`: Token CSRF para peticiones POST
- `session`: Datos básicos de sesión
- `g`: Objeto con `csp_nonce` para scripts inline

## 4. Gestión de Templates

### Variables Globales Requeridas

```python
{
    "request": request,                    # Requerido por Jinja2
    "url_for": url_for,                    # Generación de URLs
    "current_user_role": role,             # Rol para mostrar/ocultar botones
    "csrf_token_value": csrf_token,        # Token para POSTs
    "session": session_data,               # Datos de sesión
    "g": {"csp_nonce": csp_nonce}        # Nonce para CSP
}
```

### Jerarquía de Templates

- `base.html`: Layout principal con navegación
- `dockerlabs/`: Templates de DockerLabs principal
- `bunkerlabs/`: Templates de BunkerLabs (zona protegida)
- `dockerlabs/auth/`: Login, registro, recuperación
- `dockerlabs/admin/`: Gestión de usuarios, máquinas, backups
- `dockerlabs/user/`: Perfil, estadísticas, writeups

## 5. Multi-Dominio: DockerLabs vs BunkerLabs

| Característica | DockerLabs | BunkerLabs |
|----------------|------------|------------|
| **Origen** | `origen="docker"` | `origen="bunker"` |
| **URL** | `/` | `/bunkerlabs` |
| **Dificultad** | Muy Fácil, Fácil, Medio, Difícil | Muy Fácil, Fácil, Medio, Difícil, Real |
| **PIN** | Opcional | Requerido (excepto Entorno Real) |
| **Entorno Real** | No disponible | Checkbox disponible |
| **Acceso** | Público | Requiere PIN o invitación |

### Campos Específicos de BunkerLabs

- `pin`: Flag/PIN de la máquina
- `entorno_real`: Checkbox para máquinas de entorno de producción real (omite PIN y dificultad fija a "Real")

## 6. Endpoints API Clave

### Autenticación
- `POST /api/auth/login` - Inicio de sesión
- `POST /api/auth/register` - Registro de usuario
- `POST /api/auth/recover` - Recuperación de contraseña con PIN

### Writeups
- `POST /api/submit_writeup` - Enviar writeup (requiere CSRF en header)
- `POST /api/writeups/recibidos/{id}/aprobar` - Aprobar writeup pendiente

### Máquinas (Admin)
- `GET /add-maquina` - Página de formulario
- `POST /api/add-maquina` - Crear máquina (requiere rol admin)
- `POST /api/gestion-maquinas/upload-logo` - Subir logo de máquina

### Perfil
- `POST /api/upload-profile-photo` - Subir foto de perfil
- `POST /api/update_social_links` - Actualizar LinkedIn, GitHub, YouTube
- `POST /api/change_password` - Cambiar contraseña

### Backups (Admin)
- `GET /backups` - Página de gestión
- `POST /backups/download` - Descargar backup ZIP
- `POST /backups/restore` - Restaurar backup

## 7. Patrones de Código

### Estructura de Rutas

Las rutas se registran en `routers.py` o en módulos separados bajo `dockerlabs/routes/`:

```python
def register_XXX_routes(api_router, pages_router, ...):
    @api_router.post("/endpoint")
    async def api_endpoint(..., csrf_ok: bool = Depends(verify_csrf_token)):
        # Lógica API
        pass

    @pages_router.get("/page", response_class=HTMLResponse)
    def page_endpoint(...):
        # Renderizar template
        pass
```

### Validación de Roles

```python
role = flask_session.get("role", "")
if role not in ("admin", "moderador"):
    return JSONResponse(status_code=403, content={"error": "Acceso denegado"})
```

### Manejo de Errores

```python
try:
    # Operación DB
    alchemy_db.session.commit()
except Exception as e:
    alchemy_db.session.rollback()
    return JSONResponse(status_code=500, content={"error": str(e)})
```

## 8. Consideraciones de Seguridad

1. **Siempre validar CSRF** en endpoints que modifiquen estado (POST, PUT, DELETE)
2. **Nunca confiar en datos del cliente** sin validación (validators.py)
3. **Sanitizar filenames** con `secure_filename()` de Werkzeug
4. **Validar tipos MIME** de archivos subidos (imágenes solo)
5. **Límites de tamaño:** 5MB para perfiles, 2MB para logos
6. **CSP Nonce:** Scripts inline requieren `nonce="{{ g.csp_nonce }}"`
7. **Rate limiting:** Endpoints sensibles deben usar `@limiter.limit()`

## 9. Dependencias Clave

```
fastapi
flask
flask-sqlalchemy
flask-login
slowapi
jinja2
pillow  # Procesamiento de imágenes
werkzeug
bleach  # Sanitización HTML
```

## 10. Estado de la Migración

- **Completado:** Sistema de autenticación, writeups, perfiles, backups
- **En progreso:** Eliminación progresiva de endpoints Flask legacy
- **Estable:** La arquitectura híbrida es funcional y mantenible a largo plazo
