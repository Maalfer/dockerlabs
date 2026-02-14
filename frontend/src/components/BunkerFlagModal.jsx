import React, { useState, useRef, useEffect } from 'react'
import { useBunkerSession } from './BunkerLayout'
import './BunkerModals.css'

export default function BunkerFlagModal({ machineName, machineId, onClose, onSuccess }) {
    const [flag, setFlag] = useState('')
    const [msg, setMsg] = useState(null) // { type: 'success'|'error', text }
    const [loading, setLoading] = useState(false)
    const inputRef = useRef(null)
    const { csrf_token } = useBunkerSession()

    useEffect(() => { inputRef.current?.focus() }, [])

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!flag.trim()) return
        setLoading(true)
        setMsg(null)

        try {
            const res = await fetch('/bunkerlabs/subir-flag', {
                method: 'POST',
                credentials: 'include',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf_token },
                body: JSON.stringify({ machine_id: machineId, flag: flag.trim() })
            })
            const data = await res.json()
            if (res.ok && data.success) {
                setMsg({ type: 'success', text: data.message || '¡Flag correcta! 🎉' })
                if (onSuccess) onSuccess()
            } else {
                setMsg({ type: 'error', text: data.error || data.message || 'Flag incorrecta.' })
            }
        } catch {
            setMsg({ type: 'error', text: 'Error de conexión.' })
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="bunker-overlay" onClick={onClose}>
            <div className="bunker-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 450 }}>
                <button className="bunker-modal-close" onClick={onClose}>×</button>
                <h2>🚩 Subir Flag</h2>
                <h3>{machineName}</h3>

                <form onSubmit={handleSubmit}>
                    <div className="bunker-flag-input-group">
                        <input
                            ref={inputRef}
                            type="text"
                            placeholder="Introduce el PIN..."
                            value={flag}
                            onChange={e => setFlag(e.target.value)}
                            autoComplete="off"
                        />
                        <button type="submit" className="bunker-flag-btn" disabled={loading || !flag.trim()}>
                            {loading ? '...' : 'Validar'}
                        </button>
                    </div>
                </form>

                {msg && (
                    <div className={`bunker-alert ${msg.type}`}>{msg.text}</div>
                )}
            </div>
        </div>
    )
}
