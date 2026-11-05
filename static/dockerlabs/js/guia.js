/* Guía de ayuda de la home: botón "?" junto al filtro de dificultad.
   Abre un modal donde la ballena explica, paso a paso, qué es DockerLabs y cómo
   descargar y desplegar una máquina. Usa window.DLBallena (ballena.js). */
(function () {
    "use strict";
    var btn = document.getElementById("dl-ayuda-btn");
    var guia = document.getElementById("dl-guia");
    if (!btn || !guia) return;

    var ventana = guia.querySelector(".dl-guia-ventana");
    var panel = guia.querySelector(".dl-guia-panel");
    var pasos = Array.prototype.slice.call(guia.querySelectorAll(".dl-guia-paso"));
    var nEl = guia.querySelector(".dl-guia-n");
    var dots = guia.querySelector(".dl-guia-dots");
    var ant = guia.querySelector(".dl-guia-ant");
    var sig = guia.querySelector(".dl-guia-sig");
    var sigTxt = sig.querySelector("span");
    var reducir = window.matchMedia("(prefers-reduced-motion: reduce)");
    var ultimo = pasos.length - 1, actual = 0, abierta = false, focoPrevio = null, tCierre = 0;

    /* Primera visita: el botón late suavemente hasta que se abre la guía */
    try { if (!localStorage.getItem("dl-guia-vista")) btn.classList.add("dl-ayuda-nuevo"); } catch (e) { /* sin storage */ }

    /* Puntos de navegación */
    pasos.forEach(function (p, i) {
        var d = document.createElement("button");
        d.type = "button";
        d.className = "dl-guia-dot";
        d.setAttribute("aria-label", "Paso " + (i + 1) + ": " + p.querySelector("h2").textContent);
        d.addEventListener("click", function () { ir(i); });
        dots.appendChild(d);
    });
    var dotEls = dots.querySelectorAll(".dl-guia-dot");

    function ballena(paso) {
        var B = window.DLBallena;
        if (!B) return;
        B.decir(paso.getAttribute("data-dice") || "");
        switch (paso.getAttribute("data-estado")) {
            case "hola": B.momento("feliz", 1800); B.soplar(); break;
            case "feliz": B.momento("feliz", 1800); break;
            case "sopla": B.soplar(); break;
            case "teclea": B.momento("teclea", 2600); break;
        }
    }

    function ir(i) {
        if (typeof cerrarVisor === "function" && visor && !visor.hidden) { visor.classList.remove("abierto"); visor.hidden = true; }
        i = Math.max(0, Math.min(ultimo, i));
        var dir = i >= actual ? "entra-der" : "entra-izq";
        actual = i;
        pasos.forEach(function (p, k) { p.hidden = k !== i; });
        var p = pasos[i];
        p.classList.remove("entra-der", "entra-izq");
        if (!reducir.matches) { void p.offsetWidth; p.classList.add(dir); }
        nEl.textContent = i + 1;
        for (var k = 0; k < dotEls.length; k++) {
            if (k === i) dotEls[k].setAttribute("aria-current", "step");
            else dotEls[k].removeAttribute("aria-current");
        }
        ant.disabled = i === 0;
        sigTxt.textContent = i === ultimo ? "¡Entendido!" : "Siguiente";
        sig.classList.toggle("final", i === ultimo);
        panel.scrollTop = 0;
        if (abierta) ballena(p);
    }

    function abrir() {
        if (abierta) return;
        clearTimeout(tCierre);
        focoPrevio = document.activeElement;
        guia.hidden = false;
        document.documentElement.classList.add("dl-guia-sin-scroll");
        void guia.offsetWidth;
        guia.classList.add("abierta");
        abierta = true;
        btn.setAttribute("aria-expanded", "true");
        btn.classList.remove("dl-ayuda-nuevo");
        try { localStorage.setItem("dl-guia-vista", "1"); } catch (e) { /* sin storage */ }
        ir(actual);
        setTimeout(function () { sig.focus(); }, reducir.matches ? 0 : 120);
    }

    function cerrar() {
        if (!abierta) return;
        if (visor && !visor.hidden) { visor.classList.remove("abierto"); visor.hidden = true; }
        abierta = false;
        guia.classList.remove("abierta");
        btn.setAttribute("aria-expanded", "false");
        document.documentElement.classList.remove("dl-guia-sin-scroll");
        tCierre = setTimeout(function () { guia.hidden = true; }, reducir.matches ? 0 : 280);
        if (focoPrevio && focoPrevio.focus) focoPrevio.focus();
    }

    btn.addEventListener("click", abrir);
    guia.addEventListener("click", function (e) {
        if (e.target.closest("[data-cerrar]")) cerrar();
    });
    ant.addEventListener("click", function () { ir(actual - 1); });
    sig.addEventListener("click", function () {
        if (actual === ultimo) cerrar(); else ir(actual + 1);
    });

    /* Capturas: se amplían dentro del propio modal */
    var visor = guia.querySelector(".dl-guia-visor");
    var visorImg = visor ? visor.querySelector("img") : null;
    var visorTxt = visor ? visor.querySelector(".dl-guia-visor-txt") : null;
    var visorCerrar = visor ? visor.querySelector(".dl-guia-visor-cerrar") : null;
    var visorOrigen = null, tVisor = 0;
    function visorAbierto() { return !!visor && !visor.hidden; }
    function abrirVisor(b) {
        var img = b.querySelector("img"), cap = b.closest("figure").querySelector("figcaption");
        clearTimeout(tVisor);
        visorOrigen = b;
        visorImg.style.width = "";
        visorImg.src = img.currentSrc || img.src;
        visorImg.alt = img.alt;
        visorTxt.innerHTML = cap ? cap.innerHTML : "";
        visor.hidden = false;
        // Ampliar de verdad: hasta el doble del tamaño real, sin salirse del hueco disponible
        var ajusta = function () {
            var nw = visorImg.naturalWidth, nh = visorImg.naturalHeight;
            if (!nw || !nh) return;
            var cs = getComputedStyle(visor);
            var aw = visor.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
            var ah = visor.clientHeight - parseFloat(cs.paddingTop) - parseFloat(cs.paddingBottom) - visorTxt.offsetHeight - 14;
            var k = Math.min(2, aw / nw, ah / nh);
            visorImg.style.width = Math.max(1, Math.floor(nw * k)) + "px";
        };
        if (visorImg.complete) ajusta(); else visorImg.onload = ajusta;
        void visor.offsetWidth;
        visor.classList.add("abierto");
        visorCerrar.focus();
    }
    function cerrarVisor() {
        if (!visorAbierto()) return;
        visor.classList.remove("abierto");
        tVisor = setTimeout(function () { visor.hidden = true; }, reducir.matches ? 0 : 200);
        if (visorOrigen) visorOrigen.focus();
    }
    if (visor) {
        guia.querySelectorAll(".dl-guia-zoom-btn").forEach(function (b) {
            b.addEventListener("click", function () { abrirVisor(b); });
        });
        visor.addEventListener("click", cerrarVisor);
    }

    /* Teclado: Esc cierra, flechas navegan, Tab se queda dentro del modal */
    document.addEventListener("keydown", function (e) {
        if (!abierta) return;
        if (visorAbierto()) {
            if (e.key === "Escape") { e.preventDefault(); cerrarVisor(); }
            else if (e.key === "Tab") { e.preventDefault(); visorCerrar.focus(); }
            return;
        }
        if (e.key === "Escape") { e.preventDefault(); cerrar(); return; }
        if (e.key === "ArrowRight") { e.preventDefault(); ir(actual + 1); return; }
        if (e.key === "ArrowLeft") { e.preventDefault(); ir(actual - 1); return; }
        if (e.key === "Tab") {
            var f = Array.prototype.filter.call(
                ventana.querySelectorAll('button, a[href], [tabindex]:not([tabindex="-1"])'),
                function (el) { return !el.disabled && el.offsetParent !== null; });
            if (!f.length) return;
            var primero = f[0], fin = f[f.length - 1];
            if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); fin.focus(); }
            else if (!e.shiftKey && document.activeElement === fin) { e.preventDefault(); primero.focus(); }
            else if (!ventana.contains(document.activeElement)) { e.preventDefault(); primero.focus(); }
        }
    });

    /* Deslizar con el dedo para cambiar de paso */
    var x0 = null, y0 = null;
    panel.addEventListener("touchstart", function (e) { x0 = e.touches[0].clientX; y0 = e.touches[0].clientY; }, { passive: true });
    panel.addEventListener("touchend", function (e) {
        if (x0 === null) return;
        var dx = e.changedTouches[0].clientX - x0, dy = e.changedTouches[0].clientY - y0;
        if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5) ir(actual + (dx < 0 ? 1 : -1));
        x0 = y0 = null;
    }, { passive: true });

    /* Copiar comandos */
    guia.querySelectorAll(".dl-guia-copiar").forEach(function (b) {
        b.addEventListener("click", function () {
            var texto = b.getAttribute("data-copy") || "";
            var ok = function () {
                b.classList.add("copiado");
                b.setAttribute("aria-label", "Copiado");
                if (window.DLBallena) window.DLBallena.momento("feliz", 900);
                setTimeout(function () { b.classList.remove("copiado"); b.setAttribute("aria-label", "Copiar comando"); }, 1600);
            };
            if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(texto).then(ok, function () {});
        });
    });

    /* Último paso: llevar directamente a las máquinas Muy fácil */
    var cta = guia.querySelector('[data-accion="muyfacil"]');
    if (cta) {
        cta.addEventListener("click", function () {
            cerrar();
            if (typeof window.botonmuyfacil === "function") {
                window.botonmuyfacil();
                if (typeof window.setFiltroLabel === "function") window.setFiltroLabel("Muy Fácil", "var(--accent-cyan)");
            }
            window.scrollTo({ top: 0, behavior: reducir.matches ? "auto" : "smooth" });
        });
    }
})();
