/* Gestión de cookies y almacenamiento local (LSSI art. 22.2 + guía AEPD).
   - Necesarias (sesión, recordar esta elección): siempre activas, no requieren consentimiento.
   - Preferencias (guía vista, frases de Cody, aviso de instalar la app, caché/modo sin conexión):
     DESACTIVADAS por defecto; solo se usan tras consentir. Rechazar o retirar el consentimiento
     borra todo lo que hubiera guardado.
   La elección dura 12 meses y se puede cambiar en cualquier momento desde «Gestionar cookies».
   API: window.DLConsent.permite("preferencias"), .abrir(); evento "dl-consent" al cambiar. */
(function () {
    "use strict";
    var CLAVE = "dl-consentimiento", VERSION = 1, VIGENCIA = 365 * 864e5;
    var CLAVES_PREF = ["dl-cody-vistas", "dl-guia-vista", "dl-install-dismissed"];
    var memoria = null, estado = null;

    function leer() {
        try {
            var d = JSON.parse(localStorage.getItem(CLAVE) || "null");
            if (d && d.v === VERSION && typeof d.t === "number" && typeof d.preferencias === "boolean" && Date.now() - d.t < VIGENCIA) return d;
        } catch (e) { /* sin storage */ }
        return memoria;
    }
    estado = leer();

    function permite(cat) { return cat === "necesarias" ? true : !!(estado && estado.preferencias); }

    function limpiar() {
        CLAVES_PREF.forEach(function (k) { try { localStorage.removeItem(k); } catch (e) {} });
        try {
            if (navigator.serviceWorker && navigator.serviceWorker.getRegistrations) {
                navigator.serviceWorker.getRegistrations().then(function (rs) { rs.forEach(function (r) { r.unregister(); }); }).catch(function () {});
            }
            if (window.caches && caches.keys) {
                caches.keys().then(function (ks) { ks.forEach(function (k) { caches.delete(k); }); }).catch(function () {});
            }
        } catch (e) {}
    }

    function guardar(preferencias) {
        estado = { v: VERSION, t: Date.now(), preferencias: !!preferencias };
        memoria = estado;
        try { localStorage.setItem(CLAVE, JSON.stringify(estado)); } catch (e) {}
        if (!estado.preferencias) limpiar();
        try { window.dispatchEvent(new CustomEvent("dl-consent", { detail: { preferencias: estado.preferencias } })); } catch (e) {}
    }

    // Sin consentimiento (o sin decisión): se elimina cualquier resto de visitas anteriores.
    if (!permite("preferencias")) limpiar();

    /* ---------------- Interfaz ---------------- */
    var banner = null, modal = null, ultimoFoco = null, chkPref = null;

    function el(html) { var d = document.createElement("div"); d.innerHTML = html.trim(); return d.firstChild; }

    function construir() {
        banner = el(
'<div class="dl-ck-banner" id="dl-ck-banner" role="dialog" aria-labelledby="dl-ck-titulo" aria-describedby="dl-ck-texto" hidden>' +
'  <div class="dl-ck-banner-in">' +
'    <div class="dl-ck-texto">' +
'      <strong id="dl-ck-titulo"><i class="bi bi-shield-check" aria-hidden="true"></i> Tu privacidad en DockerLabs</strong>' +
'      <p id="dl-ck-texto">Solo usamos almacenamiento propio: lo necesario para iniciar sesión está siempre activo. Con tu permiso, además guardamos ' +
'        preferencias de comodidad en tu dispositivo (guía vista, frases de Cody sin repetir, modo sin conexión). ' +
'        Sin publicidad ni analítica de terceros. <a href="/politica-cookies">Política de Cookies</a>.</p>' +
'    </div>' +
'    <div class="dl-ck-acciones">' +
'      <button type="button" class="dl-btn dl-btn--neutro" data-ck="rechazar">Rechazar las no esenciales</button>' +
'      <button type="button" class="dl-btn dl-btn--neutro" data-ck="configurar">Configurar</button>' +
'      <button type="button" class="dl-btn dl-btn--neutro" data-ck="aceptar">Aceptar todas</button>' +
'    </div>' +
'  </div>' +
'</div>');
        modal = el(
'<div class="dl-ck-modal" id="dl-ck-modal" hidden>' +
'  <div class="dl-ck-dialogo" role="dialog" aria-modal="true" aria-labelledby="dl-ck-mtitulo">' +
'    <button type="button" class="dl-ck-x" data-ck="cerrar" aria-label="Cerrar">&times;</button>' +
'    <h2 id="dl-ck-mtitulo">Preferencias de cookies</h2>' +
'    <p class="dl-ck-intro">Elige qué podemos guardar en tu dispositivo. Puedes cambiarlo cuando quieras desde «Gestionar cookies», en el pie de página.</p>' +
'    <label class="dl-ck-opcion">' +
'      <input type="checkbox" checked disabled>' +
'      <span><strong>Necesarias</strong> <em>Siempre activas</em>' +
'        <small>Cookie de sesión al iniciar sesión (<code>session</code>) y recordar esta elección (<code>dl-consentimiento</code>). Son imprescindibles y no requieren consentimiento.</small></span>' +
'    </label>' +
'    <label class="dl-ck-opcion">' +
'      <input type="checkbox" id="dl-ck-pref">' +
'      <span><strong>Preferencias y modo sin conexión</strong> <em>Desactivadas por defecto</em>' +
'        <small>Recuerda que ya viste la guía de ayuda, las frases que te mostró Cody para no repetirlas, que descartaste el aviso de instalar la app, ' +
'        y guarda archivos para que la web cargue más rápido y funcione sin conexión. No contienen datos personales ni salen de tu dispositivo.</small></span>' +
'    </label>' +
'    <p class="dl-ck-nota">Los vídeos de YouTube nunca se cargan sin que pulses «Reproducir». No usamos cookies publicitarias ni analíticas de terceros.</p>' +
'    <div class="dl-ck-acciones dl-ck-acciones-modal">' +
'      <button type="button" class="dl-btn dl-btn--neutro" data-ck="rechazar">Rechazar las no esenciales</button>' +
'      <button type="button" class="dl-btn dl-btn--neutro" data-ck="guardar">Guardar selección</button>' +
'      <button type="button" class="dl-btn dl-btn--neutro" data-ck="aceptar">Aceptar todas</button>' +
'    </div>' +
'  </div>' +
'</div>');
        document.body.appendChild(banner);
        document.body.appendChild(modal);
        chkPref = modal.querySelector("#dl-ck-pref");
        document.addEventListener("click", function (e) {
            var b = e.target.closest && e.target.closest("[data-ck]");
            if (b && (banner.contains(b) || modal.contains(b))) { accion(b.getAttribute("data-ck")); return; }
            var abrirLink = e.target.closest && e.target.closest("[data-cookie-prefs]");
            if (abrirLink) { e.preventDefault(); abrirConfig(); }
        });
        modal.addEventListener("mousedown", function (e) { if (e.target === modal) cerrarConfig(); });
        document.addEventListener("keydown", teclado);
    }

    function accion(a) {
        if (a === "aceptar") { guardar(true); finalizar(); }
        else if (a === "rechazar") { guardar(false); finalizar(); }
        else if (a === "guardar") { guardar(chkPref.checked); finalizar(); }
        else if (a === "configurar") abrirConfig();
        else if (a === "cerrar") cerrarConfig();
    }

    function finalizar() {
        cerrarConfig(true);
        mostrarBanner(false);
    }

    function mostrarBanner(si) {
        banner.hidden = !si;
        document.documentElement.classList.toggle("dl-ck-abierto", si);
        if (si) document.documentElement.style.setProperty("--dl-ck-alto", banner.offsetHeight + "px");
    }

    function abrirConfig() {
        if (!modal) return;
        ultimoFoco = document.activeElement;
        chkPref.checked = permite("preferencias");
        modal.hidden = false;
        document.body.style.overflow = "hidden";
        chkPref.focus();
    }

    function cerrarConfig(sinFoco) {
        if (!modal || modal.hidden) return;
        modal.hidden = true;
        document.body.style.overflow = "";
        if (!sinFoco && ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
    }

    function teclado(e) {
        if (!modal || modal.hidden) return;
        if (e.key === "Escape") { cerrarConfig(); return; }
        if (e.key !== "Tab") return;
        var f = Array.prototype.filter.call(modal.querySelectorAll("button, input, a[href]"), function (n) { return !n.disabled; });
        var p = f[0], u = f[f.length - 1];
        if (e.shiftKey && document.activeElement === p) { e.preventDefault(); u.focus(); }
        else if (!e.shiftKey && document.activeElement === u) { e.preventDefault(); p.focus(); }
    }

    function iniciar() {
        construir();
        if (!estado) mostrarBanner(true);
    }
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
    else iniciar();

    window.DLConsent = { permite: permite, abrir: function () { if (modal) abrirConfig(); } };
})();
