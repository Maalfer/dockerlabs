FROM debian:latest

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    memcached \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

RUN mkdir -p /app/static/images/perfiles \
    /app/static/images/logos \
    /app/static/images/logos-bunkerlabs

RUN chmod 777 /app

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000

ENTRYPOINT ["/entrypoint.sh"]
