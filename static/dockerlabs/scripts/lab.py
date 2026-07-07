#!/usr/bin/env python3
# =============================================================================
#  PLANTILLA DE LABORATORIO  ·  DockerLabs  ·  Sección "Empezar de 0"
# =============================================================================
#
#  LEE ESTAS REGLAS ANTES DE CREAR TU LABORATORIO:
#
#   1) SOLO LIBRERÍA ESTÁNDAR DE PYTHON.
#      NO uses librerías que requieran `pip install` (Flask, Django, requests,
#      fastapi, etc.). El alumno tiene que poder ejecutar el lab con SOLO:
#
#            python3 lab.py
#
#      Usa únicamente módulos que ya vienen con Python:
#      http.server, socketserver, sqlite3, json, base64, hashlib, html, re...
#
#   2) EL SERVIDOR DEBE ESCUCHAR EN 0.0.0.0
#      Deja HOST = "0.0.0.0" (no lo cambies a 127.0.0.1), así el laboratorio
#      queda accesible.
#
#   3) UN ÚNICO ARCHIVO .py
#      Todo el laboratorio vive en este mismo archivo. Es lo que se sube y se
#      descarga desde DockerLabs.
#
#   4) LA FLAG usa el formato  DL{...}
#
# -----------------------------------------------------------------------------
#  Cómo se ejecuta:   python3 lab.py
#  Luego abre:        http://<IP-de-la-maquina>:8000
# =============================================================================

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# --- Configuración del laboratorio ------------------------------------------
HOST = "0.0.0.0"                  # ⚠️ debe quedarse en 0.0.0.0
PORT = 8000
FLAG = "DL{cambia_esta_flag}"     # TODO: pon aquí la flag de tu reto

TITULO   = "Mi primer laboratorio"
OBJETIVO = "Describe aquí qué tiene que conseguir el alumno para sacar la flag."


class Lab(BaseHTTPRequestHandler):

    def _responder(self, codigo, html):
        datos = html.encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(datos)))
        self.end_headers()
        self.wfile.write(datos)

    def do_GET(self):
        # ------------------------------------------------------------------
        # TODO: aquí va la lógica VULNERABLE de tu laboratorio.
        #       Este ejemplo solo muestra una página de bienvenida.
        # ------------------------------------------------------------------
        if self.path == "/":
            self._responder(200, f"""
                <!doctype html>
                <meta charset="utf-8">
                <title>{TITULO}</title>
                <h1>{TITULO}</h1>
                <p>{OBJETIVO}</p>
                <p>Edita este archivo <code>lab.py</code> para construir tu reto.</p>
            """)
        else:
            self._responder(404, "<h1>404 - No encontrado</h1>")

    # Silencia el log por defecto del servidor (opcional)
    def log_message(self, *args):
        pass


def main():
    print(f"[+] Laboratorio escuchando en http://{HOST}:{PORT}")
    print(f"[+] Abre http://<tu-ip>:{PORT} en el navegador para empezar")
    ThreadingHTTPServer((HOST, PORT), Lab).serve_forever()


if __name__ == "__main__":
    main()
