/* Soporte: botones «Copiar» (correo y comandos). Sin dependencias. */
(function () {
    "use strict";
    function copiar(texto) {
        if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(texto);
        return new Promise(function (ok, ko) {
            var t = document.createElement("textarea");
            t.value = texto; t.setAttribute("readonly", ""); t.style.position = "fixed"; t.style.opacity = "0";
            document.body.appendChild(t); t.select();
            try { document.execCommand("copy") ? ok() : ko(); } catch (e) { ko(e); } finally { document.body.removeChild(t); }
        });
    }
    document.addEventListener("click", function (e) {
        var b = e.target.closest && e.target.closest("[data-copiar]");
        if (!b) return;
        var etiqueta = b.querySelector("span"), icono = b.querySelector("i");
        copiar(b.getAttribute("data-copiar")).then(function () {
            b.classList.add("copiado");
            if (etiqueta) etiqueta.textContent = "¡Copiado!";
            if (icono) icono.className = "bi bi-check2";
        }).catch(function () {
            if (etiqueta) etiqueta.textContent = "Selecciona y copia";
        }).then(function () {
            setTimeout(function () {
                b.classList.remove("copiado");
                if (etiqueta) etiqueta.textContent = "Copiar";
                if (icono) icono.className = "bi bi-clipboard";
            }, 1800);
        });
    });
})();
