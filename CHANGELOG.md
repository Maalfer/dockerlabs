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

## [Sin publicar]

## [2.1.0] - 2026-11-05

### Added

- **Cody**, la ballena hacker de DockerLabs (SVG animado, sin dependencias):
  acompaña login, registro y recuperación de contraseña; sigue el cursor, se
  tapa el ojo al escribir la contraseña, teclea en su portátil y suelta un
  chorro binario. Bocadillo de terminal con ~40 frases motivacionales.
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

### Changed

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

### Fixed

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
