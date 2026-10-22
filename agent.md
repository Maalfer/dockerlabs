# DockerLabs – Arquitectura y decisiones de diseño

## 1. Almacenamiento de imágenes

Las imágenes de perfil y logos de máquinas se guardan en `uploads/`:

```
uploads/
├── perfiles/    # user_{user_id}_{timestamp}.webp
└── logos/       # docker_{machine_id}_{timestamp}.webp  |  bunker_{...}.webp
```

El timestamp evita colisiones entre versiones. `.gitignore` excluye toda la carpeta `uploads/` (incluidos los `.gitkeep` que puede haber dentro en el VPS en vivo): las subcarpetas no están trackeadas en git, se crean solas con `os.makedirs(exist_ok=True)` la primera vez que algo se sube.

Las columnas `profile_image_data` y `logo_data` (BLOB) están marcadas como `deferred` en los modelos y solo se acceden si `*_path` es NULL — compatibilidad con datos anteriores a la migración a disco.

## 2. Stack técnico

- **FastAPI** + Uvicorn (2 workers en producción)
- **MariaDB** via PyMySQL y SQLAlchemy
- **Jinja2** para templates HTML
- **itsdangerous** para firmado de cookies de sesión
- **Werkzeug** para hashing de contraseñas (scrypt) y `secure_filename`
- **PIL/Pillow** para procesamiento de imágenes (WebP)
- **nginx** como reverse proxy con TLS (certificado Cloudflare Origin)

## 3. Base de datos

El `scoped_session` está indexado por un `ContextVar` por request (no por hilo), porque Uvicorn ejecuta los endpoints síncronos en un threadpool mientras el middleware corre en el event loop. La sesión se crea en el worker y se limpia en el middleware al finalizar el request.

## 4. Sesiones

Sesiones firmadas con `URLSafeTimedSerializer` de itsdangerous. La clave secreta vive en la tabla `session_config` (persiste entre reinicios del servicio).

Función de inyección: `get_session(request)` en `routers.py`. Devuelve un dict con `user_id`, `username`, `role`, `csrf_token`.

## 5. CSRF

Token HMAC stateless: `HMAC-SHA256(secret_key, session._id)`. No se persiste en la cookie — se recalcula en cada request a partir del `_id` de sesión. Los endpoints de escritura validan via `Depends(verify_csrf_token)`.

## 6. Estructura de routers

```python
api_router   = APIRouter(prefix="/api")   # /api/*
pages_router = APIRouter()                # Páginas HTML sin prefijo
```

Los submódulos bajo `routes/` se registran al final de `routers.py` via funciones `register_*_routes(api_router, pages_router, get_session, db, ...)`.

## 7. DockerLabs vs BunkerLabs

Las dos plataformas comparten modelos y base de datos. Se distinguen por el campo `origen`:
- `"docker"` → DockerLabs (acceso público)
- `"bunker"` → BunkerLabs (acceso por PIN o invitación)

BunkerLabs tiene un campo adicional `pin` y el modo `entorno_real` que omite el PIN y fija la dificultad a "Real".

## 8. Rate limiting

Middleware ASGI personalizado en `asgi.py`: 300 req/min por IP, ventana deslizante en memoria. Excluye `/static/`, `/img/` y `/database/` (prefijo histórico; la carpeta `database/` ya no existe). Al ser en memoria, el límite efectivo con 2 workers es 300×2 por IP; suficiente para producción sin dependencias externas.

## 9. Seguridad en uploads

1. Verificación de tipo MIME (`content_type.startswith('image/')`)
2. Apertura y verificación con PIL (`img.verify()`)
3. Validación de contenido con `validators.validate_image_content()`
4. Conversión a WebP antes de guardar (excepto SVG en logos)
5. `secure_filename()` en el nombre original
6. Límites de tamaño: 5 MB perfiles, 2 MB logos

## 10. Cache-busting de estáticos

La función `static_v(filename)` en Jinja2 añade `?v=<mtime_hex>` a los assets. Cuando se modifica un archivo su mtime cambia → la URL cambia → navegadores y CDN descargan la versión nueva sin necesidad de invalidar manualmente.

## 11. Reglas para IAs y agentes que trabajen en este proyecto

- **Sin comentarios innecesarios.** Solo añadir un comentario cuando el motivo no sea evidente leyendo el código. No comentar lo que el código ya dice por sí solo.
- **Sin emojis** en código, comentarios ni documentación técnica.
- **Sin rastros de migración.** No dejar en el código alusiones a frameworks anteriores, fases de migración ni referencias a cómo estaba antes.
- **Nombres claros.** Las variables, funciones y parámetros deben describir su propósito. No usar abreviaciones ni nombres genéricos como `data`, `obj`, `tmp` salvo que el contexto los haga obvios.
- **No sobre-documentar.** Los módulos y funciones tienen una docstring corta solo si aporta información que el nombre no da. Sin bloques de docstring de varios párrafos.
- **Código de producción.** Cada cambio debe ser seguro, reversible y no romper funcionalidad existente. Hacer backup de BD antes de cualquier cambio de esquema.
