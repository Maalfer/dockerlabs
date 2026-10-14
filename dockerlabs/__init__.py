"""Paquete de la aplicación DockerLabs.

Expone ``__version__``, única fuente de verdad para la versión de la
aplicación (SemVer: MAJOR.MINOR.PATCH — ver CONTRIBUTING.md).

La versión vive en el fichero ``VERSION`` en la raíz del repo (no aquí en
código) para que herramientas no-Python (CI, Docker, scripts de release,
badges del README) puedan leerla sin tener que importar el paquete.
Subir de versión es, por tanto, editar un único fichero de una línea.
"""

from pathlib import Path

__all__ = ["__version__"]

_VERSION_FILE = Path(__file__).resolve().parent.parent / "VERSION"

try:
    __version__ = _VERSION_FILE.read_text(encoding="utf-8").strip()
except OSError:
    # No debe poder tumbar la app: si falta el fichero, se degrada a un
    # valor reconocible en vez de lanzar una excepción en el arranque.
    __version__ = "0.0.0-unknown"
