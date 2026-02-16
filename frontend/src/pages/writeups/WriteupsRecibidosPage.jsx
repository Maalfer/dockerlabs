import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import '../bunker/BunkerHomePage.css' // Reusing styles

export default function WriteupsRecibidosPage() {
    const [writeups, setWriteups] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [csrf, setCsrf] = useState('')
    const navigate = useNavigate()

    const getImagenUrl = (imagen) => {
        const img = (imagen || '').toString().trim()
        if (!img) return null
        if (img.startsWith('http://') || img.startsWith('https://')) return img
        if (img.startsWith('dockerlabs/') || img.startsWith('bunkerlabs/')) return `/assets/${img}`
        if (img.includes('/')) return `/assets/dockerlabs/images/${img}`
        return `/assets/dockerlabs/images/logos/${img}`
    }

    useEffect(() => {
        fetch('/api/csrf', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(data => { if (data && data.csrf_token) setCsrf(data.csrf_token) })
            .catch(() => { })
        fetchWriteups()
    }, [])

    const fetchWriteups = async () => {
        try {
            const res = await fetch('/api/writeups_recibidos', { credentials: 'include' })
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
            const res = await fetch(`/api/writeups_recibidos/${id}/aprobar`, {
                method: 'POST',
                credentials: 'include',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrf,
                    'Accept': 'application/json'
                }
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
            const res = await fetch(`/api/writeups_recibidos/${id}`, {
                method: 'DELETE',
                credentials: 'include',
                headers: {
                    'X-CSRFToken': csrf,
                    'Accept': 'application/json'
                }
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
        <div className="container" style={{ paddingTop: '100px', overflowX: 'hidden' }}>
            <div className="header">
                <div className="header-left">
                    <h1><i className="bi bi-inbox" style={{ color: '#a78bfa', marginRight: '10px' }}></i>Writeups Recibidos</h1>
                    <p className="subtitle">Gestión de writeups pendientes de aprobación</p>
                </div>
            </div>

            {loading && <div style={{ textAlign: 'center', color: '#94a3b8' }}>Cargando...</div>}
            {error && <div className="alert alert-danger">{error}</div>}

            <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '100%', overflowX: 'hidden' }}>
                {writeups.map(w => {
                    const imgUrl = getImagenUrl(w.imagen)
                    return (
                        <div
                            key={w.id}
                            className="item"
                            style={{
                                display: 'flex',
                                flexDirection: 'row',
                                alignItems: 'center',
                                justifyContent: 'space-between',
                                gap: '1rem',
                                height: 'auto',
                                padding: '0.95rem 1rem',
                                border: '1px solid rgba(148,163,184,0.12)',
                                background: 'rgba(15, 23, 42, 0.35)',
                                borderRadius: '14px',
                                width: '100%',
                                maxWidth: '100%',
                                boxSizing: 'border-box'
                            }}
                        >
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem', minWidth: 0, flex: 1 }}>
                                {imgUrl && (
                                    <img
                                        src={imgUrl}
                                        alt={w.maquina}
                                        style={{ width: '52px', height: '52px', borderRadius: '10px', objectFit: 'cover', background: '#0f172a', flex: '0 0 auto' }}
                                        onError={(e) => { e.target.onerror = null; e.target.src = '/assets/dockerlabs/images/logo.png' }}
                                    />
                                )}
                                <div style={{ minWidth: 0 }}>
                                    <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff', wordBreak: 'break-word' }}>{w.maquina}</div>
                                    <div style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.2rem' }}>
                                        Autor: <span style={{ color: '#a78bfa', fontWeight: 700 }}>{w.autor}</span>
                                    </div>
                                    <div style={{ marginTop: '0.45rem', display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap', maxWidth: '100%' }}>
                                        <span className="badge" style={{ background: '#334155', color: '#fff' }}>{w.tipo}</span>
                                        <span style={{ fontSize: '0.8rem', color: '#64748b' }}>{new Date(w.created_at).toLocaleDateString()}</span>
                                        <a href={w.url} target="_blank" rel="noreferrer" style={{ color: '#60a5fa', fontSize: '0.85rem', textDecoration: 'none', maxWidth: '100%', overflowWrap: 'anywhere' }}>
                                            <i className="bi bi-link-45deg"></i> Ver writeup
                                        </a>
                                    </div>
                                </div>
                            </div>

                            <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'flex-end', flexWrap: 'wrap', flex: '0 0 auto' }}>
                                <button
                                    type="button"
                                    onClick={() => handleApprove(w.id)}
                                    style={{
                                        background: 'rgba(34, 197, 94, 0.15)',
                                        color: '#4ade80',
                                        border: '1px solid rgba(34, 197, 94, 0.55)',
                                        padding: '0.45rem 0.75rem',
                                        borderRadius: '10px'
                                    }}
                                >
                                    <i className="bi bi-check-lg"></i> Aprobar
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleDelete(w.id)}
                                    style={{
                                        background: 'rgba(239, 68, 68, 0.12)',
                                        color: '#f87171',
                                        border: '1px solid rgba(239, 68, 68, 0.55)',
                                        padding: '0.45rem 0.75rem',
                                        borderRadius: '10px'
                                    }}
                                >
                                    <i className="bi bi-trash"></i> Rechazar
                                </button>
                            </div>
                        </div>
                    )
                })}
                {!loading && writeups.length === 0 && (
                    <div style={{ textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                        <i className="bi bi-check-circle" style={{ fontSize: '3rem', marginBottom: '1rem', display: 'block' }}></i>
                        No hay writeups pendientes de revisión
                    </div>
                )}
            </div>
        </div>
    )
}
