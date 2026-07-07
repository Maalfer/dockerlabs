#!/bin/bash

echo "Starting application without memcached..."

if [ -f "/app/dockerlabs.db" ]; then
    echo "Found dockerlabs.db"
fi

if [ -f "/app/bunkerlabs.db" ]; then
    echo "Found bunkerlabs.db"
fi

echo "Starting Application with Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile - \
    --error-logfile - \
    asgi:application
