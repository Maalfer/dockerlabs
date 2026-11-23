// Writeups publicados (/writeups-publicados).
// Carga las máquinas que tienen writeups, permite buscarlas, filtrarlas y ordenarlas,
// y abre una ventana con los writeups de cada una (?maquina=Nombre enlaza directo).
(function () {
    'use strict';
    var app = document.getElementById('wp-app');
    if (!app) return;
    var moderacion = app.getAttribute('data-moderacion') === 'true';
    var meta = document.querySelector('meta[name="csrf-token"]');
    var csrf = meta ? meta.getAttribute('content') : '';
    var $ = function (id) { return document.getElementById(id); };
    var rejilla = $('wp-rejilla'), rango = $('wp-rango');
    var buscar = $('wp-buscar'), selDif = $('wp-dificultad'), selFmt = $('wp-formato'), selOrden = $('wp-orden'), soloMios = $('wp-mios');
    var maquinas = [];

    /* ---------- utilidades ---------- */
    function el(tag, clase, texto) {
        var e = document.createElement(tag);
        if (clase) e.className = clase;
        if (texto !== undefined && texto !== null) e.textContent = texto;
        return e;
    }
    function icono(nombre) { var i = el('i', 'bi ' + nombre); i.setAttribute('aria-hidden', 'true'); return i; }
    function plano(s) { return (s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim(); }
    function plural(n, uno, varios) { return n + ' ' + (n === 1 ? uno : varios); }
    function esVideo(tipo) { return /v[ií]deo/i.test(tipo || ''); }
    function urlSegura(u) { return /^https?:\/\//i.test(u || '') ? u : '#'; }
    function hace(iso) {
        if (!iso) return '';
        var t = new Date(/Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z');
        if (isNaN(t)) return '';
        var dias = Math.floor((Date.now() - t.getTime()) / 86400000);
        if (dias < 1) return 'hoy';
        if (dias === 1) return 'ayer';
        if (dias < 60) return 'hace ' + dias + ' días';
        if (dias < 730) return 'hace ' + Math.floor(dias / 30) + ' meses';
        return 'hace ' + Math.floor(dias / 365) + ' años';
    }
    function fecha(iso) {
        if (!iso) return '';
        var t = new Date(/Z|[+-]\d\d:?\d\d$/.test(iso) ? iso : iso + 'Z');
        return isNaN(t) ? '' : t.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' });
    }
    function aviso(texto, error) {
        var caja = $('wp-avisos');
        var a = el('div', 'wp-aviso' + (error ? ' wp-aviso--error' : ''), texto);
        caja.appendChild(a);
        setTimeout(function () { a.classList.add('wp-aviso--sale'); setTimeout(function () { a.remove(); }, 300); }, 3800);
    }
    // Cody (si está en la página) comenta lo que pasa, sin insistir
    var ultimoCody = {};
    function cody(clave, expresion) {
        var B = window.DLBallena, ahora = Date.now();
        if (!B || !B.avisa || ahora - (ultimoCody[clave] || 0) < 20000) return;
        ultimoCody[clave] = ahora;
        if (expresion && B.expresion) B.expresion(expresion);
        B.avisa(clave, 3600);
    }
    function pide(url, opciones) {
        return fetch(url, Object.assign({ credentials: 'same-origin' }, opciones || {})).then(function (r) {
            return r.json().catch(function () { return {}; }).then(function (d) {
                if (!r.ok) throw new Error((d && (d.error || d.detail)) || 'Error ' + r.status);
                return d;
            });
        });
    }
    function modo() { return soloMios && soloMios.checked ? 'mine' : 'all'; }

    /* ---------- tarjetas de máquina ---------- */
    function claseDificultad(d) {
        var p = plano(d);
        return p === 'muy facil' ? 'muy-facil' : p === 'facil' ? 'facil' : p === 'medio' ? 'medio' : p === 'dificil' ? 'dificil' : '';
    }
    function logo(m, clase) {
        if (m.imagen) {
            var img = el('img', clase);
            img.src = m.imagen; img.alt = ''; img.loading = 'lazy'; img.width = 64; img.height = 64;
            img.addEventListener('error', function () { img.replaceWith(marcador(clase)); });
            return img;
        }
        return marcador(clase);
    }
    function marcador(clase) { var d = el('div', clase + ' wp-logo-vacio'); d.appendChild(icono('bi-journal-richtext')); return d; }

    function tarjeta(m) {
        var b = el('button', 'wp-tarjeta');
        b.type = 'button';
        b.setAttribute('aria-label', m.maquina + ': ' + plural(m.total, 'writeup', 'writeups'));
        b.appendChild(logo(m, 'wp-tarjeta-logo'));
        b.appendChild(el('span', 'wp-tarjeta-nombre', m.maquina));
        var linea = el('span', 'wp-tarjeta-linea');
        if (m.dificultad) linea.appendChild(el('span', 'wp-dif wp-dif--' + claseDificultad(m.dificultad), m.dificultad));
        linea.appendChild(el('span', 'wp-cuenta', plural(m.total, 'writeup', 'writeups')));
        b.appendChild(linea);
        var tipos = el('span', 'wp-tarjeta-tipos');
        if (m.textos) { var t = el('span'); t.appendChild(icono('bi-file-text')); t.appendChild(document.createTextNode(' ' + m.textos)); t.title = plural(m.textos, 'writeup escrito', 'writeups escritos'); tipos.appendChild(t); }
        if (m.videos) { var v = el('span'); v.appendChild(icono('bi-play-circle-fill')); v.appendChild(document.createTextNode(' ' + m.videos)); v.title = plural(m.videos, 'vídeo', 'vídeos'); tipos.appendChild(v); }
        if (m.ultimo) { var u = el('span', 'wp-tarjeta-fecha', hace(m.ultimo)); u.title = 'Último writeup: ' + fecha(m.ultimo); tipos.appendChild(u); }
        b.appendChild(tipos);
        b.addEventListener('click', function () { abre(m, b); });
        return b;
    }

    function visibles() {
        var q = plano(buscar.value), dif = selDif.value, fmt = selFmt.value, orden = selOrden.value;
        var lista = maquinas.filter(function (m) {
            return (!q || plano(m.maquina).indexOf(q) >= 0) &&
                (!dif || plano(m.dificultad) === dif) &&
                (!fmt || (fmt === 'video' ? m.videos > 0 : m.textos > 0));
        });
        lista.sort(function (a, b) {
            if (orden === 'mas') return b.total - a.total || a.maquina.localeCompare(b.maquina, 'es');
            if (orden === 'menos') return a.total - b.total || a.maquina.localeCompare(b.maquina, 'es');
            if (orden === 'recientes') return String(b.ultimo || '').localeCompare(String(a.ultimo || '')) || a.maquina.localeCompare(b.maquina, 'es');
            return a.maquina.localeCompare(b.maquina, 'es', { sensitivity: 'base' });
        });
        return lista;
    }
    function hayFiltros() { return !!(buscar.value.trim() || selDif.value || selFmt.value); }

    function pinta() {
        var lista = visibles();
        rejilla.textContent = '';
        if (!maquinas.length) {
            rejilla.appendChild(vacio('bi-inbox', modo() === 'mine' ? 'Todavía no tienes writeups publicados.' : 'Todavía no hay writeups publicados.', ''));
            rango.textContent = '';
            return;
        }
        if (!lista.length) {
            var v = vacio('bi-search', 'Ninguna máquina coincide con esos filtros.', '');
            var quitar = el('button', 'dl-btn dl-btn--neutro', 'Quitar filtros');
            quitar.type = 'button';
            quitar.addEventListener('click', function () { buscar.value = ''; selDif.value = ''; selFmt.value = ''; pinta(); buscar.focus(); });
            v.appendChild(quitar);
            rejilla.appendChild(v);
            rango.textContent = '';
            if (buscar.value.trim()) cody('wp_nada', 'niega');
            return;
        }
        var trozo = document.createDocumentFragment();
        lista.forEach(function (m) { trozo.appendChild(tarjeta(m)); });
        rejilla.appendChild(trozo);
        rango.textContent = hayFiltros()
            ? 'Mostrando ' + lista.length + ' de ' + plural(maquinas.length, 'máquina', 'máquinas')
            : plural(maquinas.length, 'máquina', 'máquinas');
    }
    function vacio(ic, texto, sub) {
        var d = el('div', 'wp-vacio');
        d.appendChild(icono(ic));
        d.appendChild(el('p', '', texto));
        if (sub) d.appendChild(el('span', '', sub));
        return d;
    }
    function resumen() {
        var w = 0, v = 0;
        maquinas.forEach(function (m) { w += m.total; v += m.videos || 0; });
        $('wp-n-maquinas').textContent = maquinas.length;
        $('wp-n-writeups').textContent = w;
        $('wp-n-videos').textContent = v;
    }

    function carga() {
        return pide('/api/writeups_subidos/maquinas?filter_mode=' + modo()).then(function (d) {
            maquinas = (d && d.maquinas) || [];
            resumen(); pinta();
        }).catch(function () {
            rejilla.textContent = '';
            var v = vacio('bi-exclamation-triangle', 'No se pudieron cargar los writeups.', '');
            var re = el('button', 'dl-btn dl-btn--neutro', 'Reintentar');
            re.type = 'button'; re.addEventListener('click', carga);
            v.appendChild(re); rejilla.appendChild(v);
        });
    }

    /* ---------- ventana de una máquina ---------- */
    var modal = $('wp-modal'), lista = $('wp-modal-lista'), origen = null, abierta = null;
    function enlaceMaquina(nombre) {
        var u = new URL(window.location.href);
        if (nombre) u.searchParams.set('maquina', nombre); else u.searchParams.delete('maquina');
        history.replaceState(null, '', u.pathname + (u.search || ''));
    }
    function abre(m, desde) {
        origen = desde || document.activeElement; abierta = m;
        $('wp-modal-titulo').textContent = m.maquina;
        var logoCaja = $('wp-modal-logo'); logoCaja.textContent = ''; logoCaja.appendChild(logo(m, 'wp-modal-img'));
        $('wp-modal-sub').textContent = (m.dificultad ? m.dificultad + ' · ' : '') + plural(m.total, 'writeup', 'writeups');
        lista.textContent = ''; lista.appendChild(el('p', 'wp-cargando', 'Cargando writeups…'));
        modal.hidden = false;
        document.documentElement.classList.add('wp-sin-scroll');
        modal.querySelector('.wp-modal-cerrar').focus();
        enlaceMaquina(m.maquina);
        cody('wp_abre');
        pide('/api/writeups_subidos?' + new URLSearchParams({ maquina: m.maquina, filter_mode: modo() })).then(function (ws) {
            if (abierta !== m) return;
            lista.textContent = '';
            if (!Array.isArray(ws) || !ws.length) { lista.appendChild(vacio('bi-inbox', 'No hay writeups para esta máquina.', '')); return; }
            ws.forEach(function (w) { lista.appendChild(fila(w, m)); });
        }).catch(function () {
            lista.textContent = ''; lista.appendChild(vacio('bi-exclamation-triangle', 'No se pudieron cargar los writeups.', ''));
        });
    }
    function cierra() {
        if (modal.hidden) return;
        modal.hidden = true; abierta = null;
        document.documentElement.classList.remove('wp-sin-scroll');
        enlaceMaquina('');
        if (origen && document.contains(origen)) origen.focus();
    }
    function fila(w, m) {
        var video = esVideo(w.tipo);
        var f = el('div', 'wp-fila');
        var ic = el('div', 'wp-fila-icono' + (video ? ' wp-fila-icono--video' : ''));
        ic.appendChild(icono(video ? 'bi-play-circle-fill' : 'bi-file-text'));
        f.appendChild(ic);
        var info = el('div', 'wp-fila-info');
        info.appendChild(el('span', 'wp-fila-autor', w.autor || 'Anónimo'));
        var metaTxt = (video ? 'Vídeo' : 'Writeup escrito') + (w.created_at ? ' · ' + fecha(w.created_at) : '');
        info.appendChild(el('span', 'wp-fila-meta', metaTxt));
        f.appendChild(info);
        var acciones = el('div', 'wp-fila-acciones');
        var ver = el('a', 'dl-btn');
        ver.href = urlSegura(w.url); ver.target = '_blank'; ver.rel = 'noopener noreferrer';
        ver.appendChild(icono('bi-box-arrow-up-right')); ver.appendChild(document.createTextNode(video ? ' Ver vídeo' : ' Ver writeup'));
        acciones.appendChild(ver);
        if (moderacion) {
            var del = el('button', 'dl-btn dl-btn--peligro');
            del.type = 'button'; del.setAttribute('aria-label', 'Eliminar el writeup de ' + (w.autor || 'Anónimo'));
            del.appendChild(icono('bi-trash3'));
            del.addEventListener('click', function () { borra(w, m, f, del); });
            acciones.appendChild(del);
        }
        f.appendChild(acciones);
        return f;
    }
    function borra(w, m, f, btn) {
        if (!confirm('¿Eliminar el writeup de «' + (w.autor || 'Anónimo') + '» para ' + m.maquina + '?\n\nNo se puede deshacer.')) return;
        btn.disabled = true;
        pide('/api/writeups_subidos/' + w.id, { method: 'DELETE', headers: { 'X-CSRFToken': csrf } }).then(function () {
            f.remove();
            m.total = Math.max(0, m.total - 1);
            if (esVideo(w.tipo)) m.videos = Math.max(0, (m.videos || 0) - 1); else m.textos = Math.max(0, (m.textos || 0) - 1);
            if (!m.total) maquinas = maquinas.filter(function (x) { return x !== m; });
            $('wp-modal-sub').textContent = (m.dificultad ? m.dificultad + ' · ' : '') + plural(m.total, 'writeup', 'writeups');
            if (!lista.querySelector('.wp-fila')) lista.appendChild(vacio('bi-inbox', 'No hay writeups para esta máquina.', ''));
            resumen(); pinta();
            aviso('Writeup eliminado correctamente');
            cody('wp_borra');
        }).catch(function (e) {
            btn.disabled = false;
            aviso('No se pudo eliminar: ' + e.message, true);
        });
    }
    modal.addEventListener('click', function (e) { if (e.target.closest('[data-cerrar]')) cierra(); });
    document.addEventListener('keydown', function (e) {
        if (modal.hidden) {
            if (e.key === '/' && !e.ctrlKey && !e.metaKey && !/INPUT|TEXTAREA|SELECT/.test((e.target || {}).tagName || '')) { e.preventDefault(); buscar.focus(); }
            return;
        }
        if (e.key === 'Escape') { e.preventDefault(); cierra(); return; }
        if (e.key === 'Tab') {   // el foco se queda dentro de la ventana
            var f = Array.prototype.filter.call(modal.querySelectorAll('button, a[href]'), function (x) { return !x.disabled && x.offsetParent !== null; });
            if (!f.length) return;
            if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
            else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
        }
    });

    /* ---------- controles ---------- */
    var tBuscar = 0;
    buscar.addEventListener('input', function () { clearTimeout(tBuscar); tBuscar = setTimeout(pinta, 120); });
    [selDif, selFmt, selOrden].forEach(function (s) { s.addEventListener('change', pinta); });
    if (soloMios) soloMios.addEventListener('change', carga);

    carga().then(function () {
        // enlace directo: /writeups-publicados?maquina=Nombre
        var pedida = new URLSearchParams(window.location.search).get('maquina');
        if (!pedida) return;
        var m = maquinas.filter(function (x) { return plano(x.maquina) === plano(pedida); })[0];
        if (m) abre(m, null); else enlaceMaquina('');
    });
})();
