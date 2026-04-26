import secrets
import time
from collections import defaultdict
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dockerlabs.database import init_db
from dockerlabs.routers import api_router, pages_router

# Inicializar Base de Datos
init_db()

# Rate limiter simple por IP
rate_limit_store = defaultdict(list)
RATE_LIMIT = 100  # requests por minuto
RATE_WINDOW = 60  # segundos

# Rate limiter para FastAPI
# Configuración: 100 peticiones por minuto por IP (global)
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
    storage_uri="memory://"
)

fastapi_app = FastAPI(
    title="DockerLabs API",
    docs_url="/fastapi-docs",
    openapi_url="/fastapi-openapi.json"
)

fastapi_app.state.limiter = limiter
fastapi_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Middleware de Rate Limiting
@fastapi_app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Obtener IP del cliente
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    
    # Limpiar requests antiguos (más de RATE_WINDOW segundos)
    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip] 
        if current_time - t < RATE_WINDOW
    ]
    
    # Verificar si excede el límite
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "detail": f"Maximum {RATE_LIMIT} requests per {RATE_WINDOW} seconds"}
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
