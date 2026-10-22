# Suite de tests de DockerLabs

Suite de 610 tests (pytest) contra el `fastapi_app` real de `asgi.py` y una
MariaDB de verdad (vía Docker Compose), construida para reemplazar los 5
tests muertos de la era Flask que había antes. Sin SQLite ni mocks del ORM:
los tests de `tests/integration/` golpean la app de punta a punta (incluidos
todos los middlewares — CSRF, rate limiting, cabeceras de seguridad) y los de
`tests/unit/` cubren funciones puras sin BD ni red.

## Arrancar y correr

```bash
# 1. Entorno (una sola vez)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -r tests/requirements-test.txt

# 2. Correr el suite (levanta la MariaDB de test sola si hace falta)
pytest tests/ -v

# También funciona sin paso previo: conftest.py detecta si el contenedor
# de test no está arriba y lo levanta con:
#   docker compose -f docker-compose.yml -f tests/docker-compose.test.yml up -d db
```

No hace falta `DATABASE_URL` en el entorno: `conftest.py` la fija sola,
apuntando a un esquema `dockerlabs_test` dedicado en el contenedor de test
(puerto `3307`, para no chocar con una MariaDB de producción que pudiera
correr en el `5432`/`3306` por defecto de la máquina).

## Tirar abajo la BD de test

El contenedor **no se para solo** al acabar pytest (se reutiliza entre
ejecuciones, para no pagar el coste de arranque en cada run). Para tirarlo
abajo y borrar sus datos:

```bash
docker compose -f docker-compose.yml -f tests/docker-compose.test.yml down -v
```

## Estructura

```
tests/
  conftest.py       # fixtures raíz: BD de test, truncado entre tests, TestClient,
                     # mocks de red (SMTP/Discord), login_as, admin_api_token
  factories.py       # make_user/make_machine/make_writeup/... con defaults sensatos
  unit/              # sin BD, sin red — funciones puras (validators, slugs, image_utils...)
  integration/        # contra TestClient + MariaDB real, un fichero por familia de rutas
```

## Aislamiento entre tests

Cada test corre con la BD completamente vacía: una fixture `autouse` hace
`TRUNCATE` de todas las tablas al terminar cada test. No se usa rollback de
transacción porque la app hace commits reales dentro de los endpoints.

**Gotcha importante (REPEATABLE READ):** una petición vía `client.post(...)`
corre en una sesión/transacción de SQLAlchemy *distinta* a la que usa el
propio test (`db` fixture) — así está montada la app (`scoped_session` por
request, ver `dockerlabs/database.py`). Bajo REPEATABLE READ (modo por
defecto de MariaDB/InnoDB), si la sesión del test ya tenía una transacción
abierta seguiría viendo el estado de ANTES del commit ajeno. Por eso, tras
cualquier `client.post/delete/...` que mute datos, los tests hacen
`db.session.rollback()` antes de volver a consultar — cierra esa transacción
y abre una nueva que sí ve el commit.

**Gotcha relacionado (identity map):** si un test creó una fila con
`make_user(db, ...)` y luego la borra vía endpoint, **no** se debe volver a
tocar `objeto.algun_campo` ni usar `Modelo.query.get(objeto.id)` para
comprobar que ya no existe — el objeto Python sigue en el identity map de la
sesión del test y SQLAlchemy intentará refrescarlo, lanzando
`ObjectDeletedError` en vez de devolver `None`. El patrón correcto: guardar
el id en una variable simple ANTES del borrado (`obj_id = obj.id`) y
consultar con `Modelo.query.filter_by(id=obj_id).first() is None` (una
`filter_by` no consulta el identity map, hace un SELECT limpio).

## Mocks de red

Por defecto, **ningún** test puede abrir un socket SMTP real ni llamar al
webhook real de Discord (fixture `autouse`, falla fuerte si algo lo intenta
sin querer). Los tests que sí quieren comprobar "se envió el correo/mensaje"
usan las fixtures `mock_smtp` / `mock_discord`, que devuelven la lista de
envíos registrados.

## Concurrencia: NO correr varios `pytest` en paralelo contra la misma BD

