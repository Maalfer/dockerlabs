#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Detecta código potencialmente muerto: imports sin usar y funciones nunca referenciadas.

Solo INFORMA, no modifica nada. Cada candidato debe verificarse a mano antes
de tocarlo (los nombres usados dentro de cadenas, plantillas o getattr no se
detectan estáticamente).
"""
import ast
import pathlib
import sys

BASE = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
EXCLUIR = {"venv", "__pycache__", ".git", "tools"}


def ficheros_py():
    for r in sorted(BASE.rglob("*.py")):
        if EXCLUIR & set(r.parts):
            continue
        yield r


def nombres_usados(arbol, fuente):
    """Todos los identificadores referenciados en el módulo."""
    usados = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Name):
            usados.add(n.id)
        elif isinstance(n, ast.Attribute):
            # captura el objeto base de a.b.c
            base = n
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                usados.add(base.id)
    # Los nombres citados en cadenas (type hints, __all__, getattr) cuentan
    for n in ast.walk(arbol):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            for token in n.value.replace(".", " ").replace(",", " ").split():
                usados.add(token.strip("'\"[]()"))
    return usados


def imports_del_modulo(arbol):
    """(nombre_local, linea, texto) de cada import."""
    res = []
    for n in ast.walk(arbol):
        if isinstance(n, ast.Import):
            for a in n.names:
                local = a.asname or a.name.split(".")[0]
                res.append((local, n.lineno, "import %s%s" % (a.name, " as " + a.asname if a.asname else "")))
        elif isinstance(n, ast.ImportFrom):
            if n.names and n.names[0].name == "*":
                continue
            for a in n.names:
                local = a.asname or a.name
                res.append((local, n.lineno, "from %s import %s%s" % (
                    n.module or ".", a.name, " as " + a.asname if a.asname else "")))
    return res


def main():
    total_no_usados = 0
    print("=" * 70)
    print("IMPORTS SIN USAR (candidatos, verificar a mano)")
    print("=" * 70)
    for ruta in ficheros_py():
        try:
            fuente = ruta.read_text(encoding="utf-8")
            arbol = ast.parse(fuente)
        except Exception as exc:
            print("  %s: NO SE PUDO ANALIZAR (%s)" % (ruta.relative_to(BASE), exc))
            continue

        usados = nombres_usados(arbol, fuente)
        sin_usar = []
        for local, linea, texto in imports_del_modulo(arbol):
            if local == "*":
                continue
            if local not in usados:
                sin_usar.append((linea, local, texto))
        if sin_usar:
            print("\n%s" % ruta.relative_to(BASE))
            for linea, local, texto in sorted(sin_usar):
                print("  L%-5d %-22s  %s" % (linea, local, texto))
                total_no_usados += 1

    print("\nTOTAL imports sin usar: %d" % total_no_usados)

    # --- funciones/clases de nivel superior nunca referenciadas en el proyecto ---
    print()
    print("=" * 70)
    print("DEFINICIONES NIVEL SUPERIOR NUNCA REFERENCIADAS (candidatos)")
    print("=" * 70)
    fuentes = {}
    for ruta in ficheros_py():
        try:
            fuentes[ruta] = ruta.read_text(encoding="utf-8")
        except Exception:
            pass
    todo_el_texto = "\n".join(fuentes.values())
    # las plantillas tambien pueden llamar funciones
    for t in BASE.rglob("*.html"):
        if EXCLUIR & set(t.parts):
            continue
        try:
            todo_el_texto += "\n" + t.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            pass

    candidatos = 0
    for ruta, fuente in fuentes.items():
        try:
            arbol = ast.parse(fuente)
        except Exception:
            continue
        for n in arbol.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                nombre = n.name
                if nombre.startswith("__"):
                    continue
                # Los handlers con decorador (@api_router.get, @app.middleware...)
                # se referencian desde el decorador, no por nombre: no son muertos.
                if getattr(n, "decorator_list", None):
                    continue
                # cuenta apariciones fuera de su propia definicion
                apariciones = todo_el_texto.count(nombre)
                if apariciones <= 1:
                    print("  %-45s L%-5d %s" % (ruta.relative_to(BASE), n.lineno, nombre))
                    candidatos += 1
    print("\nTOTAL definiciones nunca referenciadas: %d" % candidatos)


if __name__ == "__main__":
    main()
