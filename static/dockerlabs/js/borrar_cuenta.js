/* Eliminación de la propia cuenta (panel de usuario).
   Asistente de 3 pasos para evitar borrados accidentales:
     1) leer qué se borra y marcar 3 casillas,
     2) escribir usuario + frase exacta + contraseña,
     3) última advertencia con cuenta atrás de 8 s.
   El servidor revalida todo en POST /api/delete_account. */
(function () {
    "use strict";
    var modal = document.getElementById("borrarCuentaModal");
    var abrir = document.getElementById("btnAbrirBorrado");
    if (!modal || !abrir) return;

    var FRASE = "ELIMINAR MI CUENTA";
    var ESPERA = 8;                       // segundos antes de poder confirmar
    var usuario = modal.getAttribute("data-usuario") || "";
    var pasos = modal.querySelectorAll("[data-paso]");
    var indicador = document.getElementById("borrarIndicador");
    var titulo = document.querySelector("#borrarTitulo span");
    var checks = modal.querySelectorAll(".borrar-check");
    var sig1 = document.getElementById("borrarSiguiente1");
    var sig2 = document.getElementById("borrarSiguiente2");
    var inUsuario = document.getElementById("borrarUsuario");
    var inFrase = document.getElementById("borrarFrase");
    var inPass = document.getElementById("borrarPassword");
    var confirmar = document.getElementById("borrarConfirmar");
    var err2 = document.getElementById("borrarError");
    var err3 = document.getElementById("borrarError3");
    var cerrarX = document.getElementById("borrarCerrar");
    var ultimoFoco = null, tCuenta = 0, enviando = false, pasoActual = 1;

    document.getElementById("borrarUsuarioEsperado").textContent = usuario;
    document.getElementById("borrarUltimaUsuario").textContent = usuario;

    var TITULOS = { 1: "Eliminar tu cuenta", 2: "Confirma tu identidad", 3: "¿Seguro del todo?", 4: "Cuenta eliminada" };

    function mostrarPaso(n) {
        pasoActual = n;
        Array.prototype.forEach.call(pasos, function (p) { p.hidden = Number(p.getAttribute("data-paso")) !== n; });
        titulo.textContent = TITULOS[n];
        indicador.hidden = n === 4;
        indicador.textContent = "Paso " + n + " de 3";
        cerrarX.hidden = n === 4;
        clearInterval(tCuenta);
        if (n === 3) cuentaAtras();
        var foco = { 1: checks[0], 2: inUsuario, 3: modal.querySelector('[data-paso="3"] [data-cancelar]'), 4: null }[n];
        if (foco) foco.focus();
    }

    function cuentaAtras() {
        var resto = ESPERA;
        confirmar.disabled = true;
        confirmar.textContent = "Eliminar definitivamente (" + resto + ")";
        tCuenta = setInterval(function () {
            resto--;
            if (resto > 0) { confirmar.textContent = "Eliminar definitivamente (" + resto + ")"; return; }
            clearInterval(tCuenta);
            confirmar.disabled = false;
            confirmar.textContent = "Eliminar definitivamente";
        }, 1000);
    }

    function reiniciar() {
        clearInterval(tCuenta);
        Array.prototype.forEach.call(checks, function (c) { c.checked = false; });
        inUsuario.value = inFrase.value = inPass.value = "";
        sig1.disabled = sig2.disabled = true;
        err2.hidden = err3.hidden = true;
        enviando = false;
        confirmar.textContent = "Eliminar definitivamente";
    }

    function abrirModal() {
        ultimoFoco = document.activeElement;
        reiniciar();
        modal.classList.add("visible");
        modal.setAttribute("aria-hidden", "false");
        document.body.style.overflow = "hidden";
        mostrarPaso(1);
    }

    function cerrarModal() {
        if (enviando || pasoActual === 4) return;
        modal.classList.remove("visible");
        modal.setAttribute("aria-hidden", "true");
        document.body.style.overflow = "";
        reiniciar();                       // no se conserva la contraseña escrita
        if (ultimoFoco && ultimoFoco.focus) ultimoFoco.focus();
    }

    function validar1() {
        sig1.disabled = !Array.prototype.every.call(checks, function (c) { return c.checked; });
    }
    function validar2() {
        sig2.disabled = !(inUsuario.value === usuario && inFrase.value.trim().toUpperCase() === FRASE && inPass.value.length > 0);
    }

    function mostrarError(el, msg) { el.textContent = msg; el.hidden = false; }

    function eliminar() {
        if (enviando || confirmar.disabled) return;
        enviando = true;
        confirmar.disabled = true;
        confirmar.textContent = "Eliminando…";
        err3.hidden = true;
        var csrf = typeof getCsrfToken === "function" ? getCsrfToken() : "";
        fetch("/api/delete_account", {
            method: "POST",
            credentials: "same-origin",
            headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
            body: JSON.stringify({ password: inPass.value, username_confirm: inUsuario.value, phrase: inFrase.value })
        }).then(function (r) {
            return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, d: d }; });
        }).then(function (res) {
            if (res.ok && res.d.success) {
                inPass.value = "";
                mostrarPaso(4);
                setTimeout(function () { window.location.href = "/"; }, 6000);
                return;
            }
            enviando = false;
            // Fallo (p. ej. contraseña incorrecta): se vuelve al paso 2 con el motivo.
            mostrarPaso(2);
            mostrarError(err2, res.d.error || "No se pudo eliminar la cuenta.");
            inPass.value = ""; validar2(); inPass.focus();
        }).catch(function () {
            enviando = false;
            mostrarPaso(3);
            mostrarError(err3, "Error de conexión. No se ha borrado nada; inténtalo de nuevo.");
        });
    }

    abrir.addEventListener("click", abrirModal);
    cerrarX.addEventListener("click", cerrarModal);
    Array.prototype.forEach.call(modal.querySelectorAll("[data-cancelar]"), function (b) { b.addEventListener("click", cerrarModal); });
    // Clic fuera: cierra solo en los pasos 1 y 2 (en el 3 hay que decidirlo con el botón).
    modal.addEventListener("mousedown", function (e) { if (e.target === modal && pasoActual < 3) cerrarModal(); });
    Array.prototype.forEach.call(checks, function (c) { c.addEventListener("change", validar1); });
    [inUsuario, inFrase, inPass].forEach(function (i) {
        i.addEventListener("input", function () { err2.hidden = true; validar2(); });
        i.addEventListener("keydown", function (e) { if (e.key === "Enter") e.preventDefault(); });   // Enter nunca avanza
    });
    sig1.addEventListener("click", function () { if (!sig1.disabled) mostrarPaso(2); });
    document.getElementById("borrarAtras2").addEventListener("click", function () { mostrarPaso(1); });
    sig2.addEventListener("click", function () { if (!sig2.disabled) mostrarPaso(3); });
    document.getElementById("borrarAtras3").addEventListener("click", function () { if (!enviando) mostrarPaso(2); });
    confirmar.addEventListener("click", eliminar);

    document.addEventListener("keydown", function (e) {
        if (!modal.classList.contains("visible")) return;
        if (e.key === "Escape") { cerrarModal(); return; }
        if (e.key !== "Tab") return;                                  // trampa de foco dentro del diálogo
        var f = Array.prototype.filter.call(
            modal.querySelectorAll('button, input, a[href]'),
            function (el) { return !el.disabled && !el.closest("[hidden]") && el.offsetParent !== null; });
        if (!f.length) return;
        var primero = f[0], ultimo = f[f.length - 1];
        if (e.shiftKey && document.activeElement === primero) { e.preventDefault(); ultimo.focus(); }
        else if (!e.shiftKey && document.activeElement === ultimo) { e.preventDefault(); primero.focus(); }
    });
})();
