"""Toda referencia de una plantilla a otro fichero existe y todo script en
línea lleva el nonce CSP."""
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

RAIZ = Path(__file__).resolve().parents[2]
PLANTILLAS = RAIZ / "templates"
ESTATICOS = RAIZ / "static"

_RE_STATIC = re.compile(
    r"""static_v\(\s*['"]([^'"]+)['"]\s*\)"""
    r"""|url_for\(\s*['"]static['"]\s*,\s*filename\s*=\s*['"]([^'"]+)['"]\s*\)"""
)
_RE_PLANTILLA = re.compile(r"""\{%-?\s*(?:include|extends)\s+['"]([^'"]+)['"]""")


def _plantillas():
    return sorted(PLANTILLAS.rglob("*.html"))


def _referencias(regex):
    for plantilla in _plantillas():
        texto = plantilla.read_text(encoding="utf-8")
        for m in regex.finditer(texto):
            ruta = next(g for g in m.groups() if g)
            if "{{" in ruta or "{%" in ruta:  # rutas construidas en tiempo de render
                continue
            yield plantilla.relative_to(RAIZ), ruta


def test_hay_plantillas_y_referencias():
    assert _plantillas()
    assert list(_referencias(_RE_STATIC))


def test_recursos_estaticos_existen():
    rotos = [f"{p}: {r}" for p, r in _referencias(_RE_STATIC) if not (ESTATICOS / r).is_file()]
    assert not rotos, "recursos estáticos que no existen:\n" + "\n".join(rotos)


def test_includes_y_extends_existen():
    rotos = [f"{p}: {r}" for p, r in _referencias(_RE_PLANTILLA) if not (PLANTILLAS / r).is_file()]
    assert not rotos, "plantillas incluidas/extendidas que no existen:\n" + "\n".join(rotos)


_RE_SCRIPT = re.compile(r"<script\b([^>]*)>", re.I)


def test_scripts_en_linea_llevan_nonce():
    """Todo <script> en línea (sin src) necesita el nonce CSP, o el navegador lo
    bloquearía en cuanto la CSP pase de report-only a obligatoria."""
    sin_nonce = []
    for plantilla in _plantillas():
        for n, linea in enumerate(plantilla.read_text(encoding="utf-8").splitlines(), 1):
            for m in _RE_SCRIPT.finditer(linea):
                attrs = m.group(1)
                if "src=" in attrs or "nonce=" in attrs or "application/ld+json" in attrs:
                    continue
                sin_nonce.append(f"{plantilla.relative_to(RAIZ)}:{n}")
    assert not sin_nonce, "scripts en línea sin nonce:\n" + "\n".join(sin_nonce)
