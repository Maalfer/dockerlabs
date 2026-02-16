import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import '../bunker/BunkerHomePage.css' // Reusing styles

export default function WriteupsPublicadosPage() {
    const [machines, setMachines] = useState([])
    const [writeups, setWriteups] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)
    const [filter, setFilter] = useState('all') // 'all' or 'mine'
    const [selectedMachine, setSelectedMachine] = useState(null)

    useEffect(() => {
        fetchMachines()
    }, [filter])

    const fetchMachines = async () => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`/api/writeups_subidos/maquinas?filter=${filter}`, { credentials: 'include' })
            if (!res.ok) throw new Error('Error al cargar máquinas')
            const data = await res.json()
            setMachines(Array.isArray(data) ? data : [])
            setSelectedMachine(null)
            setWriteups([])
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    const fetchWriteupsForMachine = async (machineName) => {
        setLoading(true)
        setError(null)
        try {
            const res = await fetch(`/api/writeups_subidos?filter=${filter}&maquina=${encodeURIComponent(machineName)}`, { credentials: 'include' })
            if (!res.ok) throw new Error('Error al cargar writeups')
            const data = await res.json()
            setWriteups(Array.isArray(data) ? data : [])
            setSelectedMachine(machineName)
        } catch (err) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

     return (
        <div className="container" style={{ paddingTop: '100px', maxWidth: 1200 }}>
            <div
                className="header"
                style={{
                    padding: '1.25rem 1.25rem',
                    borderRadius: '16px',
                    border: '1px solid rgba(148,163,184,0.14)',
                    background: 'linear-gradient(180deg, rgba(30,41,59,0.55), rgba(15,23,42,0.25))'
                }}
            >
                <div className="header-left">
                    <h1 style={{ margin: 0 }}>
                        <i className="bi bi-file-text" style={{ color: '#a78bfa', marginRight: '10px' }}></i>
                        Writeups Publicados
                    </h1>
                    <p className="subtitle" style={{ marginTop: '0.4rem' }}>Explora los writeups de la comunidad</p>
                </div>
                <div className="header-right" style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', alignItems: 'center' }}>
                    <button
                        type="button"
                        className={`btn-filter ${filter === 'all' ? 'active' : ''}`}
                        onClick={() => setFilter('all')}
                    >
                        Todos
                    </button>
                    <button
                        type="button"
                        className={`btn-filter ${filter === 'mine' ? 'active' : ''}`}
                        onClick={() => setFilter('mine')}
                    >
                        Mis Writeups
                    </button>
                </div>
            </div>

            {loading && <div style={{ textAlign: 'center', color: '#94a3b8' }}>Cargando...</div>}
            {error && <div className="alert alert-danger">{error}</div>}

            {selectedMachine && (
                <div style={{ marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <button className="btn-filter" onClick={() => { setSelectedMachine(null); setWriteups([]) }}>
                        <i className="bi bi-arrow-left"></i> Volver
                    </button>
                    <div style={{ color: '#e2e8f0', fontWeight: 700 }}>{selectedMachine}</div>
                </div>
            )}

            <div className="machines-grid" style={{ marginTop: '1rem' }}>
                {!selectedMachine && machines.map(m => (
                    <button
                        key={m.maquina}
                        type="button"
                        className="item"
                        onClick={() => fetchWriteupsForMachine(m.maquina)}
                        style={{
                            textAlign: 'left',
                            cursor: 'pointer',
                            padding: '1rem',
                            border: '1px solid rgba(148,163,184,0.14)',
                            background: 'rgba(15, 23, 42, 0.35)',
                            borderRadius: '14px'
                        }}
                    >
                        <div className="item-content" style={{ width: '100%', alignItems: 'center', gap: '0.9rem' }}>
                            <div style={{ width: 56, height: 56, borderRadius: 12, overflow: 'hidden', flex: '0 0 auto', background: '#0f172a', border: '1px solid rgba(148,163,184,0.12)' }}>
                                <img
                                    src={m.imagen || '/assets/dockerlabs/images/logo.png'}
                                    alt={m.maquina}
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    onError={(e) => { e.target.onerror = null; e.target.src = '/assets/dockerlabs/images/logo.png' }}
                                />
                            </div>
                            <div style={{ flex: 1, minWidth: 0 }}>
                                <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#fff', wordBreak: 'break-word' }}>{m.maquina}</div>
                                <div style={{ color: '#94a3b8', fontSize: '0.9rem', marginTop: '0.15rem' }}>
                                    <span style={{ color: '#a78bfa', fontWeight: 800 }}>{m.total}</span> writeup(s)
                                </div>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: '#94a3b8', flex: '0 0 auto' }}>
                                <span style={{ fontSize: '0.8rem', padding: '0.2rem 0.5rem', border: '1px solid rgba(148,163,184,0.18)', borderRadius: 999, background: 'rgba(148,163,184,0.06)' }}>{filter === 'mine' ? 'Mis' : 'Todos'}</span>
                                <i className="bi bi-chevron-right" style={{ color: '#64748b' }}></i>
                            </div>
                        </div>
                    </button>
                ))}

                {selectedMachine && writeups.map(w => (
                    <div
                        key={w.id}
                        className="item"
                        style={{
                            flexDirection: 'column',
                            alignItems: 'stretch',
                            gap: '0.75rem',
                            height: 'auto',
                            padding: '1rem',
                            border: '1px solid rgba(148,163,184,0.14)',
                            background: 'rgba(15, 23, 42, 0.35)',
                            borderRadius: '14px'
                        }}
                    >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                            <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>
                                <i className="bi bi-person" style={{ marginRight: 6 }}></i>
                                <span style={{ color: '#a78bfa', fontWeight: 800 }}>{w.autor}</span>
                            </div>
                            <span className="badge" style={{ background: '#334155', color: '#fff' }}>{w.tipo}</span>
                            <span style={{ color: '#64748b', fontSize: '0.8rem' }}>{new Date(w.created_at).toLocaleDateString()}</span>
                        </div>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
                            <a href={w.url} target="_blank" rel="noreferrer" style={{ color: '#60a5fa', textDecoration: 'none' }}>
                                <i className="bi bi-link-45deg"></i> Abrir writeup
                            </a>
                            <a href={w.url} target="_blank" rel="noreferrer" style={{ color: '#94a3b8', textDecoration: 'none', fontSize: '0.85rem' }}>
                                Copiar enlace <i className="bi bi-box-arrow-up-right" style={{ marginLeft: 4 }}></i>
                            </a>
                        </div>
                    </div>
                ))}

                {!loading && !selectedMachine && machines.length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                        <i className="bi bi-search" style={{ fontSize: '3rem', marginBottom: '1rem', display: 'block' }}></i>
                        No se encontraron máquinas con writeups
                    </div>
                )}

                {!loading && selectedMachine && writeups.length === 0 && (
                    <div style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '3rem', color: '#64748b' }}>
                        <i className="bi bi-search" style={{ fontSize: '3rem', marginBottom: '1rem', display: 'block' }}></i>
                        No se encontraron writeups
                    </div>
                )}
            </div>
        </div>
    )
}
