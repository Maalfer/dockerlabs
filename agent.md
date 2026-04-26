# Dockerlabs - Agent Rules & Architecture Decisions

- **Almacenamiento de Imágenes Multimedia:** La web guarda las imágenes de perfil de los usuarios, los logotipos de las máquinas y demás recursos multimedia (información que se puede ir modificando con el tiempo) directamente dentro de la base de datos (SQLite) utilizando almacenamiento binario (BLOB). Sabemos que esto no es una buena práctica habitual en la industria, pero se ha decidido implementar de esta manera por pura comodidad. Además, gracias a la sencillez y ligereza del sitio, la web puede seguir funcionando a su máxima velocidad incluso con esta implementación.

- **Stack Tecnológico:**
  - **Backend:** Python + Flask. Arquitectura modular basada en Blueprints (`auth_bp`, `maquinas_bp`, `api_bp`, `writeups_bp`, `messaging_bp`).
  - **Base de Datos:** SQLite gestionado a través de SQLAlchemy (`models.py`). Toda la lógica de datos (usuarios, máquinas, reportes, reclamos, mensajes) vive aquí.
  - **Frontend:** Vanilla HTML, CSS y JavaScript (Jinja2 para templates). No se usan frameworks reactivos pesados (como React o Vue). La interactividad se logra con llamadas AJAX (`fetch`) y manipulación del DOM nativa.

- **Autenticación y Seguridad:**
  - Gestión de sesiones combinada con `flask_login` y JWT/Tokens propios.
  - Uso intensivo de decoradores personalizados (`@role_required`, `@csrf_protect`) para proteger endpoints sensibles.
  - **CSRF Tokens:** Se generan y validan manualmente en formularios y llamadas AJAX mediante el header `X-CSRFToken` o `FormData`.
  - **Rate Limiting:** Implementado con `flask_limiter` para evitar abusos (fuerza bruta, spam de reportes o de peticiones a la API).

- **Gestión de Caché en Frontend:**
  - Debido a la carga estática de JavaScript, se utiliza el patrón de **Cache Busting** (ej. `script.js?v=3`) en los templates HTML para forzar a los navegadores de los usuarios a descargar las últimas versiones de los scripts tras un despliegue o cambio crítico.

- **Estructura Multi-Dominio:**
  - El proyecto da soporte a dos ecosistemas bajo el mismo código: **Dockerlabs** (laboratorios principales) y **Bunkerlabs** (entorno alternativo o privado). Cada uno tiene sus propios templates y lógicas de frontend (ej. `presentacionmaquina.js` vs `presentacionmaquina_bunkerlabs.js`), pero comparten gran parte de la base de datos y backend subyacente.
