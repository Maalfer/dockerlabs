import React from 'react'
import { Link } from 'react-router-dom'
import './Footer.css'

export default function Footer(){
  return (
    <footer>
      <div className="footer-content">
        <p className="copyright"> <i className="bi bi-c-circle"/> Copyright DockerLabs · <Link to="/politica-privacidad">Política de Privacidad</Link> · <Link to="/politica-cookies">Cookies</Link> · <Link to="/condiciones-uso">Condiciones de Uso</Link></p>
        <div className="footer-icons">
          <a href="https://discord.gg/dD3yVejBUR" className="footer-icon" target="_blank" rel="noopener noreferrer"><i className="bi bi-discord"></i></a>
          <a href="https://es.linkedin.com/in/maalfer1" className="footer-icon" target="_blank" rel="noopener noreferrer"><i className="bi bi-linkedin"></i></a>
          <a href="https://t.me/elpinguinohack" className="footer-icon" target="_blank" rel="noopener noreferrer"><i className="bi bi-telegram"></i></a>
          <a href="https://github.com/Maalfer/dockerlabs" className="footer-icon support-tooltip" data-tooltip="¿Nos das una estrella?" target="_blank" rel="noopener noreferrer" aria-label="GitHub"><i className="bi bi-github github-pulse"></i></a>
        </div>
        <p><a href="https://www.youtube.com/@ElPinguinoDeMario" className="footer-link" target="_blank">By El Pingüino de Mario 🐧</a></p>
      </div>
      <div className="wave-container"><div className="wave wave1"></div><div className="wave wave2"></div></div>
    </footer>
  )
}
