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

init_db()

rate_limit_store = defaultdict(list)
API_RATE_LIMIT = 300
RATE_WINDOW = 60
# Sin esto el diccionario crece con una entrada por IP vista y no se libera
# nunca: cualquiera puede agotar la memoria del worker rotando IPs de origen.
RATE_STORE_MAX_KEYS = 10_000

fastapi_app = FastAPI(
    title="DockerLabs API",
    docs_url="/fastapi-docs",
    openapi_url="/fastapi-openapi.json"
)


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

@fastapi_app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()
    path = request.url.path

    if path.startswith("/static/") or path.startswith("/img/") or path.startswith("/database/"):
        response = await call_next(request)
        return response

    limit = API_RATE_LIMIT

    if len(rate_limit_store) > RATE_STORE_MAX_KEYS:
        for stale in [
            ip for ip, hits in rate_limit_store.items()
            if not hits or current_time - hits[-1] >= RATE_WINDOW
        ]:
            del rate_limit_store[stale]

    rate_limit_store[client_ip] = [
        t for t in rate_limit_store[client_ip]
        if current_time - t < RATE_WINDOW
    ]

    if len(rate_limit_store[client_ip]) >= limit:
        return JSONResponse(
            status_code=429,
            content={"error": "Rate limit exceeded", "detail": f"Maximum {limit} requests per {RATE_WINDOW} seconds"}
        )

    rate_limit_store[client_ip].append(current_time)

    response = await call_next(request)
    return response

@fastapi_app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    nonce = secrets.token_urlsafe(16)
    request.state.csp_nonce = nonce

    response = await call_next(request)

    response.headers['Content-Security-Policy-Report-Only'] = (
        f"default-src 'self'; "
        f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        f"script-src 'self' 'nonce-{nonce}' 'unsafe-hashes' https://www.googletagmanager.com; "
        f"img-src 'self' data: https:; "
        f"font-src 'self' https://fonts.gstatic.com; "
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

    path = request.url.path
    content_type = response.headers.get('content-type', '')
    if path.startswith('/static/'):
        if 'cache-control' not in response.headers:
            response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    elif 'text/html' in content_type:
        response.headers['Cache-Control'] = 'no-cache, must-revalidate'

    # Las imágenes (logos, avatares) pueden ser SVG subidos por usuarios. Servidos
    # como documento de primer nivel ejecutarían su <script>; una CSP restrictiva
    # y EN VIGOR (no Report-Only) los deja inertes sin afectar al uso como <img>.
    if path.startswith('/img/'):
        response.headers['Content-Security-Policy'] = "default-src 'none'; style-src 'unsafe-inline'; sandbox"

    return response

fastapi_app.mount("/static", StaticFiles(directory="static"), name="static")

fastapi_app.include_router(pages_router)
fastapi_app.include_router(api_router)

@fastapi_app.get("/fastapi-status")
def get_status():
    return {"status": "ok", "message": "FastAPI is running standalone!"}

application = fastapi_app
app = application
