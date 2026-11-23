// Cola de revisión de máquinas (/pending-machines).
// Cada tarjeta tiene botones con data-accion: «estado» (añadida, rechazada o de
// vuelta a pendientes) y «eliminar». Al cambiar de estado la tarjeta sale de la
// pestaña actual, se actualizan los contadores y un aviso permite deshacer.
// «Limpiar» borra de golpe el archivo de añadidas o rechazadas.
document.addEventListener('DOMContentLoaded', function () {
    var app = document.getElementById('pm-app');
    if (!app) return;
    var csrf = app.getAttribute('data-csrf') || '';
    var pestana = app.getAttribute('data-estado') || 'pendiente';
    var API = '/api/admin/pending-machines/';

    function post(url, cuerpo) {
        return fetch(url, {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify(cuerpo || {})
        }).then(function (r) {
            return r.json().catch(function () { return {}; }).then(function (d) {
                if (!r.ok || d.error) throw new Error(d.error || 'No se pudo completar la acción.');
                return d;
            });
        });
    }

    function pintaCuentas(c) {
        if (!c) return;
        document.querySelectorAll('[data-cuenta]').forEach(function (el) {
            var k = el.getAttribute('data-cuenta');
            if (typeof c[k] === 'number') el.textContent = c[k];
        });
    }

    // Quita la tarjeta con una pequeña animación; si la página se queda vacía, recarga
    // (el servidor trae la página anterior o el estado «todo al día»).
    function retira(card) {
        card.classList.add('pm-card--sale');
        setTimeout(function () {
            card.remove();
            if (!document.querySelector('.pm-card')) location.reload();
        }, 260);
    }

    function ocupada(card, si) {
        card.querySelectorAll('button').forEach(function (b) { b.disabled = si; });
        card.classList.toggle('pm-card--ocupada', si);
    }

    function cambiaEstado(card, valor) {
        var id = card.getAttribute('data-id');
        var nombre = card.getAttribute('data-nombre') || 'La máquina';
        var antes = card.getAttribute('data-estado');
        ocupada(card, true);
        post(API + id + '/estado', { estado: valor }).then(function (d) {
            pintaCuentas(d.counts);
            // En «Todas» la tarjeta no sale de la lista: se recarga para verla con su nuevo estado.
            if (pestana === 'todas') { location.reload(); return; }
            retira(card);
            var textos = {
                aprobado: '«' + nombre + '» marcada como añadida',
                rechazado: '«' + nombre + '» rechazada',
                pendiente: '«' + nombre + '» vuelve a pendientes'
            };
            showToast(textos[valor] || d.message, 'success', {
                texto: 'Deshacer',
                accion: function () {
                    post(API + id + '/estado', { estado: antes })
                        .then(function () { location.reload(); })
                        .catch(function (e) { showToast(e.message, 'error'); });
                }
            });
        }).catch(function (e) {
            ocupada(card, false);
            showToast(e.message, 'error');
        });
    }

    function elimina(card) {
        var id = card.getAttribute('data-id');
        var nombre = card.getAttribute('data-nombre') || 'esta máquina';
        if (!confirm('¿Eliminar definitivamente el envío de «' + nombre + '»?\n\nDesaparecerá también de «Mis máquinas enviadas» de su autor. No se puede deshacer.')) return;
        ocupada(card, true);
        post(API + id + '/reject').then(function (d) {
            pintaCuentas(d.counts);
            retira(card);
            showToast('Envío de «' + nombre + '» eliminado');
        }).catch(function (e) {
            ocupada(card, false);
            showToast(e.message, 'error');
        });
    }

    app.addEventListener('click', function (e) {
        var b = e.target.closest('[data-accion]');
        if (b) {
            var card = b.closest('.pm-card');
            if (!card) return;
            if (b.getAttribute('data-accion') === 'estado') cambiaEstado(card, b.getAttribute('data-valor'));
            else if (b.getAttribute('data-accion') === 'eliminar') elimina(card);
            return;
        }
        var l = e.target.closest('[data-limpiar]');
        if (l) {
            var estado = l.getAttribute('data-limpiar');
            var dias = parseInt(l.getAttribute('data-dias') || '0', 10) || 0;
            var que = estado === 'aprobado' ? 'añadidas' : 'rechazadas';
            var pregunta = dias
                ? '¿Eliminar las ' + que + ' revisadas hace más de ' + dias + ' días?'
                : '¿Eliminar las ' + (l.getAttribute('data-total') || '') + ' ' + que + ' del archivo?';
            if (!confirm(pregunta + '\n\nSus autores dejarán de verlas en «Mis máquinas enviadas». No se puede deshacer.')) return;
            l.disabled = true;
            post(API + 'limpiar', { estado: estado, dias: dias || null }).then(function (d) {
                if (!d.eliminadas) { l.disabled = false; showToast('No había nada que limpiar con ese criterio'); return; }
                showToast(d.message);
                setTimeout(function () { location.reload(); }, 700);
            }).catch(function (err) {
                l.disabled = false;
                showToast(err.message, 'error');
            });
        }
    });

    // Cambiar el orden aplica el filtro al momento
    var orden = document.getElementById('pm-orden');
    if (orden) orden.addEventListener('change', function () { orden.form.submit(); });

    // «/» lleva al buscador
    document.addEventListener('keydown', function (e) {
        if (e.key !== '/' || e.ctrlKey || e.metaKey || e.altKey) return;
        var t = e.target;
        if (t && (t.tagName === 'INPUT' || t.tagName === 'TEXTAREA' || t.tagName === 'SELECT' || t.isContentEditable)) return;
        var campo = app.querySelector('input[name="q"]');
        if (campo) { e.preventDefault(); campo.focus(); campo.select(); }
    });
});

// Aviso flotante. `boton` opcional: { texto, accion } (p. ej. «Deshacer»).
function showToast(message, type, boton) {
    document.querySelectorAll('.pm-toast').forEach(function (t) { t.remove(); });
    var toast = document.createElement('div');
    toast.className = 'pm-toast' + (type === 'error' ? ' pm-toast--error' : '');
    toast.setAttribute('role', 'status');
    var txt = document.createElement('span');
    txt.textContent = message;
    toast.appendChild(txt);
    var cerrar = function () {
        toast.classList.add('pm-toast--sale');
        setTimeout(function () { toast.remove(); }, 300);
    };
    if (boton) {
        var b = document.createElement('button');
        b.type = 'button';
        b.textContent = boton.texto;
        b.addEventListener('click', function () { b.disabled = true; boton.accion(); cerrar(); });
        toast.appendChild(b);
    }
    document.body.appendChild(toast);
    setTimeout(cerrar, boton ? 7000 : 3200);
}
