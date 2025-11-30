## DESPLIEGUE NORMAL

Para desplegar dockerlabs en producción con apache, estos son los permisos necesarios:

```bash
sudo chown -R www-data:www-data /var/www/dockerlabs
sudo find /var/www/dockerlabs -type d -exec chmod 755 {} \;
sudo find /var/www/dockerlabs -type f -exec chmod 644 {} \;
sudo chmod 775 /var/www/dockerlabs
sudo chmod 664 /var/www/dockerlabs/bunkerlabs.db
sudo chmod 664 /var/www/dockerlabs/dockerlabs.db
```

Y por otra parte para el tema del rate limit, tenemos que tener memcached activado:

```bash
sudo apt install memcached
sudo systemctl enable memcached
sudo systemctl start memcached
```

Si queremos auditar dockerlabs en local con un usuario que tenga rol de admin, debemos añadir en el app.py el siguiente endpoint y después visitar dicha ruta:

```python
@app.route('/make-me-admin')
def make_me_admin():
    user_id = session.get('user_id')
    if not user_id:
        return "Debes iniciar sesión para convertirte en admin.", 401
    db = get_db()
    db.execute(
        "UPDATE users SET role = 'admin' WHERE id = ?",
        (user_id,)
    )
    db.commit()

    return "Ahora eres admin."
```

# DESPLIEGUE EN DOCKER

Para construir una imagen de docker y lanzar la aplicación, ejecutaremos los siguientes comandos:

```bash
docker build -t dockerlabs .
docker run -d -p 5000:5000 --name dockerlabs dockerlabs
```

