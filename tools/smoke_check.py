#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Smoke check de DockerLabs.

Red de seguridad para refactorizar sin romper nada. No modifica datos:
solo importa la app, compila los módulos, parsea las plantillas y hace
peticiones GET de solo lectura.

Uso:
    python tools/smoke_check.py --baseline   # guarda el estado actual como referencia
    python tools/smoke_check.py              # compara contra la referencia

Devuelve código de salida 1 si detecta cualquier regresión.
"""

import argparse
import json
import os
import pathlib
import py_compile
import sys
import tempfile
import traceback

BASE_DIR = pathlib.Path(__file__).resolve().parent.parent
BASELINE = BASE_DIR / "tools" / "smoke_baseline.json"

sys.path.insert(0, str(BASE_DIR))


def cargar_env():
    """Carga .env en os.environ (DATABASE_URL y demás)."""
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for linea in env_path.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, _, valor = linea.partition("=")
        os.environ.setdefault(clave.strip(), valor.strip())


def compilar_modulos():
    """Compila todos los .py del proyecto. Detecta errores de sintaxis."""
    errores = []
    ficheros = 0
    tmp = tempfile.mkdtemp(prefix="smoke_pyc_")
    for ruta in BASE_DIR.rglob("*.py"):
        partes = ruta.parts
        if "venv" in partes or "__pycache__" in partes or ".git" in partes:
            continue
        ficheros += 1
        destino = os.path.join(tmp, "%d.pyc" % ficheros)
        try:
            py_compile.compile(str(ruta), cfile=destino, doraise=True, quiet=2)
        except Exception as exc:
            errores.append("%s: %s" % (ruta.relative_to(BASE_DIR), exc))
    return ficheros, errores


def inventario_rutas(app):
    """Lista ordenada de (ruta, métodos, nombre). Detecta rutas perdidas o renombradas.

    Recorre el árbol en profundidad: FastAPI envuelve los routers incluidos en
    objetos (_IncludedRouter, Mount) que no exponen `path` pero sí `routes`.
    """
    rutas = []
    vistos = set()

    def recorrer(nodo, prefijo=""):
        if id(nodo) in vistos:
            return
        vistos.add(id(nodo))

        # FastAPI envuelve cada router incluido en _IncludedRouter, que guarda
        # el router real en `original_router` (no en `routes`).
        original = getattr(nodo, "original_router", None)
        if original is not None:
            recorrer(original, prefijo)

        for r in getattr(nodo, "routes", []) or []:
            path = getattr(r, "path", None)
            if getattr(r, "original_router", None) is not None:
                recorrer(r, prefijo)
                continue
            hijos = getattr(r, "routes", None)
            sub_app = getattr(r, "app", None)
            if hijos is not None:
                recorrer(r, prefijo + (path or ""))
                continue
            if sub_app is not None and getattr(sub_app, "routes", None) is not None:
                recorrer(sub_app, prefijo + (path or ""))
                continue
            if not path:
                continue
            rutas.append({
                "path": prefijo + path,
                "methods": sorted(getattr(r, "methods", []) or []),
                "name": getattr(r, "name", ""),
            })

    recorrer(app)

    # Segunda fuente, independiente: el esquema OpenAPI. Cubre lo que el
    # recorrido pudiera perderse si FastAPI cambia su estructura interna.
    try:
        for path, ops in (app.openapi().get("paths") or {}).items():
            for metodo in ops:
                rutas.append({
                    "path": path,
                    "methods": [metodo.upper()],
                    "name": "(openapi)",
                })
    except Exception as exc:
        rutas.append({"path": "ERROR_OPENAPI", "methods": [], "name": str(exc)})
    vistas = {json.dumps(x, sort_keys=True) for x in rutas}
    unicas = [json.loads(x) for x in vistas]
    unicas.sort(key=lambda r: (r["path"], tuple(r["methods"]), r["name"]))
    return unicas, len(unicas)


def parsear_plantillas():
    """Parsea todas las plantillas Jinja. Detecta errores de sintaxis de plantilla."""
    from dockerlabs.routers import templates
    env = templates.env
    errores = []
    nombres = sorted(n for n in env.list_templates(extensions=["html"])
                     if not os.path.basename(n).startswith("._"))
    for nombre in nombres:
        try:
            fuente = env.loader.get_source(env, nombre)[0]
            env.parse(fuente)
        except Exception as exc:
            errores.append("%s: %s" % (nombre, exc))
    return nombres, errores


# GET de solo lectura. Nunca métodos que muten estado.
RUTAS_HTTP = [
    "/",
    "/api",
    "/api/ranking_autores",
    "/api/ranking_writeups",
    "/login",
    "/register",
    "/bunkerlabs",
    "/add-maquina",
    "/gestion-maquinas",
    "/maquinas-hechas",
    "/agradecimientos",
    "/img/maquina/277",
    "/static/dockerlabs/js/utils.js",
    "/ruta-que-no-existe-smoke-test",
]


def smoke_http(app):
    """Códigos de estado de rutas de solo lectura."""
    from fastapi.testclient import TestClient
    resultados = {}
    with TestClient(app, follow_redirects=False) as client:
        for ruta in RUTAS_HTTP:
            try:
                resp = client.get(ruta)
                resultados[ruta] = resp.status_code
            except Exception as exc:
                resultados[ruta] = "EXCEPCION: %s" % type(exc).__name__
    return resultados


def recoger():
    cargar_env()
    estado = {}

    n_ficheros, errores_compil = compilar_modulos()
    estado["modulos_compilados"] = n_ficheros
    estado["errores_compilacion"] = errores_compil

    import asgi
    # asgi.app es un envoltorio ASGI; el FastAPI con las rutas es fastapi_app
    app = getattr(asgi, "fastapi_app", None) or asgi.app

    rutas, n_rutas = inventario_rutas(app)
    estado["rutas"] = rutas
    estado["n_rutas"] = n_rutas

    plantillas, errores_plantillas = parsear_plantillas()
    estado["plantillas"] = plantillas
    estado["errores_plantillas"] = errores_plantillas

    estado["http"] = smoke_http(app)
    return estado


def comparar(actual, base):
    """Devuelve lista de regresiones."""
    fallos = []

    for clave in ("errores_compilacion", "errores_plantillas"):
        if actual[clave]:
            fallos.append("%s: %s" % (clave, actual[clave]))

    rutas_base = {(r["path"], tuple(r["methods"])) for r in base["rutas"]}
    rutas_act = {(r["path"], tuple(r["methods"])) for r in actual["rutas"]}
    for r in sorted(rutas_base - rutas_act):
        fallos.append("RUTA PERDIDA: %s %s" % (r[1], r[0]))
    nuevas = sorted(rutas_act - rutas_base)

    plant_base = set(base["plantillas"])
    plant_act = set(actual["plantillas"])
    for p in sorted(plant_base - plant_act):
        fallos.append("PLANTILLA PERDIDA: %s" % p)

    for ruta, codigo in base["http"].items():
        actual_cod = actual["http"].get(ruta)
        if actual_cod != codigo:
            fallos.append("HTTP CAMBIADO %s: %s -> %s" % (ruta, codigo, actual_cod))

    return fallos, nuevas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true", help="guardar el estado actual como referencia")
    args = ap.parse_args()

    try:
        estado = recoger()
    except Exception:
        print("FALLO AL RECOGER EL ESTADO:")
        traceback.print_exc()
        return 1

    print("modulos compilados : %d (errores: %d)" % (estado["modulos_compilados"], len(estado["errores_compilacion"])))
    print("rutas registradas  : %d" % estado["n_rutas"])
    print("plantillas         : %d (errores: %d)" % (len(estado["plantillas"]), len(estado["errores_plantillas"])))
    print("http comprobadas   : %d" % len(estado["http"]))

    if args.baseline:
        BASELINE.parent.mkdir(parents=True, exist_ok=True)
        BASELINE.write_text(json.dumps(estado, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
        print("\nreferencia guardada en %s" % BASELINE.relative_to(BASE_DIR))
        for clave in ("errores_compilacion", "errores_plantillas"):
            if estado[clave]:
                print("  AVISO, %s: %s" % (clave, estado[clave]))
        return 0

    if not BASELINE.exists():
        print("\nNo hay referencia. Ejecuta primero: python tools/smoke_check.py --baseline")
        return 1

    base = json.loads(BASELINE.read_text(encoding="utf-8"))
    fallos, nuevas = comparar(estado, base)

    if nuevas:
        print("\nrutas nuevas (informativo, no es fallo):")
        for p, m in nuevas:
            print("  + %s %s" % (list(m), p))

    if fallos:
        print("\n=== %d REGRESIONES ===" % len(fallos))
        for f in fallos:
            print("  ! %s" % f)
        return 1

    print("\nSIN REGRESIONES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
