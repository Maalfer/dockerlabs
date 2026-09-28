#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Elimina imports sin usar regenerando cada sentencia completa.

Solo actua sobre los ficheros que se le pasan. Nunca toca `__future__`
(directiva del compilador) ni imports de modulo entero cuyo unico proposito
sea el efecto secundario (esos hay que excluirlos a mano).
"""
import ast
import sys


def nombres_usados(arbol):
    usados = set()
    for n in ast.walk(arbol):
        if isinstance(n, ast.Name):
            usados.add(n.id)
        elif isinstance(n, ast.Attribute):
            base = n
            while isinstance(base, ast.Attribute):
                base = base.value
            if isinstance(base, ast.Name):
                usados.add(base.id)
        elif isinstance(n, ast.Constant) and isinstance(n.value, str):
            for t in n.value.replace(".", " ").replace(",", " ").split():
                usados.add(t.strip("'\"[]()"))
    return usados


def podar(ruta):
    fuente = open(ruta, encoding="utf-8").read()
    arbol = ast.parse(fuente)
    lineas = fuente.split("\n")
    usados = nombres_usados(arbol)

    reemplazos = {}   # (inicio, fin) -> texto nuevo o None para borrar
    quitados = 0

    for n in arbol.body:          # solo imports de nivel superior
        if isinstance(n, ast.ImportFrom) and n.module == "__future__":
            continue
        if isinstance(n, ast.Import):
            mantener = [a for a in n.names
                        if (a.asname or a.name.split(".")[0]) in usados]
            if len(mantener) == len(n.names):
                continue
            quitados += len(n.names) - len(mantener)
            if not mantener:
                reemplazos[(n.lineno, n.end_lineno)] = None
            else:
                reemplazos[(n.lineno, n.end_lineno)] = "\n".join(
                    "import %s%s" % (a.name, " as " + a.asname if a.asname else "")
                    for a in mantener)
        elif isinstance(n, ast.ImportFrom):
            if any(a.name == "*" for a in n.names):
                continue
            mantener = [a for a in n.names if (a.asname or a.name) in usados]
            if len(mantener) == len(n.names):
                continue
            quitados += len(n.names) - len(mantener)
            if not mantener:
                reemplazos[(n.lineno, n.end_lineno)] = None
            else:
                modulo = "." * n.level + (n.module or "")
                piezas = ["%s%s" % (a.name, " as " + a.asname if a.asname else "")
                          for a in mantener]
                una_linea = "from %s import %s" % (modulo, ", ".join(piezas))
                if len(una_linea) <= 99:
                    reemplazos[(n.lineno, n.end_lineno)] = una_linea
                else:
                    reemplazos[(n.lineno, n.end_lineno)] = (
                        "from %s import (\n    %s,\n)" % (modulo, ",\n    ".join(piezas)))

    if not reemplazos:
        print("  %-42s sin cambios" % ruta)
        return 0

    salida = []
    i = 1
    while i <= len(lineas):
        clave = next((k for k in reemplazos if k[0] == i), None)
        if clave:
            nuevo = reemplazos[clave]
            if nuevo is not None:
                salida.append(nuevo)
            i = clave[1] + 1
        else:
            salida.append(lineas[i - 1])
            i += 1

    texto = "\n".join(salida)
    ast.parse(texto)           # falla aqui antes de escribir nada
    open(ruta, "w", encoding="utf-8").write(texto)
    print("  %-42s %d imports eliminados" % (ruta, quitados))
    return quitados


if __name__ == "__main__":
    total = sum(podar(r) for r in sys.argv[1:])
    print("\nTOTAL eliminados: %d" % total)
