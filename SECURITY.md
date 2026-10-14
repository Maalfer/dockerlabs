# 🛡️ Programa de Divulgación de Vulnerabilidades

DockerLabs dispone de un Programa de Divulgación de Vulnerabilidades (VDP) a través de la plataforma [Secur0](https://secur0.com/).

Invitamos a investigadores de seguridad y a la comunidad a participar de forma responsable, ayudando a identificar y reportar posibles vulnerabilidades en nuestros sistemas.

Para comenzar, revisa las directrices del programa y envía tus hallazgos a través de la plataforma oficial:

👉 https://app.secur0.com/programs/vdp/Dockerlabs

Tu colaboración es clave para reforzar la seguridad de DockerLabs. 🛠️🐳

## Versiones soportadas

DockerLabs sigue [Versionado Semántico](https://semver.org/lang/es/)
(`MAJOR.MINOR.PATCH`) a partir de la `v2.0.0`. Solo la última versión
publicada (ver [tags](https://github.com/Maalfer/dockerlabs/tags) y
[CHANGELOG.md](CHANGELOG.md)) recibe parches de seguridad, ya que DockerLabs
se despliega como servicio único en https://dockerlabs.es y no se mantienen
ramas de versiones antiguas en producción.

| Versión | Soportada |
| --- | --- |
| 2.x.x | ✅ |
| < 2.0.0 (sin versionar) | ❌ |

## CVE e identificación de vulnerabilidades

Al estar ya versionado, cada corrección de seguridad queda referenciada a un
rango de versiones afectadas y a la versión en la que se corrige (ver
`CHANGELOG.md`). Para vulnerabilidades con impacto suficiente, DockerLabs
podrá solicitar un identificador **CVE** a través del programa **GitHub
Security Advisories** (GitHub actúa como CNA — *CVE Numbering Authority* —
para repositorios públicos de GitHub):

1. El hallazgo se reporta primero de forma privada vía Secur0 (arriba) o
   mediante un [GitHub Security Advisory](https://github.com/Maalfer/dockerlabs/security/advisories/new)
   del propio repositorio.
2. Tras confirmar y corregir la vulnerabilidad, se publica un advisory
   indicando versiones afectadas (`< X.Y.Z`) y versión corregida (`X.Y.Z`).
3. Si corresponde, se solicita el CVE desde el propio advisory de GitHub.
4. El advisory y el CVE (si se emite) se referencian en `CHANGELOG.md` junto
   a la entrada de la versión que incluye el parche.

Por favor, **no** abras un issue público para reportar una vulnerabilidad:
usa siempre uno de los canales privados anteriores.
