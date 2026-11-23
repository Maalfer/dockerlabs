/* Gestión de máquinas (/gestion-maquinas).
   - Todo por delegación de eventos: el HTML no lleva manejadores inline.
   - Diálogos nativos <dialog>: foco atrapado, Esc y fondo inerte los gestiona el navegador.
   - Los avisos van a regiones aria-live para que los lectores de pantalla los anuncien.
   - La búsqueda es un formulario GET normal (ya no recarga la página al teclear). */
(() => {
    'use strict';

    const tabla = document.getElementById('gm-tabla');
    const origen = tabla ? tabla.dataset.origen : 'docker';
    const nombrePlataforma = origen === 'bunker' ? 'BunkerLabs' : 'DockerLabs';
    const MAX_LOGO = 2 * 1024 * 1024;           // mismo límite que el servidor
    const TIPOS_LOGO = /^image\//;

    let datos = {};
    try { datos = JSON.parse(document.getElementById('gm-datos')?.textContent || '{}'); } catch (e) { datos = {}; }

    const $ = (sel, raiz = document) => raiz.querySelector(sel);
    const csrf = () => (typeof getCsrfToken === 'function' ? getCsrfToken() : ($('meta[name="csrf-token"]')?.content || ''));
    const filaDe = (el) => el.closest('tr[data-id]');

    /* ───────────── Avisos accesibles ───────────── */
    function aviso(texto, tipo = 'ok') {
        const caja = $(tipo === 'error' ? '#gm-avisos-err' : '#gm-avisos');
        if (!caja) return;
        const el = document.createElement('div');
        el.className = `gm-aviso gm-aviso--${tipo}`;
        const icono = document.createElement('i');
        icono.className = `bi ${tipo === 'error' ? 'bi-x-circle-fill' : 'bi-check-circle-fill'}`;
        icono.setAttribute('aria-hidden', 'true');
        const msg = document.createElement('span');
        msg.textContent = texto;
        const cerrar = document.createElement('button');
        cerrar.type = 'button';
        cerrar.className = 'gm-aviso-x';
        cerrar.setAttribute('aria-label', 'Cerrar aviso');
        cerrar.innerHTML = '<i class="bi bi-x-lg" aria-hidden="true"></i>';
        cerrar.addEventListener('click', () => el.remove());
        el.append(icono, msg, cerrar);
        caja.append(el);
        // Los errores se quedan hasta que se cierran (no se puede perder un fallo por un temporizador).
        if (tipo !== 'error') setTimeout(() => el.remove(), 6000);
    }

    /* ───────────── Red ───────────── */
    async function enviar(url, formData) {
        const resp = await fetch(url, {
            method: 'POST',
            body: formData,
            headers: { 'X-CSRFToken': csrf() },
            credentials: 'same-origin',
        });
        let data = {};
        try { data = await resp.json(); } catch (e) { /* respuesta sin JSON */ }
        if (!resp.ok || data.error) {
            const motivo = data.error || (typeof data.detail === 'string' ? data.detail : '');
            throw new Error(motivo || 'No se pudo completar la operación.');
        }
        return data;
    }

    /* ───────────── Diálogos nativos ───────────── */
    const ultimoFoco = new WeakMap();
    function abrir(dlg, disparador) {
        ultimoFoco.set(dlg, disparador || document.activeElement);
        if (typeof dlg.showModal === 'function') dlg.showModal(); else dlg.setAttribute('open', '');
    }
    document.querySelectorAll('dialog.gm-dialogo').forEach((dlg) => {
        // Clic en el fondo = cancelar (la «caja» ocupa todo el diálogo; solo el fondo llega con target = dialog).
        dlg.addEventListener('click', (e) => { if (e.target === dlg) dlg.close('cancelar'); });
        dlg.addEventListener('close', () => {
            const volver = ultimoFoco.get(dlg);
            if (volver && volver.isConnected) volver.focus();
        });
    });
    document.addEventListener('click', (e) => {
        const cerrar = e.target.closest('[data-cerrar]');
        if (cerrar) document.getElementById(cerrar.dataset.cerrar)?.close('cancelar');
    });

    function confirmar({ titulo, mensaje, textoOk, disparador, peligro = false }) {
        const dlg = $('#dlg-confirmar');
        $('#dlg-conf-titulo').textContent = titulo;
        $('#dlg-conf-texto').textContent = mensaje;
        const ok = $('#dlg-conf-ok');
        ok.textContent = textoOk;
        ok.classList.toggle('gm-btn--peligro', peligro);
        ok.classList.toggle('gm-btn--primario', !peligro);
        return new Promise((resolver) => {
            dlg.addEventListener('close', () => resolver(dlg.returnValue === 'ok'), { once: true });
            dlg.returnValue = 'cancelar';
            abrir(dlg, disparador);
        });
    }

    /* ───────────── Estado visual de cada fila ───────────── */
    const CLASES_DIF = { 'Muy Fácil': 'dif-muyfacil', 'Fácil': 'dif-facil', 'Medio': 'dif-medio', 'Difícil': 'dif-dificil' };
    function colorDificultad(select) {
        select.classList.remove(...Object.values(CLASES_DIF));
        if (CLASES_DIF[select.value]) select.classList.add(CLASES_DIF[select.value]);
    }

    function etiquetar(tr) {
        // Tras renombrar, todas las etiquetas accesibles de la fila vuelven a nombrar la máquina correcta.
        const n = tr.dataset.nombre;
        const poner = (sel, texto) => { const el = $(sel, tr); if (el) el.setAttribute('aria-label', texto); };
        poner('[name="nombre"]', `Nombre de la máquina ${n}`);
        poner('[name="dificultad"]', `Dificultad de ${n}`);
        poner('[name="categoria"]', `Categoría de ${n}`);
        poner('[name="sistema_operativo"]', `Plataforma de ${n}`);
        poner('[data-accion="invitados"]', `Acceso de invitados a ${n}`);
        poner('[data-accion="stats"]', `Estadísticas de ${n}`);
        poner('[data-accion="detalles"]', `Editar detalles de ${n}`);
        poner('[data-accion="eliminar"]', `Eliminar ${n}`);
        poner('.gm-acciones', `Acciones de ${n}`);
        const img = $('img.gm-logo-img', tr); if (img) img.alt = `Logo de ${n}`;
        const sub = $('.gm-subir .gm-oculto', tr); if (sub) sub.textContent = `Subir logo de ${n}`;
        marcarPendiente(tr, tr.classList.contains('is-dirty'));
    }

    function marcarPendiente(tr, pendiente) {
        tr.classList.toggle('is-dirty', pendiente);
        const etiqueta = $('.gm-pendiente', tr);
        if (etiqueta) etiqueta.hidden = !pendiente;
        const btn = $('[data-accion="guardar"]', tr);
        if (btn) btn.setAttribute('aria-label', `Guardar cambios de ${tr.dataset.nombre}${pendiente ? ' (hay cambios sin guardar)' : ''}`);
    }

    /* ───────────── Guardar ───────────── */
    async function guardar(tr, { silencioso = false } = {}) {
        if (tr.classList.contains('is-guardando')) return false;
        const id = tr.dataset.id;
        const d = datos[id] || {};
        const campoNombre = $('[name="nombre"]', tr);
        const nombre = campoNombre.value.trim();
        if (!nombre) {
            aviso('El nombre de la máquina no puede estar vacío.', 'error');
            campoNombre.focus();
            return false;
        }

        // Mismo contrato de siempre con /api/gestion-maquinas/actualizar: se envían todos los campos.
        const fd = new FormData();
        fd.set('csrf_token', csrf());
        fd.set('id', id);
        fd.set('origen', origen);
        fd.set('nombre', nombre);
        fd.set('dificultad', $('[name="dificultad"]', tr).value);
        fd.set('autor', d.autor ?? '');
        fd.set('enlace_autor', d.enlace_autor ?? '');
        fd.set('fecha', d.fecha ?? '');
        fd.set('imagen', d.imagen ?? '');
        fd.set('descripcion', d.descripcion ?? '');
        fd.set('link_descarga', d.link_descarga ?? '');
        const cat = $('[name="categoria"]', tr);
        fd.set('categoria', cat ? cat.value : (d.categoria ?? ''));   // en BunkerLabs se conserva la existente
        const so = $('[name="sistema_operativo"]', tr);
        if (so) fd.set('sistema_operativo', so.value);

        tr.classList.add('is-guardando');
        tr.setAttribute('aria-busy', 'true');
        try {
            const data = await enviar('/api/gestion-maquinas/actualizar', fd);
            tr.dataset.nombre = nombre;
            if (cat) d.categoria = cat.value;
            marcarPendiente(tr, false);
            etiquetar(tr);
            if (!silencioso) aviso(data.message || `«${nombre}» guardada correctamente.`);
            return true;
        } catch (err) {
            aviso(err.message || 'Error de red al comunicar con el servidor.', 'error');
            return false;
        } finally {
            tr.classList.remove('is-guardando');
            tr.removeAttribute('aria-busy');
        }
    }

    /* ───────────── Estadísticas ───────────── */
    function tarjetaStat(icono, valor, etiqueta) {
        const card = document.createElement('div');
        card.className = 'gm-stat';
        const i = document.createElement('i');
        i.className = `bi ${icono}`;
        i.setAttribute('aria-hidden', 'true');
        const v = document.createElement('strong');
        v.textContent = valor;
        const l = document.createElement('span');
        l.textContent = etiqueta;
        const texto = document.createElement('div');
        texto.append(v, l);
        card.append(i, texto);
        return card;
    }

    async function verEstadisticas(tr, disparador) {
        const cuerpo = $('#dlg-stats-cuerpo');
        $('#dlg-stats-sub').textContent = tr.dataset.nombre;
        cuerpo.setAttribute('aria-busy', 'true');
        cuerpo.replaceChildren(Object.assign(document.createElement('p'), { className: 'gm-estado', textContent: 'Cargando estadísticas…' }));
        abrir($('#dlg-stats'), disparador);
        try {
            const resp = await fetch(`/api/gestion-maquinas/machine-stats/${encodeURIComponent(tr.dataset.id)}`, { credentials: 'same-origin' });
            const data = await resp.json();
            if (!resp.ok || data.error) throw new Error(data.error || 'No se pudieron cargar las estadísticas.');
            const votos = data.rating_count > 0 ? `Valoración (${data.rating_count} ${data.rating_count === 1 ? 'voto' : 'votos'})` : 'Valoración (sin votos)';
            cuerpo.replaceChildren(
                tarjetaStat('bi-file-earmark-text', data.writeups, 'Writeups publicados'),
                tarjetaStat('bi-download', data.descargas, 'Descargas'),
                tarjetaStat('bi-star-fill', `${data.rating_avg} / 5`, votos),
            );
        } catch (err) {
            const p = document.createElement('p');
            p.className = 'gm-estado gm-estado--error';
            p.textContent = err instanceof TypeError ? 'Error de red al cargar las estadísticas.' : err.message;
            cuerpo.replaceChildren(p);
        } finally {
            cuerpo.removeAttribute('aria-busy');
        }
    }

    /* ───────────── Detalles (enlace autor, descripción, link de descarga) ───────────── */
    let filaDetalles = null;
    function abrirDetalles(tr, disparador) {
        filaDetalles = tr;
        const d = datos[tr.dataset.id] || {};
        $('#dlg-detalles-sub').textContent = tr.dataset.nombre;
        $('#det-enlace').value = d.enlace_autor || '';
        $('#det-descripcion').value = d.descripcion || '';
        $('#det-link').value = d.link_descarga || '';
        const err = $('#det-error'); err.hidden = true; err.textContent = '';
        abrir($('#dlg-detalles'), disparador);
        $('#det-enlace').focus();
    }

    const urlValida = (v) => { try { const u = new URL(v); return u.protocol === 'http:' || u.protocol === 'https:'; } catch (e) { return false; } };

    async function guardarDetalles() {
        if (!filaDetalles) return;
        const err = $('#det-error');
        const enlace = $('#det-enlace').value.trim();
        const link = $('#det-link').value.trim();
        const fallo = (texto, campo) => { err.textContent = texto; err.hidden = false; campo.focus(); };
        if (enlace && !urlValida(enlace)) return fallo('El enlace del autor debe empezar por http:// o https://.', $('#det-enlace'));
        if (!link || !urlValida(link)) return fallo('El link de descarga es obligatorio y debe empezar por http:// o https://.', $('#det-link'));
        if (!$('#det-descripcion').value.trim()) return fallo('La descripción no puede estar vacía.', $('#det-descripcion'));

        const d = datos[filaDetalles.dataset.id];
        const anterior = { ...d };
        d.enlace_autor = enlace;
        d.descripcion = $('#det-descripcion').value;
        d.link_descarga = link;
        const boton = $('#det-guardar');
        boton.disabled = true;
        const ok = await guardar(filaDetalles);
        boton.disabled = false;
        if (ok) { $('#dlg-detalles').close('ok'); filaDetalles = null; }
        else { Object.assign(d, anterior); fallo('No se pudo guardar. Revisa el aviso de error y vuelve a intentarlo.', boton); }
    }

    /* ───────────── Eliminar ───────────── */
    function actualizarContadores(delta) {
        const resumen = $('#gm-resumen');
        if (resumen && resumen.dataset.total) {
            const total = Math.max(0, Number(resumen.dataset.total) + delta);
            const fin = Math.max(0, Number(resumen.dataset.fin) + delta);
            resumen.dataset.total = total; resumen.dataset.fin = fin;
            const fuertes = resumen.querySelectorAll('strong');
            if (fuertes.length >= 2) { fuertes[0].textContent = `${resumen.dataset.inicio}–${fin}`; fuertes[1].textContent = total; }
        }
        const contador = $(`[data-contador="${origen}"]`);
        if (contador) contador.textContent = Math.max(0, Number(contador.textContent) + delta);
    }

    async function eliminar(tr, disparador) {
        const nombre = tr.dataset.nombre;
        const si = await confirmar({
            titulo: `¿Eliminar «${nombre}»?`,
            mensaje: `Se eliminará la máquina «${nombre}» de ${nombrePlataforma}. Esta acción no se puede deshacer.`,
            textoOk: 'Eliminar máquina',
            peligro: true,
            disparador,
        });
        if (!si) return;

        const fd = new FormData();
        fd.set('csrf_token', csrf());
        fd.set('id', tr.dataset.id);
        fd.set('origen', origen);
        tr.classList.add('is-guardando');
        try {
            const data = await enviar('/api/gestion-maquinas/eliminar', fd);
            const vecina = tr.nextElementSibling || tr.previousElementSibling;
            delete datos[tr.dataset.id];
            tr.remove();
            actualizarContadores(-1);
            aviso(data.message || `«${nombre}» eliminada.`);
            if (vecina) $('[name="nombre"]', vecina)?.focus();   // el foco no se pierde en el vacío
            else window.location.reload();                       // era la última de la página
        } catch (err) {
            tr.classList.remove('is-guardando');
            aviso(err.message || 'Error de red al comunicar con el servidor.', 'error');
        }
    }

    /* ───────────── Acceso de invitados (BunkerLabs) ───────────── */
    async function alternarInvitados(tr, boton) {
        const permitido = boton.getAttribute('aria-checked') === 'true';
        const si = await confirmar({
            titulo: permitido ? 'Bloquear acceso de invitados' : 'Permitir acceso de invitados',
            mensaje: `¿${permitido ? 'Bloquear' : 'Permitir'} el acceso de invitados a «${tr.dataset.nombre}»?`,
            textoOk: permitido ? 'Bloquear' : 'Permitir',
            peligro: permitido,
            disparador: boton,
        });
        if (!si) return;
        const fd = new FormData();
        fd.set('csrf_token', csrf());
        fd.set('id', tr.dataset.id);
        boton.disabled = true;
        try {
            const data = await enviar('/api/gestion-maquinas/toggle-guest-access', fd);
            boton.setAttribute('aria-checked', data.guest_access ? 'true' : 'false');
            $('.gm-interruptor-txt', boton).textContent = data.guest_access ? 'Permitido' : 'Bloqueado';
            aviso(data.guest_access ? `«${tr.dataset.nombre}» desbloqueada para invitados.` : `«${tr.dataset.nombre}» bloqueada para invitados.`);
        } catch (err) {
            aviso(err.message || 'Error de red al comunicar con el servidor.', 'error');
        } finally {
            boton.disabled = false;
            boton.focus();
        }
    }

    /* ───────────── Logo ───────────── */
    async function subirLogo(tr, input) {
        const archivo = input.files && input.files[0];
        if (!archivo) return;
        if (!TIPOS_LOGO.test(archivo.type)) { aviso('El archivo debe ser una imagen.', 'error'); input.value = ''; return; }
        if (archivo.size > MAX_LOGO) {
            aviso(`La imagen pesa ${(archivo.size / 1048576).toFixed(1)} MB; el máximo es 2 MB.`, 'error');
            input.value = '';
            return;
        }
        const fd = new FormData();
        fd.set('csrf_token', csrf());
        fd.set('logo', archivo);
        fd.set('machine_id', tr.dataset.id);
        fd.set('origen', origen);
        const zona = $('.gm-logo', tr);
        zona.classList.add('is-subiendo');
        zona.setAttribute('aria-busy', 'true');
        input.disabled = true;
        try {
            const data = await enviar('/api/gestion-maquinas/upload-logo', fd);
            let img = $('img.gm-logo-img', tr);
            if (!img) {
                $('.gm-logo-vacio', tr)?.remove();
                img = Object.assign(document.createElement('img'), { className: 'gm-logo-img', width: 44, height: 44, decoding: 'async' });
                zona.prepend(img);
            }
            img.src = data.thumb_url || data.image_url;
            img.alt = `Logo de ${tr.dataset.nombre}`;
            aviso(`Logo de «${tr.dataset.nombre}» actualizado.`);
        } catch (err) {
            aviso(err.message || 'Error al subir la imagen.', 'error');
        } finally {
            zona.classList.remove('is-subiendo');
            zona.removeAttribute('aria-busy');
            input.disabled = false;
            input.value = '';
        }
    }

    /* ───────────── Eventos ───────────── */
    document.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-accion]');
        if (!btn) return;
        const tr = filaDe(btn);
        if (!tr) return;
        switch (btn.dataset.accion) {
            case 'guardar': guardar(tr); break;
            case 'eliminar': eliminar(tr, btn); break;
            case 'stats': verEstadisticas(tr, btn); break;
            case 'detalles': abrirDetalles(tr, btn); break;
            case 'invitados': alternarInvitados(tr, btn); break;
        }
    });

    if (tabla) {
        // Cambios en los campos de la fila: marcar «sin guardar»; la dificultad cambia de color.
        tabla.addEventListener('input', (e) => {
            const tr = filaDe(e.target);
            if (tr && e.target.matches('input[name], select[name]')) marcarPendiente(tr, true);
        });
        tabla.addEventListener('change', (e) => {
            const tr = filaDe(e.target);
            if (!tr) return;
            if (e.target.matches('select[name="dificultad"]')) colorDificultad(e.target);
            if (e.target.matches('select[name]')) marcarPendiente(tr, true);
            if (e.target.matches('input[type="file"][data-accion="logo"]')) subirLogo(tr, e.target);
        });
        // Intro dentro del nombre guarda la fila (antes lo hacía el <form>).
        tabla.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && e.target.matches('input[name="nombre"]')) { e.preventDefault(); const tr = filaDe(e.target); if (tr) guardar(tr); }
        });
        tabla.querySelectorAll('select[name="dificultad"]').forEach(colorDificultad);
    }

    $('#det-guardar')?.addEventListener('click', guardarDetalles);

    // Aviso antes de abandonar la página con filas modificadas sin guardar.
    window.addEventListener('beforeunload', (e) => {
        if (tabla && tabla.querySelector('tr.is-dirty')) { e.preventDefault(); e.returnValue = ''; }
    });
})();
