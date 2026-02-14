import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import './BunkerHomePage.css' // Reusing styles

export default function WriteupsPublicadosPage() {
    const [writeups, setWriteups] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [filter, setFilter] = useState('all') // 'all' or 'mine'

    useEffect(() => {
        fetchWriteups()
    }, [filter])

    const fetchWriteups = async () => {
        setLoading(true)
        try {
            const res = await fetch(`/writeups/api/writeups_subidos?filter=${filter}`)
            if (!res.ok) throw new Error('Error al cargar writeups')
            const data = await res.json()
            setWriteups(data)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="container" style={{ paddingTop: '100px' }}>
            <div className="header">
                <div className="header-left">
                    <h1><i className="bi bi-file-text" style={{ color: '#a78bfa', marginRight: '10px' }}></i>Writeups Publicados</h1>
                    <p className="subtitle">Explora los writeups de la comunidad</p>
                </div>
                <div className="header-right" style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                    <button
                        className={`btn-filter ${filter === 'all' ? 'active' : ''}`}
                        onClick={() => setFilter('all')}
                    >
                        Todos
                    </button>
                    <button
                        className={`btn-filter ${filter === 'mine' ? 'active' : ''}`}
                        onClick={() => setFilter('mine')}
                    >
                        Mis Writeups
                    </button>
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
                        </div>
                    </div>
                ))}
                {!loading && writeups.length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                        <i className="bi bi-search" style={{ fontSize: '3rem', marginBottom: '1rem', display: 'block' }}></i>
                        No se encontraron writeups
                    </div>
                )}
            </div>
        </div>
    )
}
