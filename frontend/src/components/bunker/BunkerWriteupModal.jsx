import React, { useState, useEffect } from 'react'
// No CSS import needed as we use global styles from BunkerLayout.css (bunkerlabs.css)

export default function BunkerWriteupModal({ machineName, onClose }) {
    const [writeups, setWriteups] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(false)

    useEffect(() => {
        if (!machineName) return

        // Use the API endpoint that was confirmed to work in main app
        fetch(`/api/writeups/${encodeURIComponent(machineName)}`)
            .then(r => {
                if (!r.ok) throw new Error('Error al cargar writeups')
                return r.json()
            })
            .then(data => {
                // Determine if data is array or object with writeups key
                const list = Array.isArray(data) ? data : (data.writeups || [])
                setWriteups(list)
                setLoading(false)
            })
            .catch(() => {
                setError(true)
                setLoading(false)
            })
    }, [machineName])

    return (
        <div className="modal-writeup" style={{ display: 'block' }} onClick={onClose}>
            <div className="modal-writeup-content" onClick={e => e.stopPropagation()}>
                <span className="close-writeup" onClick={onClose}>&times;</span>

                <h2 id="writeup-machine-title">{machineName}</h2>

                <div id="writeup-content">
                    {loading && <p className="loading-text">Cargando writeups...</p>}

                    {error && <p className="error-text">Error al cargar los writeups.</p>}

                    {!loading && !error && writeups.length === 0 && (
                        <p className="no-writeups">No hay writeups disponibles para esta máquina.</p>
                    )}

                    {!loading && !error && writeups.length > 0 && (
                        <>
                            {/* Grouping by video/text if needed, or just list them */}
                            <h3 className="writeup-section-title">
                                <i className="bi bi-file-text me-2"></i> Writeups Disponibles
                            </h3>
                            <ul className="writeup-list">
                                {writeups.map((w, i) => {
                                    // w.type might be '🎥', 'video', 'texto', etc.
                                    const isVideo = w.type === '🎥' || w.type === 'video' || w.type === '\U0001F3A5'
                                    const iconClass = isVideo ? 'bi bi-play-circle-fill' : 'bi bi-file-earmark-text-fill'
                                    const colorStyle = isVideo ? { color: '#ef4444' } : { color: '#3b82f6' }

                                    return (
                                        <li key={i}>
                                            <a href={w.url} target="_blank" rel="noreferrer">
                                                <i className={iconClass} style={{ marginRight: '0.5rem', ...colorStyle }}></i>
                                                {w.name || w.autor || 'Writeup'} — {isVideo ? 'Video' : 'Texto'}
                                                {w.es_usuario_registrado && (
                                                    <span title="Usuario Verificado" style={{ marginLeft: '0.5rem' }}>⭐</span>
                                                )}
                                            </a>
                                        </li>
                                    )
                                })}
                            </ul>
                        </>
                    )}
                </div>
            </div>
        </div>
    )
}
