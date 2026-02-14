import React, { useState, useEffect, useRef, createContext, useContext } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import './BunkerLayout.css'

const BunkerSessionCtx = createContext({
    logged_in: false, nombre: null, is_guest: false, is_admin: false,
    docker_logged_in: false, csrf_token: '', refresh: () => { }
})

export function useBunkerSession() { return useContext(BunkerSessionCtx) }

export default function BunkerLayout({ children }) {
    const [sess, setSess] = useState({ logged_in: false, nombre: null, is_guest: false, is_admin: false, docker_logged_in: false, csrf_token: '' })
    const [dropdownOpen, setDropdownOpen] = useState(false)
    const ddRef = useRef(null)
    const navigate = useNavigate()

    const fetchSession = () => {
        fetch('/bunkerlabs/api/session', { credentials: 'include' })
            .then(r => r.ok ? r.json() : {})
            .then(d => setSess(prev => ({ ...prev, ...d })))
            .catch(() => { })
    }

    useEffect(() => { fetchSession() }, [])

    useEffect(() => {
        const handler = (e) => { if (ddRef.current && !ddRef.current.contains(e.target)) setDropdownOpen(false) }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [])

    const handleLogout = async () => {
        await fetch('/bunkerlabs/api/logout', { method: 'POST', credentials: 'include' })
        setSess(prev => ({ ...prev, logged_in: false, nombre: null, is_guest: false }))
        navigate('/bunkerlabs/login')
    }

    const ctxValue = { ...sess, refresh: fetchSession }

    return (
        <BunkerSessionCtx.Provider value={ctxValue}>
            <div className="bunker-page">
                {/* HEADER */}
                <header className="bunker-header-bar">
                    <Link to="/bunkerlabs" className="bunker-logo-area">
                        <img src="/static/bunkerlabs/images/bunkerlabs.png" alt="BunkerLabs Logo" />
                        <span className="bunker-logo-text">BunkerLabs</span>
                    </Link>

                    <div style={{ display: 'flex', gap: '2rem', justifyContent: 'center' }}>
                        <Link to="/" style={{ color: 'var(--bunker-text-muted)', fontWeight: 500, fontSize: '0.95rem', padding: '0.5rem 1rem', borderRadius: 8 }}>
                            DockerLabs
                        </Link>
                    </div>

                    <div className="bunker-nav-actions">
                        {sess.logged_in ? (
                            <div className={`bunker-user-dropdown ${dropdownOpen ? 'active' : ''}`} ref={ddRef}>
                                <div className="bunker-user-pill" onClick={() => setDropdownOpen(!dropdownOpen)}>
                                    <i className="bi bi-person-circle"></i>
                                    <span>{sess.nombre || 'Usuario'}</span>
                                    <i className="bi bi-chevron-down" style={{ fontSize: '0.7rem' }}></i>
                                </div>
                                <div className="bunker-dropdown-menu">
                                    {sess.is_admin && (
                                        <Link to="/bunkerlabs/accesos" className="bunker-dropdown-item" onClick={() => setDropdownOpen(false)}>
                                            <i className="bi bi-gear"></i> Gestión Accesos
                                        </Link>
                                    )}
                                    <button className="bunker-dropdown-item" onClick={handleLogout}>
                                        <i className="bi bi-box-arrow-right"></i> Cerrar sesión
                                    </button>
                                </div>
                            </div>
                        ) : (
                            <Link to="/bunkerlabs/login" style={{
                                fontFamily: "'Fira Code', monospace", padding: '0.5rem 1.1rem', fontSize: '0.85rem',
                                borderRadius: 6, display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                                color: 'var(--bunker-primary-light)', border: '1px solid var(--bunker-primary)',
                                fontWeight: 600, letterSpacing: '0.5px', textDecoration: 'none',
                                transition: 'all 0.2s ease'
                            }}>
                                <i className="bi bi-box-arrow-in-right"></i> Acceder
                            </Link>
                        )}
                    </div>
                </header>

                {/* MAIN */}
                <main className="bunker-main-content">
                    {children}
                </main>

                {/* FOOTER */}
                <footer className="bunker-footer-bar">
                    <div className="bunker-footer-content">
                        <div className="bunker-footer-icons">
                            <a href="https://www.youtube.com/c/ElPinguinoDeMario" target="_blank" rel="noreferrer" className="bunker-footer-icon"><i className="bi bi-youtube"></i></a>
                            <a href="https://x.com/maboroshii_sec" target="_blank" rel="noreferrer" className="bunker-footer-icon"><i className="bi bi-twitter-x"></i></a>
                            <a href="https://github.com/maalfer" target="_blank" rel="noreferrer" className="bunker-footer-icon"><i className="bi bi-github"></i></a>
                            <a href="https://www.twitch.tv/maalfer" target="_blank" rel="noreferrer" className="bunker-footer-icon"><i className="bi bi-twitch"></i></a>
                            <a href="https://www.tiktok.com/@elpinguinodemario" target="_blank" rel="noreferrer" className="bunker-footer-icon"><i className="bi bi-tiktok"></i></a>
                        </div>
                        <div style={{ width: '40%', maxWidth: 250, height: 1, background: 'linear-gradient(90deg, transparent, var(--bunker-border-soft), transparent)', margin: '0.4rem auto' }}></div>
                        <p>© 2024 BunkerLabs. Todos los derechos reservados.</p>
                        <p>
                            <Link to="/terminos-condiciones" style={{ marginRight: '1rem' }}>Términos y Políticas</Link>
                            <Link to="/terminos-condiciones">Privacidad y Cookies</Link>
                        </p>
                    </div>
                </footer>
            </div>
        </BunkerSessionCtx.Provider>
    )
}
