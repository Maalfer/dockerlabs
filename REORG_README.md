Reorganización inicial del repo

Objetivo:
- Separar backend y frontend en carpetas distintas: `backend/` y `frontend/`.

Qué hace el script `scripts/restructure_move.sh`:
- Crea las carpetas `backend/` y `frontend/` si no existen.
- Intenta mover con `git mv` (para preservar historial) los archivos y directorios clave:
  - A `backend/`: `asgi.py`, `run.py`, `entrypoint.sh`, `populate_datos.py`, `requirements.txt`, `Dockerfile`, `bunkerlabs/`, `dockerlabs/`, `database/`.
  - A `frontend/`: `templates/` y `static/`.
- Si el repositorio no está bajo Git, usa `mv` normal.

Advertencias y pasos siguientes:
- Después de mover, habrá que actualizar imports de Python y rutas en `Dockerfile` u otros scripts.
- Revisa `git status` y prueba arrancar el backend desde `backend/` antes de continuar con la migración a React.

Cómo ejecutar:

bash scripts/restructure_move.sh

Si quieres, puedo ejecutar el script ahora y aplicar los cambios directamente en el workspace.
