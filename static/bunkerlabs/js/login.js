/* BunkerLabs · acceso: Cody explica qué es BunkerLabs y ayuda al usuario.
   Cody va en modo «guía» (ballena.js): este script le dicta qué decir, en mensajes
   cortos y separados (no todo de golpe).
   - Rota los mensajes mientras nadie escribe.
   - Reacciona a un error del servidor (contraseña incorrecta o vacía).
   - Evita el doble envío del formulario. */
(() => {
    'use strict';

    const form = document.getElementById('bk-form');
    if (!form) return;

    const cody = () => window.DLBallena;
    const campo = document.getElementById('password');
    const boton = document.getElementById('bk-enviar');
    const error = document.getElementById('bk-error');

    // El primero ya lo dice Cody al cargar (mensaje «idle» de la plantilla: laboratorios basados en
    // vulnerabilidades reales). La rotación sigue desde el segundo, uno cada vez.
    const MENSAJES = [
        'Además, se recrean laboratorios de las vulnerabilidades más críticas que se van detectando y de mayor impacto.',
        'Todo está pensado para que aprendas practicando en entornos que simulan escenarios realistas.',
        '¿Y en qué se diferencia de DockerLabs? En BunkerLabs no hay CTF: son sistemas que recrean vulnerabilidades del mundo real.',
        'No es para jugar, sino para entender cómo funciona el hacking de verdad.',
        'El acceso es exclusivo para alumnos de La Academia, del Máster en Hacking Ético y de otras instituciones.',
        'Si ya eres alumno, escribe la contraseña que te ha dado tu instructor.',
        '¿Aún no eres alumno? Echa un vistazo a La Academia y al Máster en Hacking Ético: los tienes justo debajo.',
        '¿Solo quieres echar un vistazo? Entra con el enlace que hay al final.',
    ];
    let siguiente = 0;
    let silencioHasta = 0;   // no pisar un mensaje importante (error, reacción) durante unos segundos

    function enCampo() {
        const a = document.activeElement;
        return !!a && !!a.closest && !!a.closest('.dl-campo-caja');
    }

    function rotar() {
        if (!cody() || document.hidden || enCampo() || Date.now() < silencioHasta) return;
        cody().decir(MENSAJES[siguiente % MENSAJES.length], 'Cody');
        siguiente++;
    }
    setInterval(rotar, 9000);

    // Error devuelto por el servidor: Cody se entristece y explica qué hacer.
    function mensajeParaError(texto) {
        if (/incorrecta|inactiva/i.test(texto)) return 'Esa contraseña no es correcta o está desactivada. Revísala o pídele otra a tu instructor. ¿Aún no eres alumno? Mira las formaciones de abajo.';
        if (/debes introducir/i.test(texto)) return 'Falta la contraseña. Te la da tu instructor.';
        return texto;
    }
    if (error) {
        campo.setAttribute('aria-invalid', 'true');
        setTimeout(() => {
            if (!cody()) return;
            cody().momento('triste', 2600);
            cody().decir(mensajeParaError(error.textContent.trim()), 'Cody');
            silencioHasta = Date.now() + 15000;
        }, 500);
        campo.addEventListener('input', () => campo.removeAttribute('aria-invalid'), { once: true });
    }

    // Un solo envío: el botón se bloquea y avisa (el formulario se envía igualmente).
    form.addEventListener('submit', () => {
        if (!boton) return;
        boton.disabled = true;
        const texto = boton.querySelector('span');
        if (texto) texto.textContent = 'Comprobando…';
    });
    // Si el navegador restaura la página desde la caché (botón «atrás»), el botón vuelve a estar activo.
    window.addEventListener('pageshow', (e) => {
        if (!e.persisted || !boton) return;
        boton.disabled = false;
        const texto = boton.querySelector('span');
        if (texto) texto.textContent = 'Acceder';
    });
})();
