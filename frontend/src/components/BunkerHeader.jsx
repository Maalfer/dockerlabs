import React, { useState, useRef, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useBunkerSession } from './BunkerLayout'

export default function BunkerHeader() {
    const sess = useBunkerSession()
    const [dropdownOpen, setDropdownOpen] = useState(false)
    const ddRef = useRef(null)
    const navigate = useNavigate()
    const [logoText, setLogoText] = useState('BunkerLabs')

    useEffect(() => {
        const handler = (e) => { if (ddRef.current && !ddRef.current.contains(e.target)) setDropdownOpen(false) }
        document.addEventListener('mousedown', handler)
        return () => document.removeEventListener('mousedown', handler)
    }, [])

    const handleLogout = async (e) => {
        e.preventDefault()
        await fetch('/bunkerlabs/api/logout', { method: 'POST', credentials: 'include' })
        // We might need to refresh session here or rely on navigation
        if (sess.refresh) sess.refresh()
        navigate('/bunkerlabs/login')
        setDropdownOpen(false)
    }

    const handleGoLogin = (e) => {
        e.preventDefault()
        setDropdownOpen(false)
        navigate('/bunkerlabs/login')
    }

    const handleLogoMouseEnter = () => {
        if (window.innerWidth > 768) setLogoText('DockerLabs')
    }
    const handleLogoMouseLeave = () => {
        if (window.innerWidth > 768) setLogoText('BunkerLabs')
    }

    return (
        <header>
            <div className="logo">
                <Link to="/bunkerlabs" className="logo-container" aria-label="Ir a BunkerLabs">
                    <img src="/static/dockerlabs/images/logos/logo.png" alt="Logo" />
                </Link>
                <span
                    className="logo-text"
                    role="link"
                    tabIndex={0}
                    onMouseEnter={handleLogoMouseEnter}
                    onMouseLeave={handleLogoMouseLeave}
                    onClick={() => navigate('/')}
                    onKeyDown={(e) => {
                        if (e.key === 'Enter') navigate('/')
                    }}
                >
                    {logoText}
                </span>
            </div>

            <div className="nav-actions">
                <div className={`user-dropdown ${dropdownOpen ? 'active' : ''}`} ref={ddRef}>
                    <div className={`user-pill ${sess.nombre ? '' : 'user-pill-anon'}`} onClick={() => setDropdownOpen(!dropdownOpen)}>
                        <i className={sess.nombre ? 'bi bi-person-badge' : 'bi bi-shield-lock'}></i>
                        <span>{sess.nombre || 'Acceso Token'}</span>
                        <i className="bi bi-chevron-down" style={{ fontSize: '0.7rem', marginLeft: '0.3rem' }}></i>
                    </div>
                    <div className="dropdown-menu">
                        <a href="#" onClick={handleGoLogin} className="dropdown-item">
                            <i className="bi bi-key"></i>
                            Iniciar sesión / Cambiar PIN
                        </a>
                        <a href="#" onClick={handleLogout} className="dropdown-item">
                            <i className="bi bi-box-arrow-right"></i>
                            Cerrar sesión de BunkerLabs
                        </a>
                    </div>
                </div>
            </div>
        </header>
    )
}
