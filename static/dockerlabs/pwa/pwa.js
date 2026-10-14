/* Registro del service worker + utilidades PWA (instalación en Android, guía en iOS). */
(function () {
  'use strict';
  if ('serviceWorker' in navigator) {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(function () {});
    });
  }

  var standalone = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
  if (standalone) document.documentElement.classList.add('is-pwa');

  var DISMISS_KEY = 'dl-install-dismissed';
  function dismissed() { try { return Date.now() - Number(localStorage.getItem(DISMISS_KEY) || 0) < 14 * 864e5; } catch (e) { return false; } }
  function remember() { try { localStorage.setItem(DISMISS_KEY, String(Date.now())); } catch (e) {} }

  function banner(text, actionLabel, onAction) {
    if (standalone || dismissed() || document.getElementById('pwa-install')) return;
    var el = document.createElement('div');
    el.id = 'pwa-install';
    el.setAttribute('role', 'dialog');
    var p = document.createElement('span'); p.textContent = text; el.appendChild(p);
    if (actionLabel) {
      var b = document.createElement('button'); b.type = 'button'; b.textContent = actionLabel;
      b.addEventListener('click', function () { onAction(); el.remove(); });
      el.appendChild(b);
    }
    var x = document.createElement('button'); x.type = 'button'; x.className = 'pwa-x'; x.setAttribute('aria-label', 'Cerrar'); x.textContent = '×';
    x.addEventListener('click', function () { remember(); el.remove(); });
    el.appendChild(x);
    document.body.appendChild(el);
  }

  // Android / Chrome: prompt nativo diferido
  var deferred = null;
  window.addEventListener('beforeinstallprompt', function (e) {
    e.preventDefault(); deferred = e;
    setTimeout(function () {
      banner('Instala DockerLabs como app', 'Instalar', function () {
        deferred.prompt(); deferred.userChoice.finally(function () { remember(); deferred = null; });
      });
    }, 20000);
  });
  window.addEventListener('appinstalled', function () { remember(); var b = document.getElementById('pwa-install'); if (b) b.remove(); });

  // iOS Safari: no hay prompt, se explica el gesto
  var ua = navigator.userAgent;
  var isIOS = /iPad|iPhone|iPod/.test(ua) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
  var isSafari = /Safari/.test(ua) && !/CriOS|FxiOS|EdgiOS|OPiOS/.test(ua);
  if (isIOS && isSafari && !standalone) {
    setTimeout(function () {
      banner('Instala DockerLabs: pulsa Compartir y luego «Añadir a pantalla de inicio»');
    }, 20000);
  }
})();
