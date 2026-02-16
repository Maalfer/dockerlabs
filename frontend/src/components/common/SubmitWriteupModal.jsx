import React, { useEffect, useState } from 'react'
import '../machines/MachineModal.css'

export default function SubmitWriteupModal({ machine, onClose }) {
    const [url, setUrl] = useState('')
    const [tipo, setTipo] = useState('texto')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState(null)
    const [success, setSuccess] = useState(false)
    const [csrf, setCsrf] = useState('')

    useEffect(() => {
        if (!machine) return
        fetch('/api/csrf', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(data => { if (data && data.csrf_token) setCsrf(data.csrf_token) })
            .catch(() => { })
    }, [machine])

    if (!machine) return null

    const handleSubmit = async (e) => {
        e.preventDefault()
        if (!url) return

        setLoading(true)
        setError(null)
        setSuccess(false)

        try {
            const response = await fetch('/subirwriteups', {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf,
                    'Accept': 'application/json'
                },
                body: JSON.stringify({
                    maquina: machine.nombre,
                    url: url,
                    tipo: tipo
                })
            })

            const ct = (response.headers.get('content-type') || '').toLowerCase()
            const raw = await response.text()
            const data = (ct.includes('application/json') && raw)
                ? (() => { try { return JSON.parse(raw) } catch { return null } })()
                : null

            if (!response.ok) {
                const msg = (data && (data.error || data.message)) || raw || 'Error al enviar el writeup'
                throw new Error(msg)
            }

            if (raw && ct.includes('application/json') && !data) {
                throw new Error('Respuesta inválida del servidor')
            }

            setSuccess(true)
            setTimeout(() => {
                onClose()
            }, 2000)

        } catch (err) {
            console.error(err)
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const handleOverlayClick = (e) => {
        if (e.target === e.currentTarget) {
            onClose();
        }
    };

    return (
        <div className="machine-modal-overlay visible" onClick={handleOverlayClick} style={{ display: 'flex', position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0,0,0,0.7)', zIndex: 9999, justifyContent: 'center', alignItems: 'center' }}>
            <div className="machine-modal-content" style={{ background: '#1a1a1a', padding: '2rem', borderRadius: '10px', maxWidth: '500px', width: '100%', position: 'relative', border: '1px solid #333' }}>
                <button className="machine-modal-close" onClick={onClose} style={{ position: 'absolute', top: '10px', right: '15px', background: 'none', border: 'none', fontSize: '1.5rem', color: '#fff', cursor: 'pointer' }}>&times;</button>

                <h2 style={{ color: '#fff', marginBottom: '0.5rem' }}>Subir Writeup</h2>
                <div style={{ color: '#888', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                    Máquina: <span style={{ color: machine.color || '#fff', fontWeight: 'bold' }}>{machine.nombre}</span>
                </div>

                {success ? (
                    <div style={{ textAlign: 'center', padding: '20px', color: '#4ade80' }}>
                        <i className="bi bi-check-circle-fill" style={{ fontSize: '3rem', marginBottom: '1rem', display: 'block' }}></i>
                        <p style={{ fontSize: '1.1rem' }}>¡Writeup enviado correctamente!</p>
                        <p style={{ fontSize: '0.9rem', color: '#888' }}>Será revisado por un administrador.</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit}>
                        <div className="form-group mb-3">
                            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#ccc' }}>URL del Writeup</label>
                            <input
                                type="url"
                                className="form-control"
                                value={url}
                                onChange={e => setUrl(e.target.value)}
                                placeholder="https://..."
                                required
                                style={{ width: '100%', padding: '0.5rem', borderRadius: '5px', border: '1px solid #333', background: '#0f0f0f', color: '#fff' }}
                            />
                        </div>

                        <div className="form-group mb-4">
                            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#ccc' }}>Tipo de Writeup</label>
                            <select
                                className="form-control"
                                value={tipo}
                                onChange={e => setTipo(e.target.value)}
                                style={{ width: '100%', padding: '0.5rem', borderRadius: '5px', border: '1px solid #333', background: '#0f0f0f', color: '#fff' }}
                            >
                                <option value="texto">Texto (Blog/Artículo)</option>
                                <option value="video">Video (YouTube)</option>
                            </select>
                        </div>

                        {error && <div className="alert alert-danger" style={{ color: '#ef4444', marginBottom: '1rem', padding: '0.5rem', background: 'rgba(239, 68, 68, 0.1)', borderRadius: '5px' }}>{error}</div>}

                        <div className="d-flex justify-content-end gap-2" style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                            <button type="button" className="btn btn-secondary" onClick={onClose} disabled={loading} style={{ padding: '0.5rem 1rem', borderRadius: '5px', background: '#333', border: 'none', color: '#fff', cursor: 'pointer' }}>
                                Cancelar
                            </button>
                            <button type="submit" className="btn btn-primary" disabled={loading} style={{ padding: '0.5rem 1rem', borderRadius: '5px', background: '#2563eb', border: 'none', color: '#fff', cursor: 'pointer', opacity: loading ? 0.7 : 1 }}>
                                {loading ? 'Enviando...' : 'Enviar Writeup'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    )
}
