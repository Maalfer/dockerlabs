# Changelog

Todos los cambios notables de DockerLabs se documentan en este fichero.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/)
y el proyecto usa [Versionado Semántico](https://semver.org/lang/es/)
(`MAJOR.MINOR.PATCH`):

- **MAJOR**: cambios incompatibles en la API pública (ver `API_PUBLICA.md`)
  o en el comportamiento de autenticación/sesión.
- **MINOR**: nuevas funcionalidades compatibles con versiones anteriores.
- **PATCH**: correcciones de bugs y de seguridad compatibles con versiones
  anteriores.

Las entradas de seguridad referencian su identificador de advisory
(GHSA/CVE) cuando aplica — ver `SECURITY.md`.

> **Nota:** aquí «publicar» significa asignar un número de versión, no
> desplegar. El código se edita y se aplica directamente en producción (ver
> `DEPLOYMENT.md`), así que lo que corre en https://dockerlabs.es puede ir
> por delante de la última versión en `VERSION`/`CHANGELOG.md`. «Sin
> publicar» agrupa los cambios que ya están en producción pero todavía no
> tienen versión asignada.

## [Sin publicar]

### Added

- **Herramientas de Comunidad** (`/herramientas-comunidad`): nueva página enlazada desde el
  menú principal con proyectos no oficiales de la comunidad para automatizar el uso de
  DockerLabs. Primera herramienta listada: DockerLabs CLI
  (`https://github.com/luigi70289/Dockerlabs-CLI`).
- **Writeups publicados** (`/writeups-publicados`) rehecha: resumen, buscador, filtros por
  dificultad y formato, orden, tarjetas con dificultad y recuento por tipo, ventana accesible
  con los writeups de cada máquina y enlace directo `?maquina=`. La API
  `/api/writeups_subidos/maquinas` añade `dificultad`, `videos`, `textos` y `ultimo`.
- **Cody en más páginas**: writeups publicados, agradecimientos, términos del material, máquinas
  completadas, máquinas enviadas, writeups recibidos, perfil público, errores 404/403 y las
  páginas de restablecer contraseña y verificar correo.
- **Autoría y antisuplantación**: página `/autoria` (autor, único dominio oficial, canales
  oficiales, cómo verificar y cómo avisar de una copia), enlazada desde las Condiciones de Uso.
  Aviso de independencia respecto a Docker, Inc. y cláusula de uso del nombre, el
  logotipo y Cody en las Condiciones de Uso (§7). `/.well-known/security.txt`. Metadatos de
  autor (meta, `rel=author`, JSON-LD). Cabecera de autoría en `auto_deploy.sh`. `AUTORIA.md`.
- Registro: nombres de usuario reservados ampliados (equipo, soporte, marca, autor), comparados
  sin separadores ni sustituciones tipo `4dm1n` (`validators.es_nombre_reservado`).
- **Gestión de usuarios** (`/gestion-usuarios`): orden por últimos registros, más antiguos,
  último acceso, más tiempo sin entrar o nombre; filtros por rol, fecha de registro y último
  acceso; columnas ordenables, 10-100 por página y resumen. Nueva columna
  `users.last_seen_at` (último acceso), que mantiene `get_session()` con una escritura como
  mucho cada 10 minutos por usuario. Requiere `ALTER TABLE users ADD COLUMN last_seen_at
  DATETIME NULL, ADD INDEX idx_users_last_seen_at (last_seen_at)` en instalaciones existentes.
- **Gestión de BunkerLabs** (`/bunkerlabs/gestion`) rehecha: resumen de uso, buscador y
  filtro, contraseña y enlace directo copiables, generador de contraseñas, uso de cada
  acceso (entradas, personas y última entrada) e interruptor para activar o desactivar un
  acceso sin borrarlo (`POST /bunkerlabs/gestion/{id}/toggle`). En móvil cada acceso es una ficha.
- **Cola de revisión de máquinas** (`/pending-machines`) rehecha: pestañas por
  estado con contadores (pendientes, añadidas, rechazadas, todas), buscador,
  orden y paginación (12 por página). Marcar una máquina como añadida o
  rechazarla la saca de la cola y la archiva (con «Deshacer»); el archivo se
  puede limpiar entero o solo lo revisado hace más de 30 días. Avisa si un envío
  ya está publicado, si se ha enviado más de una vez o si lleva 14 días o más
  esperando. Nuevos endpoints `POST /api/admin/pending-machines/{id}/estado` y
  `POST /api/admin/pending-machines/limpiar`.
- Al publicar una máquina desde `/add-maquina`, los envíos pendientes con ese
  mismo nombre pasan solos a «añadida». El botón «Publicar» de la cola abre el
  formulario con nombre, descripción y enlace ya rellenos.
- **Cody**, la ballena hacker de DockerLabs (SVG animado, sin dependencias):
  acompaña login, registro y recuperación de contraseña; sigue el cursor, se
  tapa el ojo al escribir la contraseña, teclea en su portátil y suelta un
  chorro binario. Bocadillo de terminal con ~40 frases motivacionales.
- Cody: repertorio ampliado a ~220 frases y citas en `frases.json`, con categorías,
  frases según la página (contraseñas en login, felicitaciones en certificados…),
  sin repetir entre páginas y firmadas como «Cody - <año>».
- Cody en las páginas legales (modo lectura): resume cada sección mientras
  lees y muestra el porcentaje leído.
- Guía de ayuda para quien empieza (botón `?` junto al filtro de dificultad):
  8 pasos con Cody y capturas ampliables; el último aplica el filtro
  «Muy fácil».
- Sistema visual común (`dl-sistema.css`): botones `.dl-btn` y sus variantes,
  con la regla de color de la web (ámbar → verde hacker).
- Footer móvil compartido por DockerLabs y BunkerLabs (`dl-footer.css`).
- Tests: el nonce de cada script coincide con la cabecera CSP; toda
  referencia de una plantilla a otro fichero existe.
- **Gestión de usuarios** (`/gestion-usuarios`): un admin puede asignar una
  contraseña nueva a cualquier usuario o enviarle el email de
  restablecimiento desde un modal en la propia fila (`POST
  /api/admin/set_user_password/{id}`, `POST
  /api/admin/send_password_reset/{id}`).

### Changed

- **Categoría de plataforma de las máquinas**: sustituye Linux/Windows/Móvil
  por **Docker**/**VirtualBox**, que es la distinción que importa (cómo se
  despliega, no el sistema operativo invitado). Afecta al filtro de la home,
  al selector de `/add-maquina` y al de `/gestion-maquinas`; la página de
  descarga usa ahora `sistema_operativo == 'virtualbox'` para decidir si
  muestra las instrucciones de importación en VirtualBox o las de
  `auto_deploy.sh`. Las instrucciones y capturas de VirtualBox se rehacen con
  el flujo real en Windows: extraer el `.zip`, abrir el `.ova` con
  **VirtualBox Manager**, entrar en **Configuración** y poner la red en
  **Adaptador puente** antes de iniciar la máquina.
- **Cody: chorro de agua real** en login, registro y recuperar contraseña, y en las páginas con Cody en modo lectura: en lugar del chorro binario, del espiráculo sale un surtidor que se abre en abanico con niebla luminosa, gotas que suben y caen, destellos y un guiño de bits verdes. Brota de vez en cuando (cada 9-18 s) y al hacerle clic; respeta `prefers-reduced-motion`.
- Header de DockerLabs: el logotipo PNG se sustituye por **Cody** (SVG en línea,
  `_cody_logo.html`): parpadea de vez en cuando y saluda al pasar el cursor. El PNG sigue
  en favicon, PWA y tarjetas sociales. Misma pose que el logotipo original (sale del agua
  en diagonal) y también en el header de BunkerLabs; estilos en `cody-logo.css`.
- **BunkerLabs: el PIN es una llave, no una identidad.** La sesión guarda solo el tipo de
  acceso (`bunkerlabs_ok`, `bunkerlabs_guest`, `bunkerlabs_id`); el nombre que se muestra
  arriba a la derecha se calcula en cada página con la sesión de DockerLabs (usuario,
  «Anónimo» o «Invitado») y ya nunca es la etiqueta del PIN ni un nombre heredado. Desactivar
  o borrar un PIN retira el acceso a quien entró con él; un invitado puede pasar a acceso
  completo introduciendo un PIN sin tener que salir antes; el historial anota el usuario de
  DockerLabs o «Anónimo». Dejan de usarse `bunkerlabs_nombre`, `bunkerlabs_anonymous` y
  `bunkerlabs_unauthenticated`.
- **Una sola página para creadores**: `/enviar-maquina` («Crear y enviar una máquina») reúne
  los pasos, las reglas y el vídeo de la antigua `/como-se-crea-una-maquina` (que ahora
  redirige con 301) con los requisitos y el formulario de envío. Se retira el bloque
  «Proceso de envío». Menú, sitemap y enlaces internos actualizados.
- Gestión de usuarios: nombres y correos ya no aparecen censurados; `?page=` no numérico
  ya no provoca un 500.
- **Acceso a BunkerLabs (`/bunkerlabs/login`) minimalista y con Cody**: una sola tarjeta centrada en lugar de
  los dos paneles con degradados; las formaciones con acceso (La Academia y el Máster en Hacking Ético) quedan siempre visibles como enlaces
  discretos bajo el formulario. Cody
  explica qué es BunkerLabs, explica en mensajes separados (laboratorios basados en vulnerabilidades reales; recreación de las más críticas y de
  mayor impacto; entornos realistas), reacciona al foco de la contraseña y, si el servidor rechaza la
  contraseña, explica qué hacer (modo «guía» de `ballena.js` + `bunkerlabs/js/login.js`). Accesibilidad 100.
- Clics del login de BunkerLabs hacia La Academia (`/go/academia-bunker`, aterriza en `#cursos`) y el Máster (`/go/master`),
  con origen `bunker-login` y UTM propia (atribución en MailerUp); `/estadisticas` añade la serie «Máster». Se corrige el
  enlace antiguo a La Academia, que devolvía 404.
- **Ayuda en las clasificaciones**: icono «?» junto al título de «Clasificación» (writeups) y «Clasificación
  Autores». Explica los puntos reales (writeup: +1/+2/+3/+4 según la dificultad; máquina publicada en DockerLabs:
  +1), los pasos para subir puestos (subir writeup, «Enviar máquina») y calcula con los datos del propio ranking
  el puesto del usuario y a cuál subiría. Los dos modales pasan a ser diálogos accesibles (rol, Esc, foco).
- **Gestión de máquinas (`/gestion-maquinas`) rediseñada** (accesibilidad, rendimiento y móvil):
  Lighthouse de accesibilidad 76 → 100; HTML 306 → 126 kB, DOM 2.436 → 1.315 nodos, 80 formularios → 4;
  todos los controles con nombre accesible, logo subible con teclado, diálogos nativos `<dialog>`, avisos
  anunciados a lectores de pantalla y botón de eliminar solo para admin/moderador. Cada plataforma es una
  vista propia (`?plataforma=docker|bunker`) con búsqueda real (sin recarga al teclear), filtro de dificultad
  (`?dificultad=`) y paginación con ventana; `page` y `per_page` se acotan y `%`/`_` de la búsqueda son literales.
  En móvil/tablet cada máquina es una tarjeta (−29 % de alto) con objetivos táctiles de 44 px.
- Logos de máquina: `/img/maquina/<id>?s=96&v=<fichero>` sirve una miniatura WebP cacheada en
  `uploads/logos/thumbs/` con caché de un año (816 kB → ~20 kB en 20 logos). Sin `v` se mantiene `no-cache`.
- Pie de página (todas las páginas): los enlaces a GitHub, LinkedIn, Telegram y Discord tienen `aria-label`.
- Botones principales de login, registro, descargas, envío de máquinas,
  soporte, dashboard y gestión de usuarios con el mismo estilo que el header.
- Foco de formularios y paginación unificados en ámbar.
- Móvil: buscador y filtros de la home en la misma fila (de 6 a 3 filas);
  nombres de máquina alineados; el nombre «DockerLabs» vuelve al header;
  header de BunkerLabs con las mismas medidas que el de DockerLabs.
- Móvil: dashboard, estadísticas, certificados, gestión de usuarios y perfil
  público ya no desbordan la pantalla (tablas convertidas en tarjetas).
- Ritmo vertical común: menos hueco entre el header y el contenido.
- Páginas informativas y legales movidas de `pages_admin.py` a
  `routes/pages_info.py`.
- `tools/backfill_certificados.py` (antes en la raíz) usa rutas relativas.
- Página de **agradecimientos** (`/agradecimientos`) rediseñada con el lenguaje
  visual de `/equipo`: cabecera de terminal, secciones «Personas» y
  «Comunidades», tarjetas con avatar y enlace, y bloque final para colaborar.
  Estilos propios en `static/dockerlabs/css/info/agradecimientos.css`. Se retira
  una de las comunidades que figuraban en la página y se añade **VulNyx**
  (`https://vulnyx.com/machines/`) junto a HackMyVM, con su logotipo alojado en
  local.

### Removed

- Página `/instrucciones-uso` y su entrada en el menú: la guía de ayuda del inicio (botón `?`)
  cubre el despliegue. La URL antigua redirige (301) al inicio.
- Tokens de API de administrador: la sección «Tokens de API» del dashboard,
  los endpoints `/api/admin/tokens` (crear, listar y revocar) y la
  autenticación por cabecera (`Authorization: Bearer` / `X-Admin-Token`) que
  equivalía a una sesión de admin. Ahora la única forma de autenticarse es la
  cookie de sesión. Todos los tokens existentes ya estaban revocados. La
  tabla `api_tokens` queda en la BD sin uso (no se borra automáticamente).

### Fixed

- BunkerLabs: eliminar un acceso con historial de entradas devolvía un error 500 (la clave
  foránea de `bunker_access_logs` impedía el borrado); ahora se borra junto con su historial.
- BunkerLabs: el historial de un acceso salía siempre vacío y «Limpiar historial» llamaba a
  una ruta inexistente; los nombres del historial ya no se insertan como HTML.
- Las instrucciones de descarga muestran el nombre real del fichero de la
  máquina en el comando `auto_deploy.sh` en vez de un placeholder genérico
  (idea original de [@ateto3](https://github.com/ateto3) en el PR #26).
- Nonce CSP: ~35 rutas pasaban un nonce propio y las bases usaban una
  variable inexistente, así que ningún script en línea casaba con la
  política. Ahora lo inyecta un context processor en todas las plantillas.
- En móvil, el título del header vuelve a llevar de DockerLabs a BunkerLabs
  y viceversa, como en escritorio.
- HTML inválido (enlaces anidados) en el header de BunkerLabs.
- Los errores 500 inesperados ya se registran en el log
  (`logger.exception`) en lugar de perderse.
- Eliminados los avisos de APIs obsoletas (`datetime.utcnow`,
  `Query.get`): de 1.057 a 1 en el suite de tests.
- Writeups recibidos (`/writeups-recibidos`): en escritorio, Cody ocupaba una
  columna lateral fija que dejaba la tabla sin ancho suficiente, obligando a
  desplazarla para ver la columna de enlaces; ahora se muestra en la misma
  barra compacta que ya usaba en tablet/móvil.

## [2.0.1] - 2026-10-22

### Fixed

- `/go/{destino}` (botones salientes Newsletter/Academia) ya valida el
  parámetro `o` contra una lista cerrada de ubicaciones conocidas
  (`footer`, `home-boton`); cualquier otro valor se agrupa como `otro` en
  vez de crear una fila nueva en `/estadisticas`. Evita que escaneos
  automatizados de SQLi/XSS contra ese parámetro (sin impacto real, ya que
  el valor se guardaba parametrizado vía ORM) contaminen las estadísticas
  de clics con una entrada distinta por cada payload probado.

## [2.0.0] - 2026-10-14

Primera versión formalmente versionada de DockerLabs. A partir de aquí el
proyecto sigue SemVer y cada release queda etiquetada en git
(`vMAJOR.MINOR.PATCH`), lo que permite referenciar rangos de versiones
afectadas/corregidas en advisories de seguridad y solicitudes de CVE.

### Added

- Versión de la aplicación expuesta de tres formas: fichero `VERSION` en la
  raíz (fuente única de verdad), pie de página en todas las vistas y
  endpoint público `GET /api/version`.
- Soporte PWA: manifest, service worker, iconos y página offline.

### Changed

- Política de divulgación de vulnerabilidades (`SECURITY.md`) actualizada
  para reflejar el nuevo esquema de versiones y el proceso de solicitud de
  CVE vía GitHub Security Advisories.

[Sin publicar]: https://github.com/Maalfer/dockerlabs/compare/v2.0.1...HEAD
[2.0.1]: https://github.com/Maalfer/dockerlabs/compare/v2.0.0...v2.0.1
[2.0.0]: https://github.com/Maalfer/dockerlabs/releases/tag/v2.0.0
