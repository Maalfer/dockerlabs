import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import BunkerLayout, { useBunkerSession } from '../components/BunkerLayout'
import './BunkerLoginPage.css'

function BunkerLoginContent() {
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [isFocused, setIsFocused] = useState(false)
    const navigate = useNavigate()
    const sess = useBunkerSession()

    useEffect(() => {
        if (sess.logged_in) navigate('/bunkerlabs')
    }, [sess.logged_in, navigate])

    const handleLogin = async (e) => {
        e.preventDefault()
        if (!password.trim()) return
        setError('')
        setLoading(true)

        try {
            // Get fresh CSRF token
            const csrfRes = await fetch('/api/csrf', { credentials: 'include' })
            const csrfData = await csrfRes.json()
            const token = csrfData.csrf_token || ''

            const res = await fetch('/bunkerlabs/api/login', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
                body: JSON.stringify({ password: password.trim() })
            })
            const data = await res.json()

            if (res.ok && data.success) {
                sess.refresh()
                navigate('/bunkerlabs')
            } else {
                setError(data.error || 'Error al iniciar sesión')
            }
        } catch {
            setError('Error de conexión')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="bunker-container">
            <div className={`bunker-box ${isFocused ? 'input-focused' : ''}`}>
                {/* Columna Izquierda: Login */}
                <div className="login-section">
                    <div className="bunker-header">
                        <div className="bunker-icon">
                            <i className="bi bi-shield-lock"></i>
                        </div>
                        <h2>Acceso BunkerLabs</h2>
                        <p className="bunker-subtitle">Área restringida - Acceso autorizado</p>
                    </div>

                    {error && (
                        <div className="alert alert-danger bunker-alert">
                            <i className="bi bi-exclamation-triangle"></i>
                            {error}
                        </div>
                    )}

                    <form onSubmit={handleLogin} className="bunker-form">
                        <div className="form-group">
                            <label htmlFor="password" className="bunker-label">
                                <i className="bi bi-key"></i>
                                Contraseña de acceso
                            </label>
                            <input
                                type="password"
                                id="password"
                                name="password"
                                className="bunker-input"
                                required
                                placeholder="Ingresa la contraseña de BunkerLabs"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                onFocus={() => setIsFocused(true)}
                                onBlur={() => setIsFocused(false)}
                                disabled={loading}
                            />
                        </div>

                        <button type="submit" className="bunker-btn" disabled={loading}>
                            <i className="bi bi-door-open"></i>
                            {loading ? 'Accediendo...' : 'Acceder a BunkerLabs'}
                        </button>
                    </form>

                    <div className="bunker-footer">
                        <p className="bunker-warning" style={{ fontSize: '0.9rem', lineHeight: 1.5 }}>
                            <i className="bi bi-info-circle"></i>
                            {' '}Lugar donde se alojan otro tipo de laboratorios vulnerables para enseñar a los alumnos la
                            explotación de vulnerabilidades en laboratorios hechos a medida.
                            <br /><br />
                            Puedes acceder en modo de prueba a BunkerLabs a través de este{' '}
                            <a href="/bunkerlabs/guest"
                                style={{ color: '#a78bfa', textDecoration: 'underline', fontWeight: 600 }}>
                                enlace
                            </a>.
                        </p>
                    </div>
                </div>

                {/* Columna Derecha: Video */}
                <div className="video-section">
                    <div className="video-overlay"></div>
                    <div className="video-container">
                        <iframe
                            src="https://www.youtube.com/embed/cJS0IewSuRU?autoplay=1&mute=1&controls=0&showinfo=0&rel=0&loop=1&playlist=cJS0IewSuRU"
                            title="BunkerLabs Video"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowFullScreen
                        ></iframe>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default function BunkerLoginPage() {
    return (
        <BunkerLayout>
            <BunkerLoginContent />
        </BunkerLayout>
    )
}
