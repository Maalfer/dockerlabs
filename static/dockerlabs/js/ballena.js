/* Cody, la ballena de DockerLabs (login / registro / recuperar contraseña,
   páginas legales en modo lectura y guía de ayuda de la home).
   - Sigue el cursor con la mirada y parpadea.
   - Se tapa el ojo con la aleta al escribir la contraseña (y mira de reojo si la muestras).
   - Echa un chorrito de bits (ceros y unos) de vez en cuando, siempre al azar — nunca porque la toquen o le hagan clic.
   - Se pone triste si hay un error y contenta si todo sale bien.
   - De vez en cuando hace un gesto: saluda, da una voltereta, nada, curiosea o suelta candaditos.
   - Reacciona a lo que haces: asiente si el correo es válido, avisa del Bloq Mayús, niega si
     falta algo, se asombra si pegas texto, sospecha de los payloads, se deja acariciar,
     se duerme si no pasa nada… (ver «Reacciones»). Nunca mira ni comenta la contraseña.
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
    // Textos de las reacciones; cada página puede cambiarlos con `ballena_mensajes`.
    var M_BASE = {
        mayus: "¡Ojo! Tienes Bloq Mayús activado.",
        falta: "Te falta algo por rellenar.",
        correo: "Mmm… ese correo tiene pinta rara.",
        coinciden: "¡Coinciden! Y eso que no he mirado.",
        distintas: "Las dos contraseñas no coinciden.",
        pega: "Copiar y pegar: técnica ninja.",
        borra: "Borrón y cuenta nueva.",
        turbo: "¡Qué velocidad de teclado!",
        payload: "¿Un payload? Buen intento… aquí no cuela.",
        cody: "¡Anda, ese es mi nombre!",
        root: "¿root? Eso hay que ganárselo escalando.",
        vuelta: "¡Has vuelto! Te guardaba el sitio.",
        despierta: "¡Eh! No dormía… estaba compilando.",
        copia: "¡Copiado al portapapeles!",
        descarga: "¡Descargando! A desplegar se ha dicho.",
        // Al acariciarla no suelta "qué gustito": se pone en modo hermética y
        // bromea sobre no chivar el flag del CTF. Varias variantes al azar
        // (ver elegirVariante) para que no se repita siempre la misma.
        mimo: [
            "Mimos no son exploit: la flag sigue a salvo.",
            "Ni acariciándome entero te chivo la solución.",
            "Qué rico, pero el walkthrough te lo curras tú.",
            "Eso ha sonado a ingeniería social… y no cuela.",
            "Guardo el flag mejor que una contraseña en bcrypt.",
            "Sobornos de cariño: rechazados. El reto sigue en pie.",
            "Ni con mil mimos suelto el root de esta máquina.",
            "El write-up no se consigue a base de caricias.",
            "Me rindo a los mimos, pero el CTF no se rinde.",
            "Las cosquillas tampoco son un vector de ataque válido.",
            "Bonito intento, pero de mí no sale ni un spoiler.",
            "Enumera tú solito, que para algo está la máquina.",
            "Qué gustito… pero la respuesta sigue siendo confidencial.",
            "Ni torturándome a mimos canto la flag.",
            "Esto es ingeniería social con mano de cariño, y no pico.",
            "Puedes insistir: la flag sigue cifrada igual.",
            "Information disclosure: denegado, aunque insistas.",
            "Mi política de privacidad no incluye soltar el flag.",
            "Prueba con nmap, no con mimitos.",
            "Esto no es un CTF de «convence a la ballena».",
            "Ni sacando un 10 en caricias te doy pistas.",
            "Soy zero-knowledge: ni sabiendo la respuesta la digo.",
            "Need-to-know basis… y tú no la necesitas, pillín.",
            "Bruteforcea la máquina, no mi paciencia.",
            "Esto es un honeypot de mimos y no pienso caer.",
            "Mis labios están cifrados (bueno, no tengo labios, pero ya me entiendes).",
            "Dato confidencial, nivel alto secreto de ballena.",
            "Si quieres el write-up, pídeselo al profe, no a mí.",
            "Tengo un rate-limit para soltar flags: cero por segundo.",
            "Sigo air-gapped de soplar la respuesta.",
            "No hay keylogger que me saque el flag con mimos.",
            "Haz recon todo lo que quieras, en mí no hay flag.",
            "Tengo un NDA con el equipo de DockerLabs, lo siento.",
            "Esto parece un ataque de fuerza bruta… con ternura.",
            "Pivotea a otra máquina, que aquí no sueltas nada.",
            "El flag está mejor guardado que mi propia contraseña.",
            "Para sonsacarme hace falta un 0-day, no una caricia.",
            "Puedes hacerme OSINT entero: aquí no hay fugas.",
            "Ni Shodan me indexa los secretos, y tú tampoco los sacas.",
            "Vacíame la caché de mimos todo lo que quieras: el flag no se cachea ahí.",
            "Mi flag lleva salt y todo: ni a mimos se adivina.",
            "Para romper esto hace falta Hashcat, no cosquillas.",
            "Si vas a interceptarme con Burp, aviso: no hay request con la respuesta dentro.",
            "Abre Wireshark si quieres: en mis paquetes no va la respuesta.",
            "Ni con Metasploit consigues una sesión dentro de mi cabeza.",
            "John the Ripper se cansaría antes que yo de guardar el secreto.",
            "Por mucho que insistas, no hay overflow de información que valga.",
            "Ni una reverse shell te conecta con mis pensamientos.",
            "No llevo backdoor instalada, lo siento.",
            "Esto no pasaría ni la auditoría de seguridad más permisiva.",
            "Tengo un 2FA emocional, y un mimo no es factor suficiente.",
            "Para esto haría falta saltarse un WAF, y aquí no hay ninguno que saltar.",
            "El tailgating conmigo no cuela: aquí no hay puerta que colar.",
            "Soy una ballena: el anzuelo del phishing no me pica.",
            "No necesito sandbox: ya vivo encerrada con el secreto, y ahí se queda.",
            "El principio de mínimo privilegio también aplica a los mimos: tienes cero.",
            "Ni el mejor EDR detecta lo que no pienso compartir.",
            "El «first blood» te lo tienes que ganar tú solito.",
            "El scoreboard no sube a base de hacerme cariños, que lo sepas.",
            "Hoy ya repartí todas mis pistas, y ninguna era esta.",
            "Ni la categoría web, ni pwn, ni crypto: el secreto sigue siendo mío.",
            "Puedes hacer footprinting y whois todo el día: mi secreto no tiene registro público.",
            "Mi DNS no resuelve hacia la respuesta, por si lo estabas probando.",
            "Ghidra no desensambla secretos de ballena.",
            "Ni con GDB me pones un breakpoint en la boca.",
            "Ni con sqlmap me inyectas suficiente curiosidad.",
            "Hydra se quedaría sin diccionario antes de sacarme el flag.",
            "No hago commits de mi secreto ni en un repo privado tuyo.",
            "Ese pull request con la respuesta lo voy a rechazar siempre.",
            "Pregúntale al pato de goma, que a mí no me sacas nada.",
            "Esto no se arregla ni preguntándolo en Stack Overflow.",
            "Funciona en mi máquina, y en la tuya tampoco vas a tener el flag.",
            "No soy un CAPTCHA, pero tampoco te dejo pasar tan fácil.",
            "Mis aletas no tienen dedos para escribirte la respuesta, qué pena.",
            "Parpadeo en binario, pero ese código no es el flag.",
            "Puedo nadar lejos de esta conversación cuando quiera.",
            "Mi espiráculo suelta bits, no secretos.",
            "Puedes resolver la máquina entera, pero a mí no me vas a resolver con mimos.",
            "Esto se resiste más que un CVE sin parchear.",
            "El equipo del writeup no acepta colaboradores a base de mimos.",
            "Hoy no reparto hints, ni aunque sobornes con mimos todo el día.",
            "Puedes hacerme ingeniería inversa entera: no vas a encontrar el código fuente del secreto.",
            "Mi checksum no cuadra con el de «chivata», así que tranquilo.",
            "Aquí no hay privilege escalation que valga: sigo siendo yo quien decide.",
            "Puedes hacerme un pentest completo: el informe dirá «sin hallazgos dignos de un flag»."
        ],
        wii: "¡Wiii!",
        mareo: "¡Para, para, que me mareo!",
        rapido: "¡Eh, que no me da tiempo a resumir!"
    };
    for (var kM in M_BASE) { if (!M[kM]) M[kM] = M_BASE[kM]; }
    // Modo lectura (páginas largas): el bocadillo resume la sección que lees
    // y la pantalla del portátil enseña el porcentaje leído.
    var lectura = escena.hasAttribute("data-lectura");
    var lecturaBase = { t: M.idle || "Te lo resumo mientras lees." };
    // Modo guía (ayuda de la home): los textos los marca guia.js con window.DLBallena.
    var guia = escena.hasAttribute("data-guia");
    var guiaBase = { t: M.idle || "¡Hola! Soy Cody. ¿Te echo una aleta?" };
    var fijo = lectura || guia;

    /* ---------- Repertorio de frases ----------
       Viven en static/dockerlabs/data/frases.json (cada una con su categoría) y se
       cargan al iniciar. Si falla la carga, se usa este pequeño repertorio de reserva.
       Las que firma «Cody» se muestran como «Cody - <año>». */
    function hash(x) { var h = 5381; for (var i = 0; i < x.length; i++) h = ((h << 5) + h + x.charCodeAt(i)) | 0; return (h >>> 0).toString(36); }
    function prepara(l) { return l.map(function (f) { return { t: f.t, a: f.a || "Cody", c: f.c || "", id: hash(f.t) }; }); }
    var RESERVA = prepara([
        { t: "Paso a paso se llega a root.", c: "inicio" },
        { t: "Enumera, enumera… y vuelve a enumerar.", c: "tecnica" },
        { t: "Prueba, falla, aprende, repite. Eso es hacking.", c: "mentalidad" },
        { t: "Atascarse también es parte del camino.", c: "mentalidad" },
        { t: "Comparte lo que sabes: así crece la comunidad.", c: "comunidad" },
        { t: "Si funcionó a la primera, sospecha.", c: "humor" }
    ]);
    var FRASES = RESERVA;
    var CONTEXTOS = {}, PROB_PREF = 0.75;
    // Contexto de la página (login, registro, certificados…): decide qué categorías se prefieren.
    var contexto = escena.getAttribute("data-contexto") || "";
    var urlFrases = escena.getAttribute("data-frases") || "";
    // Historial entre páginas: no se repite una frase hasta haber visto muchas otras.
    var CLAVE_VISTAS = "dl-cody-vistas", vistas = [];
    // Solo se lee/escribe en el dispositivo si el usuario ha consentido las cookies de preferencias.
    function almacenOk() { return !!(window.DLConsent && window.DLConsent.permite("preferencias")); }
    try {
        if (almacenOk()) {
            var guardado = JSON.parse(localStorage.getItem(CLAVE_VISTAS) || "[]");
            if (Array.isArray(guardado)) vistas = guardado.filter(function (x) { return typeof x === "string"; });
        }
    } catch (e) { vistas = []; }
    function guardaVistas() { if (!almacenOk()) return; try { localStorage.setItem(CLAVE_VISTAS, JSON.stringify(vistas)); } catch (e) {} }
    window.addEventListener("dl-consent", guardaVistas);   // si acepta ahora, se empieza a recordar
    var fraseActual = null;
    function candidatas(cats) {
        return FRASES.filter(function (f) {
            return (!cats || cats.indexOf(f.c) >= 0) && vistas.indexOf(f.id) < 0 && !(fraseActual && fraseActual.id === f.id);
        });
    }
    function siguienteFrase() {
        var cats = CONTEXTOS[contexto] || null, pool = [];
        if (cats && cats.length && Math.random() < PROB_PREF) {
            // Las primeras categorías del contexto pesan más (r² sesga hacia el principio).
            var r = Math.random();
            pool = candidatas([cats[Math.floor(r * r * cats.length)]]);
            if (!pool.length) pool = candidatas(cats);
        }
        if (!pool.length) pool = candidatas(null);
        if (!pool.length) { vistas = []; pool = candidatas(null); }
        if (!pool.length) pool = FRASES;
        fraseActual = pool[Math.floor(Math.random() * pool.length)];
        vistas.push(fraseActual.id);
        var tope = Math.max(1, Math.floor(FRASES.length * 0.6));   // olvida las más antiguas
        if (vistas.length > tope) vistas = vistas.slice(vistas.length - tope);
        guardaVistas();
        return fraseActual;
    }
    function cargaFrases(alTerminar) {
        if (!urlFrases || !window.fetch) { alTerminar(); return; }
        fetch(urlFrases, { credentials: "same-origin" })
            .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
            .then(function (d) {
                var l = d && Array.isArray(d.frases) ? d.frases.filter(function (f) { return f && typeof f.t === "string" && f.t; }) : [];
                if (l.length) {
                    FRASES = prepara(l);
                    if (d.contextos && typeof d.contextos === "object") CONTEXTOS = d.contextos;
                    if (typeof d.prefProb === "number") PROB_PREF = d.prefProb;
                }
            })
            .catch(function () {})
            .then(alTerminar);
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
        autor.textContent = quien ? "# " + (quien === "Cody" ? "Cody - " + new Date().getFullYear() : quien) : "";
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
    // Una reacción puede tener varias variantes (array): se elige una al azar,
    // sin repetir la última, para que no suene siempre a lo mismo.
    var ultimaVariante = {};
    function elegirVariante(clave, lista) {
        if (lista.length === 1) return lista[0];
        var i;
        do { i = Math.floor(Math.random() * lista.length); } while (i === ultimaVariante[clave]);
        ultimaVariante[clave] = i;
        return lista[i];
    }
    // Reacción puntual (contraseña, error...). fijarMs: tiempo mínimo en pantalla.
    function decir(clave, fijarMs) {
        var t = M[clave];
        if (!t) return;
        if (Array.isArray(t)) t = elegirVariante(clave, t);
        var now = Date.now();
        if (!fijarMs && now < bloqueoHasta) return;
        if (fijarMs) bloqueoHasta = now + fijarMs;
        reaccion = true;
        pinta(t, "", true);
    }
    // Vuelve a la frase motivacional (respetando una reacción fijada).
    function fraseBase() { return lectura ? lecturaBase : (guia ? guiaBase : (fraseActual || RESERVA[0])); }
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

    // En las páginas con frases rotatorias esperamos (como mucho 1,2 s) al repertorio
    // para que la primera frase ya cuente con el historial y el contexto.
    var iniciada = false;
    function arranca() {
        if (iniciada) return;
        iniciada = true;
        if (!fijo) siguienteFrase();   // en lectura/guía el bocadillo fija otro texto: no gastar una frase
        pinta(fraseBase().t, fraseBase().a, true);
    }
    if (fijo) { arranca(); cargaFrases(function () {}); }
    else { setTimeout(arranca, 1200); cargaFrases(arranca); }
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
    function soplar() { if (!reducir.matches && !svg.classList.contains("duerme")) momento("sopla", 2400); }

    /* ---------- Gestos (clase temporal; la coreografía está en auth-ballena.css) ---------- */
    var GESTOS = { saluda: 2400, voltereta: 1500, nada: 2600, ladea: 2800, quiere: 2500 };
    var CALMADOS = ["saluda", "ladea", "quiere"]; // los que no distraen mientras se lee
    var OCUPADA = ["tapa", "reojo", "triste", "feliz", "teclea", "leyendo",
        "asiente", "niega", "asombro", "apuro", "sospecha", "mimo", "duerme"];
    var ultimoGesto = "", ultimaTecla = 0;
    function quitaGestos() {
        for (var g in GESTOS) { clearTimeout(timers[g]); svg.classList.remove(g); }
    }
    function gesto(nombre) {
        if (!GESTOS[nombre] || reducir.matches || svg.classList.contains("tapa") || svg.classList.contains("reojo")) return;
        quitaGestos();
        ultimoGesto = nombre;
        momento(nombre, GESTOS[nombre]);
    }
    function libre() {
        if (document.hidden || !svg.getClientRects().length || Date.now() - ultimaTecla < 4000) return false;
        for (var i = 0; i < OCUPADA.length; i++) { if (svg.classList.contains(OCUPADA[i])) return false; }
        for (var g in GESTOS) { if (svg.classList.contains(g)) return false; }
        return true;
    }
    function gestoAlAzar() {
        var lista = (lectura ? CALMADOS : Object.keys(GESTOS)).filter(function (g) { return g !== ultimoGesto; });
        gesto(lista[Math.floor(Math.random() * lista.length)]);
    }
    document.addEventListener("input", function () { ultimaTecla = Date.now(); }, true);

    /* ---------- Reacciones: expresiones breves y avisos en el bocadillo ---------- */
    var EXPRESIONES = { asiente: 900, niega: 700, asombro: 1300, apuro: 2200, sospecha: 2800 };
    var ultimaVez = {};
    // true si ha pasado `ms` desde la última vez (evita que una reacción se repita sin parar)
    function enfriado(clave, ms) {
        var a = Date.now();
        if (a - (ultimaVez[clave] || 0) < ms) return false;
        ultimaVez[clave] = a;
        return true;
    }
    function seVe() { return !document.hidden && svg.getClientRects().length > 0; }
    function expresion(nombre) {
        if (!EXPRESIONES[nombre] || !seVe() || svg.classList.contains("triste")) return false;
        // con el ojo tapado solo cabe el apuro (la gotita); el resto son gestos de la cara
        if (nombre !== "apuro" && (svg.classList.contains("tapa") || svg.classList.contains("reojo"))) return false;
        quitaGestos();
        for (var e in EXPRESIONES) { if (e !== nombre) { clearTimeout(timers[e]); svg.classList.remove(e); } }
        momento(nombre, EXPRESIONES[nombre]);
        return true;
    }
    // Aviso corto en el bocadillo; no pisa un mensaje fijado (error, éxito…) y luego vuelve a lo que había.
    function avisa(clave, ms) {
        if (!M[clave] || !seVe() || Date.now() < bloqueoHasta) return false;
        decir(clave, ms);
        setTimeout(function () { if (campoPw()) actualiza(); else volver(); }, ms + 60);
        return true;
    }

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
        if (pw) quitaGestos();
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

    /* ---------- Reacciones mientras escribes ---------- */
    var CORREO = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    var PAYLOAD = /('\s*(or|and)\s|'\s*(--|#|;)|\bor\s+1\s*=\s*1|\bunion\b.+\bselect\b|<\s*script|<\w+[^>]*\son\w+\s*=|\{\{.*\}\}|\$\{.*\}|\.\.[\/\\]|[;|&]\s*(ls|cat|id|whoami|sleep)\b)/i;
    var racha = [], borrados = 0, tCampo = 0, tPw = 0, visto = {}, coinciden = false, mayusOn = false;
    function enAuth(t) { return !!(t && t.closest && t.tagName === "INPUT" && t.closest(".dl-auth")); }
    function contrasenas(t) { return t.form ? t.form.querySelectorAll("input[data-pw]") : []; }
    // Al dejar de teclear un momento: ¿qué has escrito?
    function analiza(t) {
        var v = (t.value || "").trim(), min = v.toLowerCase(), clave = "";
        if (t.type === "email") {
            var ok = CORREO.test(v);
            if (ok && !t._codyOk) expresion("asiente");
            t._codyOk = ok;
            return;
        }
        if (PAYLOAD.test(v)) clave = "payload";
        else if (min === "cody") clave = "cody";
        else if (min === "root" || min === "admin" || min === "administrador" || min === "administrator") clave = "root";
        if (clave && t._codyClave !== clave) {
            if (clave === "payload") expresion("sospecha");
            else if (clave === "cody") gesto("quiere");
            else expresion("asombro");
            avisa(clave, 4000);
        }
        t._codyClave = clave;
    }
    // Contraseñas: solo se compara si las dos coinciden; nunca su contenido ni su longitud.
    function comparaPw(t) {
        var p = contrasenas(t);
        if (p.length !== 2 || !p[0].value || !p[1].value) { coinciden = false; return; }
        var igual = p[0].value === p[1].value;
        if (igual && !coinciden) avisa("coinciden", 3000);
        coinciden = igual;
    }
    document.addEventListener("input", function (e) {
        var t = e.target;
        if (!enAuth(t) || t.type === "checkbox" || t.type === "radio" || t.type === "hidden") return;
        if (t.hasAttribute("data-pw")) { clearTimeout(tPw); tPw = setTimeout(function () { comparaPw(t); }, 600); return; }
        var tipo = e.inputType || "", ahora = Date.now();
        if (tipo === "insertFromPaste" || tipo === "insertFromDrop") {
            if (enfriado("pega", 8000)) { expresion("asombro"); avisa("pega", 3000); }
        } else if (tipo.indexOf("delete") === 0) {
            borrados++; racha = [];
            if ((borrados >= 6 || (borrados >= 3 && !t.value)) && enfriado("borra", 8000)) {
                borrados = 0; expresion("apuro"); avisa("borra", 2600);
            }
        } else {
            borrados = 0;
            racha.push(ahora);
            while (racha.length && ahora - racha[0] > 1500) racha.shift();
            if (racha.length >= 10) {           // unas 80 pulsaciones por minuto… por segundo y medio
                momento("turbo", 900);
                if (!visto.turbo) { visto.turbo = true; avisa("turbo", 2600); }
            }
        }
        clearTimeout(tCampo);
        tCampo = setTimeout(function () { analiza(t); }, 650);
    });
    // Casillas (aceptar condiciones…): asiente
    document.addEventListener("change", function (e) {
        var t = e.target;
        if (!enAuth(t) || t.type !== "checkbox" || !t.checked) return;
        expresion("asiente");
        if (t.name === "terms") avisa("terms", 3000);
    });
    // Primera vez que entras en un campo: una pista (textos «user» / «email» de la página)
    document.addEventListener("focusin", function (e) {
        var t = e.target;
        if (!enAuth(t) || t.hasAttribute("data-pw")) return;
        var clave = t.type === "email" ? "email" : (t.name === "username" ? "user" : "");
        if (clave && !visto[clave] && !t.value) { visto[clave] = true; avisa(clave, 3200); }
    });
    // Al salir de un campo: correo con mala pinta o contraseñas distintas
    document.addEventListener("focusout", function (e) {
        var t = e.target;
        if (!enAuth(t)) return;
        setTimeout(function () {
            if (t.type === "email" && t.value.trim() && !CORREO.test(t.value.trim())) {
                if (enfriado("correo", 5000)) { expresion("niega"); avisa("correo", 3500); }
            } else if (t.hasAttribute("data-pw")) {
                var p = contrasenas(t);
                if (p.length === 2 && t === p[1] && p[0].value && p[1].value && p[0].value !== p[1].value &&
                    !campoPw() && enfriado("distintas", 5000)) { expresion("apuro"); avisa("distintas", 4000); }
            }
        }, 40);
    });
    // Bloq Mayús en la contraseña: avisa en cuanto lo detecta
    function mayus(e) {
        var t = e.target;
        if (!enAuth(t) || !t.hasAttribute("data-pw") || !e.getModifierState) return;
        var on = e.getModifierState("CapsLock");
        if (on && !mayusOn && enfriado("mayus", 5000)) { expresion("apuro"); avisa("mayus", 4000); }
        mayusOn = on;
    }
    document.addEventListener("keydown", mayus, true);
    document.addEventListener("keyup", mayus, true);
    // Intentas enviar y falta algo obligatorio: «no, no»
    document.addEventListener("invalid", function (e) {
        if (!enAuth(e.target)) return;
        if (enfriado("falta", 2500)) { expresion("niega"); avisa("falta", 3200); }
    }, true);

    /* ---------- Reacciones al ratón ---------- */
    // Acariciarla: se pone contenta y, si sigues, suelta candaditos
    var tMimo = 0, caricia = 0, ux = 0, uy = 0;
    svg.addEventListener("pointerenter", function (e) {
        if (e.pointerType !== "mouse") return;
        caricia = 0; ux = e.clientX; uy = e.clientY;
        clearTimeout(tMimo);
        tMimo = setTimeout(function () {
            if (!svg.classList.contains("tapa") && !svg.classList.contains("reojo") && !svg.classList.contains("triste")) svg.classList.add("mimo");
        }, 350);
    });
    svg.addEventListener("pointermove", function (e) {
        if (!svg.classList.contains("mimo")) return;
        caricia += Math.hypot(e.clientX - ux, e.clientY - uy); ux = e.clientX; uy = e.clientY;
        if (caricia > 420 && enfriado("mimo", 15000)) { caricia = 0; gesto("quiere"); avisa("mimo", 3000); }
    });
    svg.addEventListener("pointerleave", function () { clearTimeout(tMimo); svg.classList.remove("mimo"); });

    /* ---------- La mano que acaricia ----------
       Sobre Cody el cursor se sustituye por una mano propia que sigue al ratón:
       se inclina hacia donde la mueves, se mece mientras acaricias el cuerpo,
       deja candaditos por donde pasa, hace cosquillas en la cola y se aprieta
       al hacer clic. Solo con ratón; sin ella (táctil, movimiento reducido o
       sin JS) queda el cursor de mano fijo definido en auth-ballena.css. */
    (function () {
        if (reducir.matches || !window.matchMedia || !window.matchMedia("(hover: hover) and (pointer: fine)").matches) return;
        var DIBUJO = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"> <g> <g fill="#ffffff" stroke="#ffffff" stroke-width="4.2" stroke-linejoin="round" opacity=".55"> <rect x="8.2" y="6.2" width="4.6" height="13" rx="2.3"/> <rect x="12.6" y="3.4" width="4.8" height="15" rx="2.4"/> <rect x="17.2" y="4.4" width="4.8" height="14" rx="2.4"/> <rect x="21.6" y="7.6" width="4.4" height="11.4" rx="2.2"/> <path d="M9.4 17.4 C7 15.6 4.8 14.4 3.6 15.6 C2.4 16.9 4 19.2 6.4 21.4 L9.6 24.2 Z"/> <rect x="7.6" y="14.2" width="18.6" height="14.6" rx="7"/> </g> <g fill="#0a1630" stroke="#0a1630" stroke-width="2.6" stroke-linejoin="round"> <rect x="8.2" y="6.2" width="4.6" height="13" rx="2.3"/> <rect x="12.6" y="3.4" width="4.8" height="15" rx="2.4"/> <rect x="17.2" y="4.4" width="4.8" height="14" rx="2.4"/> <rect x="21.6" y="7.6" width="4.4" height="11.4" rx="2.2"/> <path d="M9.4 17.4 C7 15.6 4.8 14.4 3.6 15.6 C2.4 16.9 4 19.2 6.4 21.4 L9.6 24.2 Z"/> <rect x="7.6" y="14.2" width="18.6" height="14.6" rx="7"/> </g> <g fill="#fff6e6"> <rect x="8.2" y="6.2" width="4.6" height="13" rx="2.3"/> <rect x="12.6" y="3.4" width="4.8" height="15" rx="2.4"/> <rect x="17.2" y="4.4" width="4.8" height="14" rx="2.4"/> <rect x="21.6" y="7.6" width="4.4" height="11.4" rx="2.2"/> <path d="M9.4 17.4 C7 15.6 4.8 14.4 3.6 15.6 C2.4 16.9 4 19.2 6.4 21.4 L9.6 24.2 Z"/> <rect x="7.6" y="14.2" width="18.6" height="14.6" rx="7"/> </g> <path d="M8.6 23.6 C11.4 27.4 20.8 28 25 23.8 C23.6 27.6 19.2 28.8 16 28.8 C12.6 28.8 9.6 27.2 8.6 23.6 Z" fill="#f3cfa3"/> <path d="M12.7 15 V18.4 M17.3 14.6 V18.2 M21.8 15.2 V18.4" fill="none" stroke="#e0b98a" stroke-width=".9" stroke-linecap="round"/> <path d="M14.2 5.4 V8.6 M9.8 8.2 V10.8" fill="none" stroke="#ffffff" stroke-width="1.1" stroke-linecap="round" opacity=".95"/> </g> </svg>';
        // Candado (no corazón): guiño a la ciberseguridad mientras se la acaricia.
        var CANDADO = '<svg viewBox="-6 -7 12 13" xmlns="http://www.w3.org/2000/svg">' +
            '<path d="M-2.6 -1.2 V-3 a2.6 2.6 0 0 1 5.2 0 V-1.2" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>' +
            '<rect x="-3.4" y="-1.2" width="6.8" height="5.6" rx="1.2" fill="currentColor"/>' +
            '<circle cx="0" cy=".6" r=".8" fill="#0a1630"/>' +
            '<rect x="-.35" y=".5" width=".7" height="1.6" rx=".35" fill="#0a1630"/>' +
            '</svg>';
        var mano = document.createElement("div");
        mano.className = "dl-mano";
        mano.setAttribute("aria-hidden", "true");
        mano.innerHTML = '<div class="dl-mano-giro"><div class="dl-mano-pose">' + DIBUJO + "</div></div>";
        document.body.appendChild(mano);
        var giro = mano.firstChild;
        var dentro = false, x = 0, y = 0, antX = 0, incl = 0, objetivo = 0, rafM = 0, tQuieta = 0;
        var tramo = 0, ultimoCandado = 0, zona = "", cosquillas = false, vivos = 0;

        // ¿Qué parte de Cody hay bajo la mano?
        function zonaDe(t) {
            if (!t || !t.closest) return "agua";
            if (t.closest(".b-cola")) return "cola";
            if (t.closest(".b-portatil")) return "portatil";
            if (t.closest(".b-flota")) return "cuerpo";
            return "agua";
        }
        function pintaGiro() {
            rafM = 0;
            incl += (objetivo - incl) * 0.22;
            giro.style.transform = "rotate(" + incl.toFixed(1) + "deg)";
            if (Math.abs(objetivo - incl) > 0.4) rafM = requestAnimationFrame(pintaGiro);
        }
        function candado() {
            if (vivos >= 7) return;
            var c = document.createElement("div");
            c.className = "dl-mano-candado";
            c.innerHTML = CANDADO;
            c.style.left = (x + (Math.random() * 14 - 7)) + "px";
            c.style.top = (y - 12) + "px";
            c.style.setProperty("--dx", (Math.random() * 26 - 13).toFixed(0) + "px");
            c.style.setProperty("--r", (Math.random() * 40 - 20).toFixed(0) + "deg");
            c.style.color = Math.random() < 0.5 ? "#3cff00" : "#22d3ee";
            document.body.appendChild(c);
            vivos++;
            setTimeout(function () { c.remove(); vivos--; }, 1000);
        }
        function entra() {
            dentro = true; tramo = 0;
            svg.classList.add("con-mano");
            mano.classList.add("visible");
        }
        function sale() {
            if (!dentro) return;
            dentro = false; zona = "";
            svg.classList.remove("con-mano");
            mano.className = "dl-mano";
            if (cosquillas) { svg.classList.remove("ilusion"); cosquillas = false; }
            objetivo = 0; incl = 0; giro.style.transform = "";
            clearTimeout(tQuieta);
        }
        svg.addEventListener("pointermove", function (e) {
            if (e.pointerType !== "mouse") return;
            if (!dentro) { entra(); antX = e.clientX; }
            x = e.clientX; y = e.clientY;
            mano.style.transform = "translate3d(" + x + "px," + y + "px,0)";

            // inclinación: la muñeca se queda atrás respecto al movimiento
            var dx = x - antX; antX = x;
            objetivo = Math.max(-26, Math.min(26, dx * 1.8));
            if (!rafM) rafM = requestAnimationFrame(pintaGiro);

            var z = zonaDe(e.target);
            if (z !== zona) {
                zona = z;
                mano.classList.toggle("zona-agua", z === "agua");
                var haceCosquillas = z === "cola" && !svg.classList.contains("duerme");
                if (haceCosquillas !== cosquillas) { svg.classList.toggle("ilusion", haceCosquillas); cosquillas = haceCosquillas; }
            }
            // sobre el cuerpo o la cola, mover la mano es acariciar
            var acaricia = (z === "cuerpo" || z === "cola") && Math.abs(dx) + Math.abs(e.movementY || 0) > 0.5;
            if (acaricia) {
                mano.classList.add("acaricia");
                tramo += Math.abs(dx) + Math.abs(e.movementY || 0);
                var ahora = Date.now();
                if (tramo > 95 && ahora - ultimoCandado > 240 && !svg.classList.contains("triste")) { tramo = 0; ultimoCandado = ahora; candado(); }
            }
            clearTimeout(tQuieta);
            tQuieta = setTimeout(function () {       // se queda quieta: vuelve a la postura neutra
                objetivo = 0; mano.classList.remove("acaricia");
                if (!rafM) rafM = requestAnimationFrame(pintaGiro);
            }, 140);
        });
        svg.addEventListener("pointerleave", sale);
        svg.addEventListener("pointerdown", function (e) { if (e.pointerType === "mouse") mano.classList.add("pulsa"); });
        window.addEventListener("pointerup", function () { mano.classList.remove("pulsa"); });
        // si la página se mueve bajo el ratón (scroll) o se pierde el foco, la mano no debe quedarse flotando
        window.addEventListener("scroll", sale, { passive: true });
        window.addEventListener("blur", sale);
        document.addEventListener("visibilitychange", function () { if (document.hidden) sale(); });
    })();
    // Vas hacia el botón de enviar o de descarga: mueve la cola de ilusión
    document.querySelectorAll('.dl-auth button[type="submit"], .dl-guia-cta').forEach(function (b) {
        b.addEventListener("pointerenter", function (e) { if (e.pointerType === "mouse") svg.classList.add("ilusion"); });
        b.addEventListener("pointerleave", function () { svg.classList.remove("ilusion"); });
        b.addEventListener("click", function () { svg.classList.remove("ilusion"); });
    });

    /* ---------- Reacciones a otras acciones ---------- */
    document.addEventListener("copy", function (e) {
        var t = e.target;
        if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA")) return;
        if (seVe() && enfriado("copia", 4000)) { momento("feliz", 900); avisa("copia", 2500); }
    });
    document.addEventListener("click", function (e) {
        var a = e.target && e.target.closest ? e.target.closest("a[download]") : null;
        if (!a || !seVe() || !enfriado("descarga", 4000)) return;
        momento("feliz", 1500); gesto("nada"); avisa("descarga", 3500);
    });
    // Vuelves a la pestaña después de un rato: te saluda
    var ocultaDesde = 0;
    document.addEventListener("visibilitychange", function () {
        if (document.hidden) { ocultaDesde = Date.now(); return; }
        var fuera = ocultaDesde ? Date.now() - ocultaDesde : 0;
        ocultaDesde = 0;
        if (fuera > 20000) setTimeout(function () { if (libre()) { gesto("saluda"); avisa("vuelta", 3500); } }, 600);
    });

    /* ---------- Sueño: si no pasa nada en minuto y medio, se duerme; cualquier cosa la despierta ---------- */
    var tSueno = 0, ultimaActividad = 0, SUENO = 90000;
    function dormir() {
        clearTimeout(tSueno);
        if (libre() && !campoPw()) svg.classList.add("duerme");
        else tSueno = setTimeout(dormir, 15000);
    }
    function actividad() {
        var a = Date.now(), dormida = svg.classList.contains("duerme");
        if (!dormida && a - ultimaActividad < 500) return;
        ultimaActividad = a;
        if (dormida) {
            svg.classList.remove("duerme");
            if (expresion("asombro")) avisa("despierta", 3000);
        }
        clearTimeout(tSueno);
        tSueno = setTimeout(dormir, SUENO);
    }
    if (!reducir.matches) {
        ["pointermove", "pointerdown", "keydown", "wheel", "touchstart"].forEach(function (ev) {
            document.addEventListener(ev, actividad, { passive: true, capture: true });
        });
        window.addEventListener("scroll", actividad, { passive: true });
        tSueno = setTimeout(dormir, SUENO);
    }

    /* ---------- Clic en la ballena: alegría y frase nueva (el chorro va aparte y al azar) ---------- */
    var clics = [];
    svg.addEventListener("click", function () {
        // Tres clics seguidos: voltereta. Seis: se marea.
        var ahora = Date.now();
        clics.push(ahora);
        clics = clics.filter(function (c) { return ahora - c < 1600; });
        if (clics.length >= 6) { clics = []; momento("apuro", EXPRESIONES.apuro); avisa("mareo", 3000); return; }
        if (clics.length === 3) { momento("feliz", 1500); gesto("voltereta"); avisa("wii", 1800); return; }
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

    /* ---------- Chorro de bits espontáneo (único disparador: nunca al tocarla) ----------
       De vez en cuando, sin avisar: primero pronto para presentarse y luego
       cada 9-18 s, siempre al azar. Nunca mientras duerme, se tapa el ojo o mira de
       reojo, y nunca como respuesta a un clic o una caricia. */
    if (!reducir.matches) {
        setTimeout(soplar, 1400);
        (function siguiente() {
            setTimeout(function () {
                if (!document.hidden && !svg.classList.contains("tapa") && !svg.classList.contains("reojo")) soplar();
                siguiente();
            }, 9000 + Math.random() * 9000);
        })();
    }

    /* ---------- Gestos espontáneos: saluda al llegar y luego uno al azar cada tanto ---------- */
    if (!reducir.matches) {
        setTimeout(function () { if (libre()) gesto("saluda"); }, 2600);
        (function otro() {
            setTimeout(function () {
                if (libre()) gestoAlAzar();
                otro();
            }, 14000 + Math.random() * 10000);
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
    function triste() { quitaGestos(); momento("triste", 2600); decir("error", 4000); setTimeout(volver, 4100); }
    function contenta() { momento("feliz", 2200); soplar(); gesto("quiere"); decir("ok", 600000); }
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
        var total = secciones.length, actual = -1, terminado = false, tLee = 0, rafL = 0, trazo = [];
        var pctEl = svg.querySelector(".b-pt-pct");
        var alScroll = function () {
            rafL = 0;
            var max = document.documentElement.scrollHeight - window.innerHeight;
            var pct = max > 0 ? Math.min(100, Math.round(window.scrollY / max * 100)) : 100;
            if (pctEl) pctEl.textContent = pct + "%";
            // ¿bajas (o subes) a toda pastilla? Más de dos pantallas y media en menos de medio segundo
            var ya = Date.now();
            while (trazo.length && ya - trazo[0][0] > 450) trazo.shift();
            trazo.push([ya, window.scrollY]);
            if (Math.abs(window.scrollY - trazo[0][1]) > window.innerHeight * 2.5 && enfriado("rapido", 25000)) {
                expresion("asombro"); avisa("rapido", 3000);
            }
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
        soplar: soplar,
        gesto: gesto,
        expresion: expresion,
        avisa: avisa
    };
})();
