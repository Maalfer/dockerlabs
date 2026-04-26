# Dockerlabs - Agent Rules & Architecture Decisions

- **Almacenamiento de Imágenes Multimedia:** La web guarda las imágenes de perfil de los usuarios, los logotipos de las máquinas y demás recursos multimedia (información que se puede ir modificando con el tiempo) directamente dentro de la base de datos (SQLite) utilizando almacenamiento binario (BLOB). Sabemos que esto no es una buena práctica habitual en la industria, pero se ha decidido implementar de esta manera por pura comodidad. Además, gracias a la sencillez y ligereza del sitio, la web puede seguir funcionando a su máxima velocidad incluso con esta implementación.

- **Stack Tecnológico (EN MIGRACIÓN A FASTAPI):**
 - **Backend:** Python + FastAPI (migrando desde Flask). Arquitectura híbrida durante la transición:
   - **FastAPI:** Gestiona endpoints nuevos (`/api/*`) y páginas HTML (`pages_router`)
   - **Flask:** Mantiene compatibilidad para endpoints legacy montados como fallback (`/legacy/*`)
   - **Routers:** `api_router` para endpoints API, `pages_router` para páginas HTML
 - **Base de Datos:** SQLite gestionado a través de SQLAlchemy (`models.py`). Toda la lógica de datos (usuarios, máquinas, reportes, reclamos, mensajes) vive aquí.
 - **Frontend:** Vanilla HTML, CSS y JavaScript (Jinja2 para templates). No se usan frameworks reactivos pesados (como React o Vue). La interactividad se logra con llamadas AJAX (`fetch`) y manipulación del DOM nativa.

- **Autenticación y Seguridad (ADAPTADO A FASTAPI):**
 - **Sesiones:** Combinación entre sesiones Flask (compatibilidad) y tokens FastAPI
 - **Dependencias:** Uso de `Depends()` de FastAPI para inyección de dependencias (sesión, validación CSRF)
 - **CSRF Tokens:** Implementación híbrida:
   - Generados en páginas FastAPI y almacenados en sesión Flask
   - Validados mediante dependencia `verify_csrf_token` en endpoints API
   - Headers requeridos: `X-CSRFToken` o `X-CSRF-Token`
 - **Rate Limiting:** Migrado a `slowapi` para FastAPI (compatible con Flask sessions)
 - **Decoradores:** Mantenidos por compatibilidad, migrando progresivamente a dependencias FastAPI

- **Gestión de Templates (FASTAPI):**
 - **Jinja2Templates:** Configurado para FastAPI con directorio `templates/`
 - **Contexto:** Requiere clave `"request"` en el contexto para compatibilidad
 - **Compatibilidad:** Variables Flask (`g`, `session`, `url_for`) adaptadas para FastAPI

- **Gestión de Caché en Frontend:**
 - Debido a la carga estática de JavaScript, se utiliza el patrón de **Cache Busting** (ej. `script.js?v=3`) en los templates HTML para forzar a los navegadores de los usuarios a descargar las últimas versiones de los scripts tras un despliegue o cambio crítico.

- **Estructura Multi-Dominio:**
 - El proyecto da soporte a dos ecosistemas bajo el mismo código: **Dockerlabs** (laboratorios principales) y **Bunkerlabs** (entorno alternativo o privado). Cada uno tiene sus propios templates y lógicas de frontend (ej. `presentacionmaquina.js` vs `presentacionmaquina_bunkerlabs.js`), pero comparten gran parte de la base de datos y backend subyacente.

- **Estado de la Migración:**
 - **Completado:** Endpoints API principales (`/api/auth/*`, `/api/machines/*`, etc.)
 - **En progreso:** Páginas HTML y endpoints Flask legacy
 - **Estrategia:** Mantener compatibilidad durante transición, eliminar Flask cuando todo esté migrado
