/* Cody, la ballena de DockerLabs (login / registro / recuperar contraseña,
   páginas legales en modo lectura y guía de ayuda de la home).
   - Sigue el cursor con la mirada y parpadea.
   - Se tapa el ojo con la aleta al escribir la contraseña (y mira de reojo si la muestras).
   - Echa un chorro de agua de vez en cuando y al hacerle clic.
   - Se pone triste si hay un error y contenta si todo sale bien.
   - El bocadillo muestra frases motivacionales que van rotando; solo las
     interrumpe para reaccionar (contraseña, error, enviando, éxito).
   Sin JavaScript los formularios funcionan igual; todo esto es decorativo. */
(function () {
    "use strict";
    var escena = document.querySelector(".dl-ballena");
    if (!escena) return;
    var svg = escena.querySelector(".ballena");
    var bocadillo = escena.querySelector(".dl-bocadillo");
    var txt = escena.querySelector(".dl-bocadillo-txt");
    var autor = escena.querySelector(".dl-bocadillo-autor");
    var otra = escena.querySelector(".dl-otra");
    var reducir = window.matchMedia("(prefers-reduced-motion: reduce)");
    var M = {};
    try { M = JSON.parse(escena.getAttribute("data-mensajes") || "{}"); } catch (e) { M = {}; }
    // Modo lectura (páginas largas): el bocadillo resume la sección que lees
    // y la pantalla del portátil enseña el porcentaje leído.
    var lectura = escena.hasAttribute("data-lectura");
    var lecturaBase = { t: M.idle || "Te lo resumo mientras lees." };
    // Modo guía (ayuda de la home): los textos los marca guia.js con window.DLBallena.
    var guia = escena.hasAttribute("data-guia");
    var guiaBase = { t: M.idle || "¡Hola! Soy Cody. ¿Te echo una aleta?" };
    var fijo = lectura || guia;

    /* ---------- Repertorio de frases (las que no tienen autor son de Cody) ---------- */
    var FRASES = [
        { t: "Paso a paso se llega a root.", a: "Cody" },
        { t: "Enumera, enumera… y vuelve a enumerar.", a: "Cody" },
        { t: "Si no encuentras la vulnerabilidad, aún no has enumerado lo suficiente.", a: "Cody" },
        { t: "Las flags no se encuentran: se ganan.", a: "Cody" },
        { t: "Atascarse también es parte del camino.", a: "Cody" },
        { t: "Prueba, falla, aprende, repite. Eso es hacking.", a: "Cody" },
        { t: "Detrás de cada shell hay horas de paciencia.", a: "Cody" },
        { t: "Tu mejor exploit es la constancia.", a: "Cody" },
        { t: "Nadie nace sabiendo escalar privilegios.", a: "Cody" },
        { t: "La curiosidad es la herramienta más potente de un hacker.", a: "Cody" },
        { t: "Rómpelo, entiéndelo y vuelve a romperlo.", a: "Cody" },
        { t: "Comparte lo que sabes: así crece la comunidad.", a: "Cody" },
        { t: "Si funcionó a la primera, sospecha.", a: "Cody" },
        { t: "¿Atascado? Respira, toma un café y vuelve a mirar los puertos.", a: "Cody" },
        { t: "Un buen writeup enseña más que mil flags.", a: "Cody" },
        { t: "Cada máquina que resuelves te hace un poco mejor que ayer.", a: "Cody" },
        { t: "Hoy es un gran día para aprender algo nuevo.", a: "Cody" },
        { t: "No compares tu capítulo 1 con el capítulo 20 de otro.", a: "Cody" },
        { t: "Lee el código fuente. Casi siempre hay pistas.", a: "Cody" },
        { t: "Los errores de hoy son los conocimientos de mañana.", a: "Cody" },
        { t: "Una pausa a tiempo también forma parte del pentest.", a: "Cody" },
        { t: "La práctica no hace al maestro: lo hace la práctica constante.", a: "Cody" },
        { t: "El que no se rinde, tarde o temprano consigue la shell.", a: "Cody" },
        { t: "Cada «Permission denied» es una invitación a seguir buscando.", a: "Cody" },
        { t: "Las ballenas también empezaron nadando en la orilla.", a: "Cody" },
        { t: "La seguridad es un proceso, no un producto.", a: "Bruce Schneier" },
        { t: "Los aficionados hackean sistemas; los profesionales hackean personas.", a: "Bruce Schneier" },
        { t: "Hablar es barato. Enséñame el código.", a: "Linus Torvalds" },
        { t: "La simplicidad es requisito previo para la fiabilidad.", a: "Edsger W. Dijkstra" },
        { t: "La única forma de hacer un gran trabajo es amar lo que haces.", a: "Steve Jobs" },
        { t: "Sigue hambriento, sigue alocado.", a: "Steve Jobs" },
        { t: "No he fracasado. He encontrado 10.000 formas que no funcionan.", a: "Thomas Edison" },
        { t: "El éxito es la suma de pequeños esfuerzos repetidos día tras día.", a: "Robert Collier" },
        { t: "Todo parece imposible hasta que se hace.", a: "Nelson Mandela" },
        { t: "El experto en cualquier cosa fue una vez un principiante.", a: "Helen Hayes" },
        { t: "Quien se atreve a enseñar nunca debe dejar de aprender.", a: "John Cotton Dana" },
        { t: "No es que tengamos poco tiempo, sino que perdemos mucho.", a: "Séneca" },
        { t: "Caer está permitido. ¡Levantarse es obligatorio!", a: "Proverbio ruso" },
        { t: "Gota a gota se llena el mar.", a: "Refrán popular" },
        { t: "El camino de mil millas comienza con un solo paso.", a: "Lao Tse" }
    ];
    var orden = [], pos = 0, fraseActual = null;
    function barajar() {
        orden = FRASES.map(function (_, i) { return i; });
        for (var i = orden.length - 1; i > 0; i--) {
            var j = Math.floor(Math.random() * (i + 1)), x = orden[i]; orden[i] = orden[j]; orden[j] = x;
        }
        pos = 0;
    }
    function siguienteFrase() {
        if (pos >= orden.length) barajar();
        fraseActual = FRASES[orden[pos++]];
        return fraseActual;
    }

    /* ---------- Bocadillo ---------- */
    // Bocadillo de terminal: "$ texto▌". Se escribe letra a letra; el resto del
    // texto ya ocupa su hueco (invisible) para que el bocadillo no cambie de tamaño.
    var mostrando = null, reaccion = false, bloqueoHasta = 0, tCambio = 0;
    txt.textContent = "";
    var elPrompt = document.createElement("span"); elPrompt.className = "dl-prompt"; elPrompt.textContent = "$";
    var elEscrito = document.createElement("span");
    var elCursor = document.createElement("span"); elCursor.className = "dl-cursor";
    var elResto = document.createElement("span"); elResto.className = "dl-resto";
    txt.appendChild(elPrompt); txt.appendChild(elEscrito); txt.appendChild(elCursor); txt.appendChild(elResto);
    function pinta(texto, quien, animar) {
        var clave = texto + "|" + (quien || "");
        if (clave === mostrando) return;
        mostrando = clave;
        clearTimeout(tCambio);
        autor.textContent = quien ? "# " + quien : "";
        autor.hidden = !quien;
        if (!animar || reducir.matches) {
            elEscrito.textContent = texto; elResto.textContent = "";
            autor.classList.remove("pendiente");
            return;
        }
        var chars = Array.from(texto), n = 0;
        autor.classList.add("pendiente");
        elEscrito.textContent = ""; elResto.textContent = texto;
        (function paso() {
            n++;
            elEscrito.textContent = chars.slice(0, n).join("");
            elResto.textContent = chars.slice(n).join("");
            if (n < chars.length) tCambio = setTimeout(paso, chars[n - 1] === " " ? 18 : 30);
            else autor.classList.remove("pendiente");
        })();
    }
    // Reacción puntual (contraseña, error...). fijarMs: tiempo mínimo en pantalla.
    function decir(clave, fijarMs) {
        var t = M[clave];
        if (!t) return;
        var now = Date.now();
        if (!fijarMs && now < bloqueoHasta) return;
        if (fijarMs) bloqueoHasta = now + fijarMs;
        reaccion = true;
        pinta(t, "", true);
    }
    // Vuelve a la frase motivacional (respetando una reacción fijada).
    function fraseBase() { return lectura ? lecturaBase : (guia ? guiaBase : fraseActual); }
    function volver() {
        var espera = bloqueoHasta - Date.now();
        if (espera > 0) { setTimeout(volver, espera + 30); return; }
        if (campoPw()) return;
        reaccion = false;
        pinta(fraseBase().t, fraseBase().a, true);
    }
    function nuevaFrase() {
        if (fijo) return;
        siguienteFrase();
        if (!reaccion) pinta(fraseActual.t, fraseActual.a, true);
    }

    siguienteFrase();
    pinta(fraseBase().t, fraseBase().a, true);
    if (otra && !fijo) {
        otra.hidden = false;
        otra.addEventListener("mousedown", function (e) { e.preventDefault(); });
        otra.addEventListener("click", function () {
            bloqueoHasta = 0; reaccion = false;
            siguienteFrase(); pinta(fraseActual.t, fraseActual.a, true);
            otra.classList.remove("gira"); void otra.offsetWidth; otra.classList.add("gira");
            reiniciaRotacion();
        });
    }
    // Rotación automática mientras nadie la está leyendo con prisa
    var tRot = 0;
    function reiniciaRotacion() {
        clearInterval(tRot);
        tRot = setInterval(function () {
            if (!document.hidden && !reaccion) nuevaFrase();
        }, 20000);
    }
    if (!fijo) reiniciaRotacion();

    /* ---------- Estados temporales ---------- */
    var timers = {};
    function momento(clase, ms) {
        svg.classList.remove(clase);
        void svg.getBoundingClientRect(); // reinicia la animación CSS
        svg.classList.add(clase);
        clearTimeout(timers[clase]);
        timers[clase] = setTimeout(function () { svg.classList.remove(clase); }, ms);
    }
    function soplar() { if (!reducir.matches) momento("sopla", 2100); }

    /* ---------- Botón ver / ocultar contraseña ---------- */
    var ICONO = '<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
        '<path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>' +
        '<path class="dl-tachado" d="M4 4l16 16"/></svg>';
    document.querySelectorAll('.dl-auth input[type="password"]').forEach(function (inp) {
        var caja = document.createElement("span");
        caja.className = "dl-campo-caja";
        inp.parentNode.insertBefore(caja, inp);
        caja.appendChild(inp);
        var b = document.createElement("button");
        b.type = "button";
        b.className = "dl-ojo";
        b.setAttribute("aria-pressed", "false");
        b.setAttribute("aria-label", "Mostrar contraseña");
        b.innerHTML = ICONO;
        caja.appendChild(b);
        b.addEventListener("mousedown", function (e) { e.preventDefault(); }); // no robar el foco
        b.addEventListener("click", function () {
            var ver = inp.type === "password";
            inp.type = ver ? "text" : "password";
            b.setAttribute("aria-pressed", ver ? "true" : "false");
            b.setAttribute("aria-label", ver ? "Ocultar contraseña" : "Mostrar contraseña");
            inp.focus();
            actualiza();
        });
        inp.setAttribute("data-pw", "");
    });

    /* ---------- Reacción al foco ---------- */
    function campoPw() {
        var a = document.activeElement;
        if (!a || !a.closest || !a.closest(".dl-auth")) return null;
        if (a.classList.contains("dl-ojo")) a = a.parentNode.querySelector("input");
        return a && a.hasAttribute("data-pw") ? a : null;
    }
    function actualiza() {
        var pw = campoPw();
        svg.classList.toggle("tapa", !!pw && pw.type === "password");
        svg.classList.toggle("reojo", !!pw && pw.type === "text");
        if (pw) decir(pw.type === "password" ? "pass" : "ver");
        else if (reaccion) volver();
    }
    document.addEventListener("focusin", actualiza);
    document.addEventListener("focusout", function () { setTimeout(actualiza, 0); });

    /* ---------- Mirada ---------- */
    var px = null, py = null, raf = 0;
    function mirarA(x, y) {
        if (svg.classList.contains("tapa") || svg.classList.contains("reojo")) return;
        var r = svg.getBoundingClientRect();
        var cx = r.left + r.width * 0.79, cy = r.top + r.height * 0.535; // posición del ojo
        var dx = x - cx, dy = y - cy, d = Math.hypot(dx, dy) || 1, k = Math.min(1, d / 220);
        svg.style.setProperty("--ox", (dx / d * 2.6 * k).toFixed(2) + "px");
        svg.style.setProperty("--oy", (dy / d * 2.4 * k).toFixed(2) + "px");
    }
    if (!reducir.matches) {
        document.addEventListener("pointermove", function (e) {
            px = e.clientX; py = e.clientY;
            if (!raf) raf = requestAnimationFrame(function () { raf = 0; mirarA(px, py); });
        }, { passive: true });
        // Mientras escribes en un campo de texto, mira hacia el campo
        document.addEventListener("input", function (e) {
            var t = e.target;
            if (!t || !t.closest || !t.closest(".dl-auth") || t.hasAttribute("data-pw")) return;
            momento("teclea", 650);
            var r = t.getBoundingClientRect();
            var frac = Math.min(1, (t.value || "").length / 22);
            mirarA(r.left + 16 + frac * (r.width - 32), r.top + r.height / 2);
        });
    }

    /* ---------- Clic en la ballena: chorro, alegría y frase nueva ---------- */
    svg.addEventListener("click", function () {
        soplar();
        momento("feliz", 1200);
        if (fijo) {
            // en lectura / guía: una frase motivacional de regalo y luego vuelve al resumen
            siguienteFrase(); reaccion = true; bloqueoHasta = Date.now() + 6000;
            pinta(fraseActual.t, fraseActual.a, true);
            setTimeout(volver, 6050);
        } else if (!campoPw()) {
            bloqueoHasta = 0; reaccion = false;
            siguienteFrase(); pinta(fraseActual.t, fraseActual.a, true);
            reiniciaRotacion();
        }
    });

    /* ---------- Chorro espontáneo ---------- */
    if (!reducir.matches) {
        setTimeout(soplar, 900);
        (function siguiente() {
            setTimeout(function () {
                if (!document.hidden && !svg.classList.contains("tapa")) soplar();
                siguiente();
            }, 7000 + Math.random() * 6000);
        })();
    }

    /* ---------- Errores y éxito (observa las alertas que ya pinta la página) ---------- */
    function visible(el) { return !!el && el.style.display !== "none" && el.offsetParent !== null; }
    function observar(id, fn) {
        var el = document.getElementById(id);
        if (!el) return;
        var antes = visible(el);
        new MutationObserver(function () {
            var ahora = visible(el);
            if (ahora && !antes) fn();
            antes = ahora;
        }).observe(el, { attributes: true, attributeFilter: ["style", "class"] });
    }
    function triste() { momento("triste", 2600); decir("error", 4000); setTimeout(volver, 4100); }
    function contenta() { momento("feliz", 2200); soplar(); decir("ok", 600000); }
    ["login-error", "register-error", "recover-error"].forEach(function (id) { observar(id, triste); });
    ["register-success", "register-pending", "recover-success"].forEach(function (id) { observar(id, contenta); });
    var aviso = document.getElementById("rl-warning");
    if (aviso && visible(aviso)) { decir("espera", 5000); setTimeout(volver, 5100); }

    document.querySelectorAll(".dl-auth form").forEach(function (f) {
        f.addEventListener("submit", function () { decir("envio", 1500); });
    });

    /* ---------- Modo lectura ---------- */
    if (lectura) {
        var secciones = Array.prototype.slice.call(document.querySelectorAll("[data-tldr]"));
        var total = secciones.length, actual = -1, terminado = false, tLee = 0, rafL = 0;
        var pctEl = svg.querySelector(".b-pt-pct");
        var alScroll = function () {
            rafL = 0;
            var max = document.documentElement.scrollHeight - window.innerHeight;
            var pct = max > 0 ? Math.min(100, Math.round(window.scrollY / max * 100)) : 100;
            if (pctEl) pctEl.textContent = pct + "%";
            if (window.scrollY > 0 && !svg.classList.contains("feliz")) {
                svg.classList.add("leyendo");
                clearTimeout(tLee);
                tLee = setTimeout(function () { svg.classList.remove("leyendo"); }, 1100);
            }
            // sección actual: la última cuyo título ya ha pasado por el 45 % de la pantalla
            var idx = -1, lim = window.innerHeight * 0.45;
            for (var i = 0; i < total; i++) { if (secciones[i].getBoundingClientRect().top < lim) idx = i; }
            if (idx !== actual) {
                actual = idx;
                lecturaBase = idx < 0 ? { t: M.idle || "Te lo resumo mientras lees." }
                    : { t: secciones[idx].getAttribute("data-tldr"), a: "resumen " + (idx + 1) + "/" + total };
                if (!reaccion) pinta(lecturaBase.t, lecturaBase.a, true);
            }
            if (!terminado && max > 40 && window.scrollY > 0 && pct >= 99) {
                terminado = true;
                clearTimeout(tLee); svg.classList.remove("leyendo");
                momento("feliz", 2600); soplar();
                decir("fin", 6000); setTimeout(volver, 6050);
            }
        };
        window.addEventListener("scroll", function () { if (!rafL) rafL = requestAnimationFrame(alScroll); }, { passive: true });
        window.addEventListener("resize", function () { if (!rafL) rafL = requestAnimationFrame(alScroll); });
        alScroll();
    }

    /* ---------- API para otros scripts (guía de ayuda) ---------- */
    window.DLBallena = {
        decir: function (texto, quien) {
            guiaBase = { t: texto, a: quien || "" };
            reaccion = false; bloqueoHasta = 0;
            pinta(guiaBase.t, guiaBase.a, true);
        },
        momento: momento,
        soplar: soplar
    };
})();
