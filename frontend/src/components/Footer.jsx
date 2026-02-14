import React from 'react'

export default function Footer(){
  return (
    <footer>
      <div className="footer-content">
        <p className="copyright"> <i className="bi bi-c-circle"/> Copyright DockerLabs · <a href="/politica_privacidad">Política de Privacidad</a> · <a href="/politica_cookies">Cookies</a> · <a href="/condiciones_uso">Condiciones de Uso</a></p>
        <div className="footer-icons">
          <a href="https://discord.gg/dD3yVejBUR" className="footer-icon" target="_blank"><i className="bi bi-discord"></i></a>
          <a href="https://es.linkedin.com/in/maalfer1" className="footer-icon" target="_blank"><i className="bi bi-linkedin"></i></a>
          <a href="https://t.me/elpinguinohack" className="footer-icon" target="_blank"><i className="bi bi-telegram"></i></a>
          <a href="https://github.com/Maalfer/dockerlabs" className="footer-icon" target="_blank"><i className="bi bi-github github-pulse"></i></a>
        </div>
        <p><a href="https://www.youtube.com/@ElPinguinoDeMario" className="footer-link" target="_blank">By El Pingüino de Mario 🐧</a></p>
      </div>
      <div className="wave-container"><div className="wave wave1"></div><div className="wave wave2"></div></div>
    </footer>
  )
}
