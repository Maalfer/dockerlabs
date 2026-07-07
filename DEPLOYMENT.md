# Despliegue — el VPS es la FUENTE DE VERDAD

> **Desde 2026-06-16 se ABANDONÓ el push-deploy (GitHub Actions).**
> El código que corre en producción vive y se edita **directamente en este VPS**
> (`/var/www/dockerlabs/`). GitHub `main` está desactualizado (último commit
> 2026-05-27, ~61 ficheros divergidos) y **NO** debe usarse para desplegar.

## Cómo desplegar un cambio
1. Edita los ficheros directamente en `/var/www/dockerlabs/` en el VPS.
2. Reinicia el servicio:
   ```bash
   sudo systemctl restart dockerlabs
   ```
3. Verifica:
   ```bash
   systemctl is-active dockerlabs
   curl -s -o /dev/null -w '%{http_code}\n' https://dockerlabs.es/
   sudo journalctl -u dockerlabs -n 30 --no-pager   # revisar errores
   ```

## Qué se desactivó (2026-06-16)
- Eliminada la clave SSH `github-actions-deploy` de `~/.ssh/authorized_keys`
  (backup: `~/.ssh/authorized_keys.bak.20260616`). El workflow de GitHub ya no
  puede conectarse al VPS → no puede ejecutar `git pull` ni reiniciar nada.
- Workflow local renombrado a `.github/workflows/deploy.yml.disabled`.

## Pendiente (requiere acceso a GitHub — hazlo tú)
- Desactiva el workflow **"Deploy to VPS"** en GitHub para que no salten runs
  fallidos: pestaña *Actions* → *Deploy to VPS* → *⋯* → *Disable workflow*
  (o `gh workflow disable "Deploy to VPS" -R Maalfer/dockerlabs`).

## Backups (el VPS es el único origen del código)
- Código: snapshot en `/home/debian/` (`dockerlabs_code_snapshot_*.tgz`, sin venv/.git).
- BD: `mysqldump -u dockerlabs -p dockerlabs > backup.sql`.
- Recomendado: programar un snapshot periódico de código + BD.
