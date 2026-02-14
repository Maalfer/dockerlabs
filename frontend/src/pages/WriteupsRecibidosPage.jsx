import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import './BunkerHomePage.css' // Reusing styles

export default function WriteupsRecibidosPage() {
    const [writeups, setWriteups] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const navigate = useNavigate()

    useEffect(() => {
        fetchWriteups()
    }, [])

    const fetchWriteups = async () => {
        try {
            const res = await fetch('/writeups/api/writeups_recibidos')
            if (!res.ok) throw new Error('Error al cargar writeups')
            const data = await res.json()
            setWriteups(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const handleApprove = async (id) => {
        if (!confirm('¿Aprobar este writeup?')) return
        try {
            const res = await fetch(`/writeups/api/writeups_recibidos/${id}/aprobar`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' } // Add CSRF if needed
            })
            if (res.ok) {
                setWriteups(writeups.filter(w => w.id !== id))
                alert('Writeup aprobado correctamente')
            } else {
                alert('Error al aprobar')
            }
        } catch (err) {
            alert('Error de conexión')
        }
    }

    const handleDelete = async (id) => {
        if (!confirm('¿Eliminar este writeup?')) return
        try {
            const res = await fetch(`/writeups/api/writeups_recibidos/${id}`, {
                method: 'DELETE'
            })
            if (res.ok) {
                setWriteups(writeups.filter(w => w.id !== id))
            } else {
                alert('Error al eliminar')
            }
        } catch (err) {
            alert('Error de conexión')
        }
    }

    return (
        <div className="container" style={{ paddingTop: '100px' }}>
            <div className="header">
                <div className="header-left">
                    <h1><i className="bi bi-inbox" style={{ color: '#a78bfa', marginRight: '10px' }}></i>Writeups Recibidos</h1>
                    <p className="subtitle">Gestión de writeups pendientes de aprobación</p>
                </div>
            </div>

            {loading && <div style={{ textAlign: 'center', color: '#94a3b8' }}>Cargando...</div>}
            {error && <div className="alert alert-danger">{error}</div>}

            <div className="machines-grid">
                {writeups.map(w => (
                    <div key={w.id} className="item" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: '1rem', height: 'auto' }}>
                        <div className="item-content" style={{ width: '100%' }}>
                            <div style={{ flex: 1 }}>
                                <div style={{ fontSize: '1.1rem', fontWeight: 'bold', color: '#fff' }}>{w.maquina}</div>
                                <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Autor: <span style={{ color: '#a78bfa' }}>{w.autor}</span></div>
                                <div style={{ color: '#94a3b8', fontSize: '0.85rem', marginTop: '0.5rem' }}>
                                    <a href={w.url} target="_blank" rel="noreferrer" style={{ color: '#60a5fa' }}><i className="bi bi-link-45deg"></i> Ver Writeup</a>
                                </div>
                                <div style={{ marginTop: '0.5rem' }}>
                                    <span className="badge" style={{ background: '#334155', color: '#fff' }}>{w.tipo}</span>
                                    <span style={{ fontSize: '0.8rem', color: '#64748b', marginLeft: '10px' }}>{new Date(w.created_at).toLocaleDateString()}</span>
                                </div>
                            </div>
                            {w.imagen && (
                                <img src={`/static/dockerlabs/images/${w.imagen}`} alt={w.maquina} style={{ width: '60px', height: '60px', borderRadius: '8px', objectFit: 'cover' }}
                                    onError={(e) => { e.target.onerror = null; e.target.src = '/static/dockerlabs/images/logo.png' }} />
                            )}
                        </div>
                        <div className="actions" style={{ width: '100%', justifyContent: 'flex-end', gap: '0.5rem', marginTop: '0.5rem' }}>
                            <button onClick={() => handleApprove(w.id)} style={{ background: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', border: '1px solid #22c55e' }}>
                                <i className="bi bi-check-lg"></i> Aprobar
                            </button>
                            <button onClick={() => handleDelete(w.id)} style={{ background: 'rgba(2ef, 68, 68, 0.2)', color: '#f87171', border: '1px solid #ef4444' }}>
                                <i className="bi bi-trash"></i> Rechazar
                            </button>
                        </div>
                    </div>
                ))}
                {!loading && writeups.length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                        <i className="bi bi-check-circle" style={{ fontSize: '3rem', marginBottom: '1rem', display: 'block' }}></i>
                        No hay writeups pendientes de revisión
                    </div>
                )}
            </div>
        </div>
    )
}
