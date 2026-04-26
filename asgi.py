from fastapi import FastAPI, Request
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dockerlabs.app import app as flask_app
from dockerlabs.routers import api_router

# Rate limiter para FastAPI (compatible con Flask sessions)
limiter = Limiter(key_func=get_remote_address)

fastapi_app = FastAPI(
    title="DockerLabs API (FastAPI + Flask)",
    docs_url="/fastapi-docs",
    openapi_url="/fastapi-openapi.json"
)

fastapi_app.state.limiter = limiter
fastapi_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

fastapi_app.include_router(api_router)

@fastapi_app.get("/fastapi-status")
def get_status():
    return {"status": "ok", "message": "FastAPI is running alongside Flask!"}

fastapi_app.mount("/", WSGIMiddleware(flask_app))

application = fastapi_app
app = application