La estrategia de aislamiento (TRUNCATE global tras cada test) asume **un
único proceso de pytest** usando la BD de test a la vez. Si se lanzan varios
`pytest` concurrentes (p. ej. varios agentes/CI en paralelo) contra el mismo
contenedor, un TRUNCATE de un proceso puede quedar bloqueado esperando el
lock de metadatos de tabla de una transacción abierta en otro proceso
("Waiting for table metadata lock"), y el suite se cuelga o falla en
cascada. Si de verdad hace falta paralelismo, usar esquemas (`TEST_DB_NAME`)
o contenedores distintos por proceso — no el mismo `dockerlabs_test`.

## Hallazgos documentados (no corregidos a propósito)

El objetivo de este suite era *fijar el comportamiento actual con tests*, no
arreglar bugs nuevos. Lo siguiente quedó documentado con comentarios `NOTA`/
`HALLAZGO` en el test correspondiente, pinnando el comportamiento real para
que el equipo decida si lo corrige:

- **`routes/certificados.py` — `GET /api/certificado/<maquina>?formato=pdf`
  rompe siempre con un `RuntimeError` (archivo inexistente).** `ensure_certificate()`
  ya no archiva un PDF físico (solo WebP; el PDF se compone al vuelo), pero
  esta rama sigue esperando un fichero que nunca se escribe. El endpoint
  público `GET /api/certificado/pdf/<cert_id>` (el que de verdad consumen
  terceros) no tiene este problema: compone el PDF al vuelo correctamente.
  **Esto afecta también a producción, no solo al clon de test** — candidato
  a arreglar aparte. Ver `test_certificados_api.py::test_formato_pdf_is_actually_broken_no_physical_pdf_archived`.
- **`routes/pending_admin.py`** — aprobar una `PendingMachineSubmission` solo
  cambia su `estado` a `"aprobado"`: no crea ninguna fila `Machine`/`Category`.
  Si no hay otro proceso que lo haga, "aprobar" no publica la máquina en el
  catálogo. Ver `test_pending_admin.py::test_approve_does_not_create_machine_or_category_row`.
- **`routes/writeups.py` — `POST /api/writeups/{id}/report`** es la única
  ruta de escritura de todo el fichero sin `Depends(verify_csrf_token)`: una
  sesión autenticada por cookie puede reportar un writeup sin CSRF token
  (impacto bajo: solo crea una fila `WriteupReport`). Ver
  `test_writeups.py::test_succeeds_without_csrf_header`.
- **`routes/writeups.py` — borrado batch de análisis** (`api_delete_writeups_batch`):
  un id no numérico en la lista dispara un `ValueError` sin manejo
  específico, capturado por un `except Exception` genérico que devuelve 500
  con el texto crudo de la excepción (fuga de detalle interno) y además
  aborta TODO el batch (nada se borra, ni los ids válidos). Ver
  `test_writeups_analisis.py::test_non_numeric_id_aborts_whole_batch_with_500`.
- **`routes/pages_admin.py` — `?page=<no numérico>`** en `/gestion-usuarios`
  no atrapa el `ValueError` de `int(...)`: un cliente real recibiría un 500
  en vez de un 400. Ver `test_pages_admin.py::test_non_numeric_page_param_crashes_with_500`.
- **`asgi.py` — rate limiter global** (`rate_limit_middleware`) usa
  `request.client.host` crudo: no respeta `X-Forwarded-For` ni
  `cf-connecting-ip`, a diferencia de `visit_counter_middleware` y de
  `/go/<destino>`. Detrás de un proxy/CDN que no reescriba la IP de origen
  real antes de Uvicorn, todo el tráfico compartiría la misma key. Ver
  `test_rate_limiting.py`.
- **`discord_notify.py` — `_hex_to_int(None, default)`** lanza
  `AttributeError` sin manejar (el `except` solo cubre `TypeError`/`ValueError`):
  si `machine.color` es `None`, `notify_new_machine` reventaría en vez de
  usar el color por defecto. Ver `test_discord_helpers.py::test_none_raises_attribute_error`.
- **`routes/writeups.py` — rutas duplicadas con semántica idéntica**:
  `POST /api/writeups/subidos/{id}/delete` vs `DELETE /api/writeups_subidos/{id}`
  (mismo patrón en `/recibidos/{id}/delete`). Comportamiento confirmado
  idéntico, no es un bug — queda como posible limpieza de superficie de API.

## Dependencias de test

Separadas de `requirements.txt` (el de producción) en
`tests/requirements-test.txt`: `pytest`, `pytest-cov`, `Faker`.
