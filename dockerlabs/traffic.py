"""Criterios compartidos para las estadísticas de tráfico (visitas, clics
salientes, descargas).

Contexto de despliegue: Cloudflare -> nginx -> uvicorn. nginx restaura la IP
real del cliente con el módulo realip (solo si la conexión viene de rangos de
Cloudflare, ver /etc/nginx/conf.d/cloudflare-realip.conf) y la pasa a la app en
`X-Real-IP`, sobrescribiendo siempre lo que mande el cliente. Por eso la IP se
lee de X-Real-IP y NO de la cabecera `CF-Connecting-IP`, que cualquiera puede
falsear si llega directamente al origen y así inflar los únicos.
"""
import hashlib
import os
import re
import time

_SALT = os.environ.get("SECRET_KEY", "dockerlabs")

# IPs propias (el propio servidor, monitores internos...) que no son visitas.
# Ampliable por entorno: STATS_IGNORE_IPS="1.2.3.4,5.6.7.8"
_IGNORE_IPS = {"127.0.0.1", "::1", "87.106.125.75"} | {
    ip.strip() for ip in os.environ.get("STATS_IGNORE_IPS", "").split(",") if ip.strip()
}

_BOT_MARKERS = (
    "bot", "crawl", "spider", "slurp", "curl", "wget", "python", "httpx", "go-http",
    "java/", "okhttp", "axios", "node-fetch", "libwww", "scrapy", "httpclient",
    "monitor", "uptime", "headless", "phantom", "selenium", "puppeteer", "playwright",
    "lighthouse", "pagespeed", "gtmetrix", "pingdom", "preview", "fetch", "scan",
    "probe", "check", "validator", "facebookexternalhit", "ggpht", "googleimageproxy",
    "serviceextension", "postman", "insomnia", "ctf-training", "http_request", "libcurl",
)

# Un navegador real lleva alguno de estos motores en el UA.
_BROWSER_ENGINE = re.compile(r"applewebkit|gecko/|firefox/|trident/", re.I)
_OLD_BROWSER = re.compile(r"(?:Chrome|Firefox|Edge)/(\d+)", re.I)


def client_ip(request) -> str:
    return (request.headers.get("x-real-ip")
            or (request.client.host if request.client else "")).strip()


def is_human_navigation(request) -> bool:
    """True si la petición parece una navegación real de una persona.

    Capas (de más fiable a menos):
      1. Sec-Fetch-* : los navegadores modernos lo envían siempre y no es
         modificable desde JS. Se exige navigate/document; así se descartan
         prefetch, fetch()/XHR, iframes, service workers y la mayoría de scripts.
      2. Sin Sec-Fetch (navegadores antiguos o clientes HTTP): se exige
         Accept-Language, un motor de navegador en el UA y que no sea bot.
      3. Lista de UAs de bots/herramientas, versiones absurdamente antiguas
         (los scrapers suelen falsear Chrome/42, Edge/12...), y IPs propias.
    """
    h = request.headers
    ua = h.get("user-agent", "")
    low = ua.lower()
    if len(ua) < 30 or any(b in low for b in _BOT_MARKERS):
        return False
    if not _BROWSER_ENGINE.search(ua):
        return False
    if client_ip(request) in _IGNORE_IPS:
        return False
    if "prefetch" in (h.get("sec-purpose", "") + h.get("purpose", "")).lower():
        return False

    m = _OLD_BROWSER.search(ua)
    if m and int(m.group(1)) < 80:
        return False
    if "Edge/12" in ua or "Windows NT 5." in ua or "MSIE" in ua:
        return False

    mode, dest = h.get("sec-fetch-mode"), h.get("sec-fetch-dest")
    if mode or dest:
        return mode == "navigate" and dest in (None, "document")
    return bool(h.get("accept-language"))


def visitor_hash(request) -> str:
    """Hash truncado IP+UA+día(UTC): únicos por día sin guardar la IP."""
    ua = request.headers.get("user-agent", "")
    day = time.strftime("%Y-%m-%d", time.gmtime())
    return hashlib.sha256(f"{_SALT}|{client_ip(request)}|{ua}|{day}".encode()).hexdigest()[:16]
