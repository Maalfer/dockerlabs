import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import BunkerLayout, { useBunkerSession } from '../../components/layout/BunkerLayout'
import { useAuth } from '../../context/AuthContext'
import './BunkerLoginPage.css'

function BunkerLoginContent() {
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
    const [isFocused, setIsFocused] = useState(false)
    const navigate = useNavigate()
    const { login } = useAuth()
    const sess = useBunkerSession()

    useEffect(() => {
        if (sess.loaded && sess.logged_in) navigate('/bunkerlabs')
    }, [sess.loaded, sess.logged_in, navigate])

    const handleLogin = async (e) => {
        e.preventDefault()
        if (!password.trim()) return
        setError('')
        setLoading(true)

        try {
            const csrfRes = await fetch('/api/csrf', { credentials: 'include' })
            const csrfData = await csrfRes.json()
            const token = csrfData.csrf_token || ''

            const res = await fetch('/bunkerlabs/api/login', {
                method: 'POST',
                credentials: 'include',
                headers: { 'X-CSRFToken': token },
                body: new URLSearchParams({
                    password: password.trim(),
                    csrf_token: token
                })
            })
            const data = await res.json()

            if (res.ok && data.success) {
                sess.refresh()
                login()
                navigate('/bunkerlabs')
            } else {
                setError(data.error || 'Autenticación fallida')
            }
        } catch {
            setError('Error de conexión con el servidor')
        } finally {
            setLoading(false)
        }
    }

    const handleGuest = async (e) => {
        e.preventDefault()
        setError('')
        setLoading(true)
        try {
            const res = await fetch('/bunkerlabs/api/guest', { method: 'POST', credentials: 'include' })
            const data = await res.json()
            if (res.ok && data.success) {
                sess.refresh()
                navigate('/bunkerlabs')
            } else {
                setError(data.error || 'Acceso de invitado no disponible')
            }
        } catch {
            setError('Error de conexión')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="bunker-login-container">
            <div className={`bunker-login-card ${isFocused ? 'focused' : ''}`}>

                {/* Left Side: Login Form */}
                <div className="bunker-login-form-section">
                    <div className="bunker-brand">
                        <div className="brand-icon">
                            <i className="bi bi-shield-lock-fill"></i>
                        </div>
                        <div className="brand-text">
                            <h1>BunkerLabs</h1>
                            <span className="brand-badge">RESTRICTED</span>
                        </div>
                    </div>

                    <div className="login-header">
                        <h2>Bienvenido de nuevo</h2>
                        <p>Introduce tu llave de acceso para continuar.</p>
                    </div>

                    {error && (
                        <div className="bunker-error-alert">
                            <i className="bi bi-exclamation-octagon-fill"></i>
                            <span>{error}</span>
                        </div>
                    )}

                    <form onSubmit={handleLogin} className="login-form">
                        <div className="input-group">
                            <label htmlFor="password">Contraseña de Acceso</label>
                            <div className="input-wrapper">
                                <i className="bi bi-key-fill input-icon"></i>
                                <input
                                    type="password"
                                    id="password"
                                    className="bunker-input"
                                    placeholder="••••••••••••••"
                                    value={password}
                                    onChange={e => setPassword(e.target.value)}
                                    onFocus={() => setIsFocused(true)}
                                    onBlur={() => setIsFocused(false)}
                                    disabled={loading}
                                    autoFocus
                                />
                            </div>
                        </div>

                        <button type="submit" className="bunker-access-btn" disabled={loading}>
                            {loading ? (
                                <span className="loader"></span>
                            ) : (
                                <>
                                    <i className="bi bi-door-open-fill"></i> Acceder al Bunker
                                </>
                            )}
                        </button>
                    </form>

                    <div className="bunker-footer-info">
                        <p>
                            ¿Solo estás de paso? Accede al{' '}
                            <a href="#" onClick={handleGuest} className="guest-link">
                                Modo de Prueba <i className="bi bi-arrow-right"></i>
                            </a>
                        </p>
                        <div className="info-box">
                            <i className="bi bi-info-circle-fill"></i>
                            <p>
                                Lugar donde se alojan laboratorios vulnerables diseñados a medida para la enseñanza de explotación de vulnerabilidades.
                            </p>
                        </div>
                    </div>
                </div>

                {/* Right Side: Visual/Video */}
                <div className="bunker-visual-section">
                    <div className="visual-overlay"></div>
                    <div className="visual-content">
                        <h3>Entrenamiento Avanzado</h3>
                        <p>Simulaciones de entornos reales para profesionales de ciberseguridad.</p>
                    </div>
                    {/* Using a static image background via CSS usually looks cleaner, or we can keep the video if desired. 
                        Let's keep the video structure but style it better. */}
                    <div className="video-background">
                        <iframe
                            src="https://www.youtube.com/embed/cJS0IewSuRU?autoplay=1&mute=1&controls=0&showinfo=0&rel=0&loop=1&playlist=cJS0IewSuRU"
                            title="BunkerLabs Background"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
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
