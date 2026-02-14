import React, { useState, useEffect } from 'react'
import './BunkerModals.css'

export default function BunkerWriteupModal({ machineName, onClose }) {
    const [writeups, setWriteups] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        if (!machineName) return
        fetch(`/bunkerlabs/api/writeups/${encodeURIComponent(machineName)}`, { credentials: 'include' })
            .then(r => r.ok ? r.json() : { writeups: [] })
            .then(data => setWriteups(data.writeups || data || []))
            .catch(() => setWriteups([]))
            .finally(() => setLoading(false))
    }, [machineName])

    return (
        <div className="bunker-overlay" onClick={onClose}>
            <div className="bunker-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 500 }}>
                <button className="bunker-modal-close" onClick={onClose}>×</button>
                <h2>📝 Writeups</h2>
                <h3>{machineName}</h3>

                {loading ? (
                    <p style={{ textAlign: 'center', color: 'var(--bunker-text-muted)' }}>Cargando writeups...</p>
                ) : writeups.length === 0 ? (
                    <p style={{ textAlign: 'center', color: 'var(--bunker-text-muted)' }}>No hay writeups disponibles.</p>
                ) : (
                    <div>
                        {writeups.map((w, idx) => (
                            <div key={w.id || idx} className="bunker-writeup-item">
                                {w.locked ? (
                                    <span className="bunker-writeup-locked">
                                        <i className="bi bi-lock-fill" style={{ marginRight: '0.5rem' }}></i>
                                        {w.autor} — Bloqueado
                                    </span>
                                ) : (
                                    <a href={w.url} target="_blank" rel="noreferrer">
                                        <i className={`bi ${w.tipo === 'video' ? 'bi-play-circle' : 'bi-file-text'}`}></i>
                                        {w.autor} — {w.tipo === 'video' ? 'Video' : 'Texto'}
                                    </a>
                                )}
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    )
}
