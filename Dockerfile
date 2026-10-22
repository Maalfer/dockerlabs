FROM python:3.13-slim

# build-essential + libssl-dev: la dependencia "scrypt" (hashing de
# contraseñas) no publica wheels precompiladas para todas las plataformas
# y necesita compilar contra OpenSSL.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 dockerlabs \
    && mkdir -p uploads/perfiles uploads/logos uploads/certificados \
    && chown -R dockerlabs:dockerlabs /app
USER dockerlabs

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/fastapi-status', timeout=3)" || exit 1

CMD ["uvicorn", "asgi:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
