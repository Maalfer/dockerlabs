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
    }

    const handleLogoMouseEnter = () => {
        if (window.innerWidth > 768) setLogoText('DockerLabs')
    }
    const handleLogoMouseLeave = () => {
        if (window.innerWidth > 768) setLogoText('BunkerLabs')
    }

    return (
        <header>
            <Link to="/bunkerlabs" className="logo">
                <div className="logo-container">
                    <img src="/static/dockerlabs/images/logos/logo.png" alt="Logo" />
                </div>
                <Link to="/" id="bunkerlabs-link" className="logo-text"
                    onMouseEnter={handleLogoMouseEnter}
                    onMouseLeave={handleLogoMouseLeave}>
                    {logoText}
                </Link>
            </Link>

            <div className="nav-actions">
                {sess.nombre ? (
                    <div className={`user-dropdown ${dropdownOpen ? 'active' : ''}`} ref={ddRef}>
                        <div className="user-pill" onClick={() => setDropdownOpen(!dropdownOpen)}>
                            <i className="bi bi-person-badge"></i>
                            <span>{sess.nombre}</span>
                            <i className="bi bi-chevron-down" style={{ fontSize: '0.7rem', marginLeft: '0.3rem' }}></i>
                        </div>
                        <div className="dropdown-menu">
                            <a href="#" onClick={handleLogout} className="dropdown-item">
                                <i className="bi bi-box-arrow-right"></i>
                                Salir de BunkerLabs
                            </a>
                        </div>
                    </div>
                ) : (
                    <div className="user-pill user-pill-anon">
                        <i className="bi bi-shield-lock"></i>
                        <span>Acceso Token</span>
                    </div>
                )}
            </div>
        </header>
    )
}
