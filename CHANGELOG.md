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
