# API pública de DockerLabs — CONTRATO ESTABLE (no romper)

> ⚠️ **AVISO PARA CUALQUIER AGENTE O DESARROLLADOR**
>
> Los endpoints de este documento son una **API pública consumida por
> aplicaciones externas**. Su forma (rutas, nombres de campo, tipos y
> semántica) es un **contrato**. **No** renombres rutas ni campos, **no**
> cambies tipos, **no** elimines claves y **no** alteres el formato de fechas
> ni de las URLs. Añadir campos nuevos es aceptable; cambiar o quitar los
> existentes **rompe a los consumidores** y está prohibido salvo versionado
> explícito (`/api/v2/...`).
>
> Si necesitas cambiar algo, crea una ruta nueva versionada y mantén la vieja.

Todos estos endpoints son **públicos y sin autenticación** (`unauth`). Debe
seguir siendo así: son de solo lectura y no exponen datos privados (nunca
`email`, `password_hash`, teléfonos ni datos de tutores).

## Solo DockerLabs — BunkerLabs queda fuera

BunkerLabs es de acceso cerrado y **no tiene certificados ni se expone aquí**.
El candado está en el código (`certificados.py: machine_certificable()` y
`CERT_ORIGENES = ('docker', 'empezar')`) **y** en el filtrado de
`public_profile.py`. No emitas diplomas ni publiques datos de máquinas cuyo
`origen == 'bunker'`.

---

## `GET /u/<slug>` — perfil público completo

`<slug>` es `User.slug` (o el `username` literal como alias). Responde `200`
con el JSON de abajo, o `404` `{"error": "...", "slug": "..."}` si no existe.
Cabecera `Cache-Control: public, max-age=60`.

Claves de primer nivel (todas deben existir siempre):

```
slug, username, perfil, progreso, estadisticas,
maquinas_hechas, maquinas_creadas, writeups, certificados
```

- **`perfil`**: `id, rol, biografia, miembro_desde, avatar_url, perfil_url,
  redes{linkedin, github, youtube}`. `avatar_url` = `/img/perfil/<id>`.
- **`progreso`** (sobre el catálogo `docker`): `catalogo, maquinas_totales,
  maquinas_hechas, porcentaje` (float 0–100) y `por_dificultad` = mapa
  `"<Dificultad>" -> {hechas, totales}`. Agrupado por `Machine.clase`
  normalizada; NO por `Machine.dificultad` (esta está sin normalizar: conviven
  'Fácil' y 'Facil').
- **`estadisticas`**: contadores `maquinas_hechas, maquinas_creadas,
  writeups_publicados, certificados_disponibles, certificados_generados,
  puntos_writeups, ranking_writeups, ranking_creadores`.
- **`maquinas_hechas[]`**: ficha de máquina + `completada_el`, `writeup_url`
  (o null), `certificado` (objeto o null). Campos de ficha: `id, nombre,
  dificultad, clase, color, origen, categoria, logo_url` y, si la máquina es de
  DockerLabs, también `autor, enlace_autor, fecha, descripcion, descarga`. De
  máquinas de BunkerLabs solo aparecen los campos básicos (nunca `descripcion`
  ni `descarga`).
- **`maquinas_creadas[]`**: misma ficha de máquina (solo orígenes públicos).
- **`writeups[]`**: `maquina, url, tipo, publicado_el, logo_url`. Sin BunkerLabs.
- **`certificados[]`**: `cert_id, maquina, dificultad, logo_url, generado
  (bool), emitido_el, pdf_url, imagen_url, verify_url`. Sin BunkerLabs.

`logo_url` de cualquier máquina = `/img/maquina/<id>` (público). `*_el` y fechas
ISO usan sufijo `Z`.

## `GET /api/certificado/pdf/<CERT_ID>` — diploma en PDF

`<CERT_ID>` con formato `DL-XXXXXX` (6 hex mayúsculas). `200 application/pdf`
del diploma archivado, o `404`. Público, `Cache-Control: 86400`.

## `GET /api/certificado/imagen/<CERT_ID>` — diploma en imagen

`200 image/webp` del diploma, `inline`. Mismo formato de ID y errores.

## `GET /api/certificado/verificar/<CERT_ID>` — verificación

`200 application/json`. Si es válido:
`{valid: true, username, machine, dificultad, generado: true, pdf_url,
imagen_url}`. Si no: `{valid: false, message}`. Es O(1) (consulta indexada);
no reintroduzcas escaneos de tabla aquí.

## `GET /img/maquina/<id>` y `GET /img/perfil/<id>` — imágenes públicas

Sirven logo de máquina y avatar. Son las URLs que devuelven los JSON de arriba;
deben seguir siendo públicas. Responden con CSP `sandbox` en vigor (mitiga SVG).

---

## Invariantes que sostienen este contrato (no romper)

1. **`cert_id` es ÚNICO** en la tabla `certificados` y estable en el tiempo. Se
   asigna con `allocate_cert_id()`, que preserva los IDs ya emitidos. Para leer
   el ID definitivo usa `Certificate.cert_id`, nunca recalcules con
   `certificate_id()` (es solo el primer candidato del hash).
2. **El PDF y la imagen se archivan al publicar el writeup** (no al pedirlos),
   así que `pdf_url`/`imagen_url` de un certificado `generado: true` siempre
   resuelven.
3. **BunkerLabs nunca aparece** ni genera certificados (ver arriba).
4. Estos endpoints **no requieren sesión**. No añadas autenticación.
