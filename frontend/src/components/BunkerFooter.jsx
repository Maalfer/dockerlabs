import React from 'react'
import { Link } from 'react-router-dom'

export default function BunkerFooter() {
    return (
        <footer className="bunker-footer">
            <div className="footer-content">
                <p className="copyright">
                    <i className="bi bi-c-circle"></i> Copyright BunkerLabs ·
                    <Link to="/politica-privacidad" className="footer-link">Política de Privacidad</Link> ·
                    <Link to="/politica-cookies" className="footer-link">Cookies</Link> ·
                    <Link to="/condiciones-uso" className="footer-link">Condiciones de Uso</Link>
                </p>

                <div className="footer-icons">
                    <a href="https://discord.gg/dD3yVejBUR" className="footer-icon" target="_blank" rel="noreferrer"><i className="bi bi-discord"></i></a>
                    <a href="https://es.linkedin.com/in/maalfer1" className="footer-icon" target="_blank" rel="noreferrer"><i className="bi bi-linkedin"></i></a>
                    <a href="https://t.me/elpinguinohack" className="footer-icon" target="_blank" rel="noreferrer"><i className="bi bi-telegram"></i></a>
                </div>

                <p>
                    <a href="https://www.youtube.com/@ElPinguinoDeMario" className="footer-link" target="_blank" rel="noreferrer">
                        By El Pingüino de Mario 🐧
                    </a>
                </p>
            </div>

            <div className="wave-container">
                <div className="wave wave1"></div>
                <div className="wave wave2"></div>
            </div>
        </footer>
    )
}
