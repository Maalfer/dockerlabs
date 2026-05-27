# Database Directory

La aplicación usa **MariaDB/MySQL**. La conexión se configura mediante la
variable `DATABASE_URL` en el fichero `.env`, por ejemplo:

```
DATABASE_URL=mysql+pymysql://usuario:clave@127.0.0.1/dockerlabs?charset=utf8mb4
```

La base de datos `dockerlabs` usa la colación `utf8mb4_bin` (sensible a
mayúsculas, igual que el comportamiento original de SQLite; la aplicación
gestiona la insensibilidad a mayúsculas explícitamente con `func.lower()` e
`ilike`).

## Contenido (tablas)

- Datos de usuarios
- Datos de máquinas (dockerlabs y bunkerlabs)
- Writeups, valoraciones, rankings
- Tablas específicas de BunkerLabs (tokens de acceso, logs, writeups)

## Notas

- Esta carpeta se usaba antiguamente para el fichero SQLite `dockerlabs.db`.
  Tras la migración a MariaDB (2026-05) ya no se utiliza para la BD; solo
  conserva `almacenamiento/` (imágenes subidas), que se sirve en `/database/`.
- Backups de MariaDB: `mariadb-dump dockerlabs > backup.sql`.
