from fastapi import FastAPI
from fastapi.middleware.wsgi import WSGIMiddleware
from dockerlabs.app import app as flask_app

fastapi_app = FastAPI(
    title="DockerLabs API (FastAPI + Flask)",
    docs_url="/fastapi-docs",
    openapi_url="/fastapi-openapi.json"
)

@fastapi_app.get("/fastapi-status")
def get_status():
    return {"status": "ok", "message": "FastAPI is running alongside Flask!"}

fastapi_app.mount("/", WSGIMiddleware(flask_app))

application = fastapi_app
app = application
