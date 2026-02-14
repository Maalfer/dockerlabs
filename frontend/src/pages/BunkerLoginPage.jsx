import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import BunkerLayout, { useBunkerSession } from '../components/BunkerLayout'
import './BunkerLoginPage.css'

function BunkerLoginContent() {
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const [loading, setLoading] = useState(false)
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

    const handleGuest = async () => {
        setError('')
        setLoading(true)
        try {
            const res = await fetch('/bunkerlabs/api/guest', {
                method: 'POST',
                credentials: 'include'
            })
            const data = await res.json()
            if (res.ok && data.success) {
                sess.refresh()
                navigate('/bunkerlabs')
            } else {
                setError(data.error || 'Error al entrar como invitado')
            }
        } catch {
            setError('Error de conexión')
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="bunker-login-wrapper">
            <div className="bunker-login-grid">
                {/* LEFT: Login form */}
                <div className="bunker-login-card">
                    <div className="bunker-login-header">
                        <h2>🔐 Acceso BunkerLabs</h2>
                        <p>Introduce tu contraseña de acceso</p>
                    </div>

                    {error && <div className="bunker-login-alert error">{error}</div>}

                    <form className="bunker-login-form" onSubmit={handleLogin}>
                        <div className="bunker-form-group">
                            <label htmlFor="bunker-pw"><i className="bi bi-key"></i> Contraseña</label>
                            <input
                                id="bunker-pw"
                                type="password"
                                placeholder="Tu contraseña de acceso..."
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                autoFocus
                                autoComplete="off"
                            />
                        </div>
                        <button type="submit" className="bunker-btn-login" disabled={loading}>
                            <i className="bi bi-box-arrow-in-right"></i>
                            {loading ? 'Accediendo...' : 'Acceder'}
                        </button>
                    </form>

                    <div className="bunker-login-footer">
                        <button onClick={handleGuest} disabled={loading}>
                            <i className="bi bi-person"></i> Entrar como invitado
                        </button>
                    </div>
                </div>

                {/* RIGHT: Video */}
                <div className="bunker-login-video">
                    <iframe
                        src="https://www.youtube.com/embed/SSPKQmep-bE?si=W0XN5dJpU2mT_vFr"
                        title="BunkerLabs Video"
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                        allowFullScreen
                    />
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
