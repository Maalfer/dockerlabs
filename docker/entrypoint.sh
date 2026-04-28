#!/bin/bash

# memcached eliminado - rate limiting configurado para Cloudflare
echo "Starting application without memcached..."

# Check if database files exist (optional, mostly for info)
if [ -f "/app/dockerlabs.db" ]; then
    echo "Found dockerlabs.db"
fi

if [ -f "/app/bunkerlabs.db" ]; then
    echo "Found bunkerlabs.db"
fi

# Start Flask application using Gunicorn
# Using 4 workers and Uvicorn worker class for ASGI support
echo "Starting Application with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile - \
    --error-logfile - \
    asgi:application
