import secrets
import time
from collections import defaultdict
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from dockerlabs.database import db_session, init_db, _request_scope_id
from dockerlabs.routers import api_router, pages_router

# Inicializar Base de Datos
init_db()

# Rate limiter en memoria por IP
rate_limit_store = defaultdict(list)
API_RATE_LIMIT = 300   # requests por minuto
RATE_WINDOW = 60       # segundos

fastapi_app = FastAPI(
    title="DockerLabs API",
    docs_url="/fastapi-docs",
    openapi_url="/fastapi-openapi.json"
)


# Limpieza de la sesión SQLAlchemy por request (middleware ASGI puro).
# DEBE ser ASGI puro y NO BaseHTTPMiddleware (@app.middleware): este último
# ejecuta la app en otra task de anyio, por lo que los contextvars fijados aquí
# no se propagarían al endpoint. Como middleware ASGI puro, el contextvar de
# ámbito se copia al threadpool donde corren los endpoints sincronos (def), de
# modo que la sesion creada alli queda indexada por el mismo request y se limpia
# aqui en el finally. Esto evita la fuga de conexiones que agotaba el QueuePool.
class DBSessionMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        token = _request_scope_id.set(object())
        try:
            await self.app(scope, receive, send)
        finally:
            db_session.remove()
            _request_scope_id.reset(token)


fastapi_app.add_middleware(DBSessionMiddleware)

# Middleware de Rate Limiting Inteligente
@fastapi_app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Obtener IP del cliente
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    path = request.url.path
    
    # Excluir completamente del rate limit: archivos estáticos, imágenes, y carga de imágenes
    if path.startswith("/static/") or path.startswith("/img/") or path.startswith("/database/"):
        # No aplicar rate limit a estos recursos
        response = await call_next(request)
        return response
    
    limit = API_RATE_LIMIT
    
    # Limpiar requests antiguos (más de RATE_WINDOW segundos)
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] 
        if current_time - t < RATE_WINDOW
    ]
    
    # Verificar si excede el límite
    if len(rate_limit_store[client_ip]) >= limit:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "detail": f"Maximum {limit} requests per {RATE_WINDOW} seconds"}
        )
    
    # Registrar este request
    rate_limit_store[client_ip].append(current_time)
    
    response = await call_next(request)
    return response

# Middleware de Cabeceras de Seguridad (Sustituye a @app.after_request de Flask)
@fastapi_app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    # Inyectar nonce en request state para plantillas
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce
    
    response = await call_next(request)
    
    response.headers['Content-Security-Policy-Report-Only'] = (
        f"default-src 'self'; "
        f"style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        f"script-src 'self' 'nonce-{nonce}' 'unsafe-hashes' https://cdn.jsdelivr.net https://www.googletagmanager.com; "
        f"img-src 'self' data: https:; "
        f"font-src 'self' https://fonts.gstatic.com https://cdn.jsdelivr.net; "
        f"connect-src 'self'; "
        f"frame-src 'self' https://www.youtube.com; "
        f"frame-ancestors 'self'; "
        f"object-src 'none'; "
        f"base-uri 'self'; "
        f"form-action 'self';"
    )
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = (
        'accelerometer=(), autoplay=(), camera=(), display-capture=(), '
        'encrypted-media=(), fullscreen=(), gamepad=(), geolocation=(), '
        'gyroscope=(), hid=(), idle-detection=(), magnetometer=(), '
        'microphone=(), midi=(), payment=(), picture-in-picture=(), '
        'publickey-credentials-get=(), screen-wake-lock=(), serial=(), '
        'storage-access=(), usb=(), xr-spatial-tracking=()'
    )

    # Cache-Control diferenciado:
    # - HTML: no-cache → el navegador revalida siempre el HTML
    #   Evita que el browser cachee el HTML con atributos media="print" sin resolver,
    #   lo que provoca layouts rotos en visitas posteriores (el bug de la imagen).
    # - Estáticos: 1 año de caché (immutable) → los assets no cambian sin cambiar la URL
    path = request.url.path
    content_type = response.headers.get('content-type', '')
    if path.startswith('/static/'):
        if 'cache-control' not in response.headers:
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif 'text/html' in content_type:
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'

    return response

# Montar archivos estáticos
fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir routers: páginas primero (sin prefijo), luego API (con prefijo /api)
fastapi_app.include_router(pages_router)
fastapi_app.include_router(api_router)

@fastapi_app.get("/fastapi-status")
def get_status():
    return {"status": "ok", "message": "FastAPI is running standalone!"}

application = fastapi_app
app = application
