Workflow de push-deploy DESACTIVADO desde el 2026-06-16.

Actualizado 2026-10-22: el repo volvió a ser la fuente de verdad del
código (ver VERSION / CHANGELOG.md, tags v2.0.0+ en GitHub) — ya NO es
cierto que "el VPS sea la fuente de verdad" como decía esta nota antes.
Lo que sigue desactivado es solo el DESPLIEGUE automático: el código se
edita directo en el VPS (/opt/dockerlabs) y se sincroniza a mano a un
clon de este repo (rsync por checksum, excluyendo venv/__pycache__/.env/
*.bak*/uploads//*.sql) para comitear y pushear. Ver DEPLOYMENT.md.

Si se quiere reactivar este workflow en el futuro, renombrarlo a
deploy.yml, configurar los secrets VPS_HOST/VPS_USER/VPS_SSH_KEY en
GitHub, y corregir la ruta `/var/www/dockerlabs` del script (es la ruta
del VPS viejo; la actual es `/opt/dockerlabs`).
