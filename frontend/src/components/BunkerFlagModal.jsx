import React, { useState } from 'react'
import { useBunkerSession } from './BunkerLayout' // Ensure correct import path
import './BunkerFlagModal.css'

export default function BunkerFlagModal({ machineName, machineId, onClose }) {
    const [pin, setPin] = useState('')
    const [loading, setLoading] = useState(false)
    const [msg, setMsg] = useState(null) // { type: 'error'|'success', text: '' }

    // We can try to use sess.csrf_token if available, or fetch fresh
    const sess = useBunkerSession()

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!pin.trim()) return

        setLoading(true)
        setMsg(null)

        try {
            // Fetch CSRF if not in session or just to be safe (or use what we have)
            let token = sess.csrf_token
            if (!token) {
                const r = await fetch('/api/csrf', { credentials: 'include' })
                if (r.ok) {
                    const d = await r.json()
                    token = d.csrf_token
                }
            }

            const res = await fetch('/bunkerlabs/subir-flag', { // Original endpoint
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': token || ''
                },
                body: JSON.stringify({ maquina: machineName, pin: pin.trim() })
            })

            const data = await res.json()

            if (data.error) {
                setMsg({ type: 'error', text: data.error })
            } else {
                setMsg({ type: 'success', text: data.message })
                if (data.message && data.message.includes('correcta')) {
                    setTimeout(() => {
                        onClose()
                        // Optional: Refresh machines to show solved state? 
                        // We might need a way to trigger refresh in parent.
                        if (sess.refresh) sess.refresh()
                        window.location.reload() // As per original JS behavior
                    }, 1500)
                }
            }
        } catch (err) {
            setMsg({ type: 'error', text: 'Error de conexión.' })
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="bunker-flag-overlay" onClick={onClose}>
            <div className="bunker-flag-popup" onClick={e => e.stopPropagation()}>
                <button className="bunker-flag-close" onClick={onClose}>&times;</button>

                <h2 className="bunker-flag-title">Subir Flag</h2>

                <p style={{ fontSize: '0.95rem', color: '#94a3b8', marginBottom: '1.5rem', textAlign: 'center', lineHeight: 1.5 }}>
                    Introduce el PIN obtenido en la máquina:<br />
                    <strong style={{ color: '#e2e8f0' }}>{machineName}</strong>
                </p>

                {msg && (
                    <div className={`bunker-alert ${msg.type}`}>
                        {msg.text}
                    </div>
                )}

                <form onSubmit={handleSubmit}>
                    <input
                        type="text"
                        className="bunker-flag-input"
                        placeholder="PIN de Acceso"
                        value={pin}
                        onChange={e => setPin(e.target.value)}
                        autoFocus
                        disabled={loading}
                    />
                    <button type="submit" className="bunker-flag-btn" disabled={loading}>
                        {loading ? 'Validando...' : 'Validar Flag'}
                    </button>
                </form>
            </div>
        </div>
    )
}
