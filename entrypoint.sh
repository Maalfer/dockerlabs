#!/bin/bash

# Start memcached service in the background
echo "Starting memcached service..."
memcached -u root -d

# Give memcached a moment to start
sleep 2

# Check if database files exist and set proper permissions
if [ -f "/app/dockerlabs.db" ]; then
    echo "Setting permissions for dockerlabs.db..."
    chmod 666 /app/dockerlabs.db
fi

if [ -f "/app/bunkerlabs.db" ]; then
    echo "Setting permissions for bunkerlabs.db..."
    chmod 666 /app/bunkerlabs.db
fi

# Ensure the app directory is writable (for database creation if they don't exist)
chmod 777 /app

# Start Flask application
echo "Starting Flask application..."
exec python3 run.py
