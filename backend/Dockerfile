FROM python:3.11-slim-bookworm

# Install system dependencies
# memcached: required for rate limiting
# gcc, libffi-dev: often required for building python extensions
# libjpeg-dev, zlib1g-dev: required for Pillow
RUN apt-get update && apt-get install -y \
    memcached \
    gcc \
    libffi-dev \
    libjpeg-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user to run the application
RUN useradd -m -u 1000 dockerlabs

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories for static files
RUN mkdir -p /app/static/images/perfiles \
    /app/static/images/logos \
    /app/static/images/logos-bunkerlabs

# Copy application code
COPY . .

# Set ownership of the application directory to the non-root user
RUN chown -R dockerlabs:dockerlabs /app

# Prepare entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && chown dockerlabs:dockerlabs /entrypoint.sh

# Switch to the non-root user
USER dockerlabs

# Expose the application port
EXPOSE 5000

# Set the entrypoint
ENTRYPOINT ["/entrypoint.sh"]
