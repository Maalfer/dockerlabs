// Gestión de accesos de BunkerLabs (/bunkerlabs/gestion).
// Cada fila lleva sus datos en data-* y sus botones un data-accion:
// copiar / enlace / historial / alternar. El borrado es un <form> normal que
// aquí se envía con fetch (si no hay JS, sigue funcionando con recarga).
(function () {
    'use strict';
    var app = document.getElementById('bg-app');
    if (!app) return;
    var csrf = app.getAttribute('data-csrf') || '';

    /* ---------- utilidades ---------- */
    function pide(url, metodo) {
        return fetch(url, {
            method: metodo || 'POST',
            credentials: 'same-origin',
            headers: { 'X-CSRFToken': csrf, 'Accept': 'application/json' }
        }).then(function (r) {
            return r.json().catch(function () { return {}; }).then(function (d) {
                if (!r.ok) throw new Error(d.error || d.detail || ('Error ' + r.status + ' del servidor'));
                return d;
            });
        });
    }
    function aviso(texto, error) {
        document.querySelectorAll('.bg-toast').forEach(function (t) { t.remove(); });
        var t = document.createElement('div');
        t.className = 'bg-toast' + (error ? ' bg-toast--error' : '');
        t.setAttribute('role', 'status');
        t.textContent = texto;
        document.body.appendChild(t);
        setTimeout(function () { t.classList.add('bg-toast--sale'); setTimeout(function () { t.remove(); }, 300); }, 3200);
    }
    function copia(texto) {
        if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(texto);
        return new Promise(function (ok, mal) {
            var ta = document.createElement('textarea');
            ta.value = texto; ta.style.position = 'fixed'; ta.style.left = '-9999px';
            document.body.appendChild(ta); ta.focus(); ta.select();
            try { document.execCommand('copy') ? ok() : mal(); } catch (e) { mal(e); }
            document.body.removeChild(ta);
        });
    }
    function marcaCopiado(btn) {
        var i = btn.querySelector('i'), antes = i.className;
        i.className = 'bi bi-check2'; btn.classList.add('bg-icono--ok');
        setTimeout(function () { i.className = antes; btn.classList.remove('bg-icono--ok'); }, 1600);
    }
    function num(id, delta) {
        var el = document.getElementById(id);
        if (el) el.textContent = Math.max(0, (parseInt(el.textContent, 10) || 0) + delta);
    }

    /* ---------- generar contraseña ---------- */
    var generar = document.getElementById('bg-generar'), campoPw = document.getElementById('bg-password');
    if (generar && campoPw) {
        generar.addEventListener('click', function () {
            var abc = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789', n = 16, out = '';
            var azar = new Uint32Array(n);
            (window.crypto || window.msCrypto).getRandomValues(azar);
            for (var i = 0; i < n; i++) out += abc[azar[i] % abc.length];
            campoPw.value = out;
            campoPw.focus(); campoPw.select();
        });
    }
    // evita el doble envío del formulario de alta
    var form = document.getElementById('bg-form');
    if (form) form.addEventListener('submit', function () {
        var b = form.querySelector('button[type="submit"]');
        if (b) setTimeout(function () { b.disabled = true; }, 0);
    });

    /* ---------- buscar y filtrar ---------- */
    var buscar = document.getElementById('bg-buscar'), filtro = document.getElementById('bg-filtro');
    var sinResultados = document.getElementById('bg-sin-resultados');
    function filas() { return Array.prototype.slice.call(document.querySelectorAll('.bg-fila')); }
    function aplicaFiltro() {
        var q = buscar ? buscar.value.trim().toLowerCase() : '', f = filtro ? filtro.value : '', visibles = 0;
        filas().forEach(function (tr) {
            var texto = ((tr.getAttribute('data-nombre') || '') + ' ' + (tr.getAttribute('data-token') || '')).toLowerCase();
            var activo = tr.getAttribute('data-activo') === '1';
            var ok = (!q || texto.indexOf(q) >= 0) &&
                (!f || (f === 'activo' && activo) || (f === 'inactivo' && !activo) ||
                 (f === 'sinuso' && tr.getAttribute('data-accesos') === '0'));
            tr.hidden = !ok;
            if (ok) visibles++;
        });
        if (sinResultados) sinResultados.hidden = visibles > 0 || !filas().length;
    }
    if (buscar) buscar.addEventListener('input', aplicaFiltro);
    if (filtro) filtro.addEventListener('change', aplicaFiltro);

    /* ---------- historial (modal) ---------- */
    var modalEl = document.getElementById('logsModal');
    var modal = modalEl && window.bootstrap ? new bootstrap.Modal(modalEl) : null;
    var L = {
        lista: document.getElementById('logsList'), carga: document.getElementById('logsLoading'),
        vacio: document.getElementById('logsEmpty'), vacioTxt: document.getElementById('logsEmptyTxt'),
        caja: document.getElementById('logsContainer'), limpiar: document.getElementById('btnClearHistory'),
        nombre: document.getElementById('logsNombre'), resumen: document.getElementById('logsResumen')
    };
    var filaActual = null;
    function estadoModal(cual) {
        L.carga.classList.toggle('d-none', cual !== 'carga');
        L.caja.classList.toggle('d-none', cual !== 'lista');
        L.resumen.classList.toggle('d-none', cual !== 'lista');
        L.vacio.classList.toggle('d-none', cual !== 'vacio');
        L.limpiar.disabled = cual !== 'lista';
    }
    function abreHistorial(tr) {
        if (!modal) return;
        filaActual = tr;
        L.nombre.textContent = tr.getAttribute('data-nombre') || 'accesos';
        L.lista.textContent = '';
        L.vacioTxt.textContent = 'No hay registros de acceso.';
        estadoModal('carga');
        modal.show();
        pide('/api/bunker/logs/' + tr.getAttribute('data-id'), 'GET').then(function (d) {
            if (filaActual !== tr) return;
            var logs = (d && d.logs) || [];
            if (!logs.length) { estadoModal('vacio'); return; }
            logs.forEach(function (log) {
                var fila = document.createElement('tr'), a = document.createElement('td'), b = document.createElement('td');
                a.className = 'ps-4'; b.className = 'text-end pe-4 text-secondary small';
                var ic = document.createElement('i'); ic.className = 'bi bi-person-circle text-secondary me-2';
                var n = document.createElement('span'); n.className = 'fw-medium text-white'; n.textContent = log.nombre;
                a.appendChild(ic); a.appendChild(n);
                b.textContent = log.fecha;
                fila.appendChild(a); fila.appendChild(b);
                L.lista.appendChild(fila);
            });
            var total = d.total || logs.length;
            L.resumen.textContent = total > logs.length
                ? 'Mostrando las ' + logs.length + ' entradas más recientes de ' + total + '.'
                : total + (total === 1 ? ' entrada registrada.' : ' entradas registradas.');
            estadoModal('lista');
        }).catch(function (e) {
            L.vacioTxt.textContent = 'No se pudo cargar el historial: ' + e.message;
            estadoModal('vacio');
        });
    }
    if (L.limpiar) L.limpiar.addEventListener('click', function () {
        if (!filaActual) return;
        var tr = filaActual, nombre = tr.getAttribute('data-nombre') || 'este acceso';
        if (!confirm('¿Eliminar TODO el historial de entradas de «' + nombre + '»?\n\nEl acceso seguirá funcionando. No se puede deshacer.')) return;
        L.limpiar.disabled = true;
        pide('/api/bunker/logs/' + tr.getAttribute('data-id'), 'DELETE').then(function () {
            var antes = parseInt(tr.getAttribute('data-accesos'), 10) || 0;
            tr.setAttribute('data-accesos', '0');
            var uso = tr.querySelector('.bg-uso');
            if (uso) {
                uso.querySelector('.bg-uso-n').innerHTML = '<strong data-campo="accesos">0</strong> entradas';
                uso.querySelector('.bg-meta').innerHTML = '<i class="bi bi-clock-history"></i> historial vacío';
            }
            num('bg-n-accesos', -antes);
            L.lista.textContent = '';
            estadoModal('vacio');
            aviso('Historial de «' + nombre + '» eliminado');
        }).catch(function (e) {
            L.limpiar.disabled = false;
            aviso(e.message, true);
        });
    });

    /* ---------- acciones de cada fila ---------- */
    app.addEventListener('click', function (e) {
        var b = e.target.closest('[data-accion]');
        if (!b) return;
        var tr = b.closest('.bg-fila');
        if (!tr) return;
        var accion = b.getAttribute('data-accion'), token = tr.getAttribute('data-token') || '';
        if (accion === 'copiar') {
            copia(token).then(function () { marcaCopiado(b); aviso('Contraseña copiada'); }, function () { aviso('No se pudo copiar', true); });
        } else if (accion === 'enlace') {
            copia(window.location.origin + '/bunkerlabs/?token=' + encodeURIComponent(token))
                .then(function () { marcaCopiado(b); aviso('Enlace directo copiado'); }, function () { aviso('No se pudo copiar', true); });
        } else if (accion === 'historial') {
            abreHistorial(tr);
        } else if (accion === 'alternar') {
            b.disabled = true;
            pide('/bunkerlabs/gestion/' + tr.getAttribute('data-id') + '/toggle').then(function (d) {
                var activo = !!d.activo;
                tr.setAttribute('data-activo', activo ? '1' : '0');
                tr.classList.toggle('bg-fila--inactiva', !activo);
                b.setAttribute('aria-checked', activo ? 'true' : 'false');
                b.querySelector('.bg-interruptor-txt').textContent = activo ? 'Activo' : 'Inactivo';
                num('bg-n-activos', activo ? 1 : -1);
                aviso(d.message || (activo ? 'Acceso activado' : 'Acceso desactivado'));
                aplicaFiltro();
            }).catch(function (err) { aviso(err.message, true); }).then(function () { b.disabled = false; });
        }
    });

    /* ---------- eliminar un acceso ---------- */
    app.addEventListener('submit', function (e) {
        var f = e.target.closest('.bg-borrar');
        if (!f) return;
        e.preventDefault();
        var tr = f.closest('.bg-fila'), nombre = tr.getAttribute('data-nombre') || 'este acceso';
        var n = parseInt(tr.getAttribute('data-accesos'), 10) || 0;
        var extra = n ? '\n\nTambién se borrarán sus ' + n + ' entradas del historial.' : '';
        if (!confirm('¿Eliminar el acceso de «' + nombre + '»?' + extra + '\n\nQuien lo use dejará de poder entrar. No se puede deshacer.')) return;
        var btn = f.querySelector('button');
        btn.disabled = true;
        pide(f.action).then(function () {
            if (tr.getAttribute('data-activo') === '1') num('bg-n-activos', -1);
            num('bg-n-total', -1);
            num('bg-n-accesos', -n);
            tr.classList.add('bg-fila--sale');
            setTimeout(function () {
                tr.remove();
                if (!filas().length) location.reload(); else aplicaFiltro();
            }, 250);
            aviso('Acceso de «' + nombre + '» eliminado');
        }).catch(function (err) {
            btn.disabled = false;
            aviso('No se pudo eliminar: ' + err.message, true);
        });
    });
})();
