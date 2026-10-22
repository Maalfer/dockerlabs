# Despliegue de la instancia de producción (dockerlabs.es)

> Esto describe cómo se despliega **la instancia oficial** en
> `/opt/dockerlabs` del VPS. Si quieres desplegar tu propia copia de
> DockerLabs en otro sitio, no necesitas nada de esto: usa **Docker
> Compose** (ver `README.md`), que es independiente de este proceso.

## Cómo se edita y publica un cambio

El código en producción se edita **directamente en el VPS**
(`/opt/dockerlabs/`), igual que entre 2026-06 y 2026-10. La diferencia es
que desde octubre de 2026 cada cambio también se sincroniza a un clon del
repo (`git@github.com:Maalfer/dockerlabs.git`) y se comitea/pushea, en vez
de quedarse solo en el VPS:

1. Edita los ficheros directamente en `/opt/dockerlabs/` en el VPS y
   reinicia el servicio para aplicar el cambio:
   ```bash
   sudo systemctl restart dockerlabs
   ```
2. Verifica:
   ```bash
   systemctl is-active dockerlabs
   curl -s -o /dev/null -w '%{http_code}\n' https://dockerlabs.es/
   sudo journalctl -u dockerlabs -n 30 --no-pager   # revisar errores
   ```
3. Para que el cambio quede también en git: copia los ficheros tocados a
   un clon aparte del repo (p. ej. `/root/dockerlabs-sync`), compara antes
   con `rsync -rtnc --delete` contra `/opt/dockerlabs` excluyendo
   `venv/ __pycache__/ .env *.bak* uploads/ *.sql` para no arrastrar nada
   que no toque, y comitea/pushea desde ahí.

No existe un pipeline de CI/CD que haga esto automáticamente: el workflow
`.github/workflows/deploy.yml.disabled` sigue desactivado (ver su
`README.txt`) porque apunta a la ruta vieja (`/var/www/dockerlabs`, del VPS
anterior) y no se ha adaptado al VPS ni al flujo actuales.

## Backups

No hay un backup automatizado de código ni de base de datos configurado
actualmente para esta instancia. Si necesitas uno puntual:

- Código: `tar` del directorio excluyendo `venv/` y `.git/`.
- BD: `mysqldump -u dockerlabs -p dockerlabs > backup.sql`.
