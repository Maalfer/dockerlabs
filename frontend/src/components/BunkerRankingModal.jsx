import React, { useEffect, useState } from 'react'
import './BunkerRankingModal.css'

export default function BunkerRankingModal({ onClose }) {
    const [ranking, setRanking] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(false)

    useEffect(() => {
        fetch('/bunkerlabs/api/ranking', { credentials: 'include' })
            .then(r => {
                if (!r.ok) throw new Error('Error al cargar ranking')
                return r.json()
            })
            .then(data => {
                // Sort by points desc
                const sorted = (data || []).sort((a, b) => b.puntos - a.puntos)
                setRanking(sorted)
                setLoading(false)
            })
            .catch(() => {
                setError(true)
                setLoading(false)
            })
    }, [])

    return (
        <div className="bunker-rank-overlay" onClick={onClose}>
            <div className="bunker-rank-popup" onClick={e => e.stopPropagation()}>
                <button className="bunker-rank-close" onClick={onClose}>&times;</button>

                <div className="bunker-rank-header">
                    <h2 className="bunker-rank-title">Salón de la Fama</h2>
                    <p style={{ fontSize: '0.8rem', color: '#94a3b8', margin: '0.2rem 0 0' }}>
                        Top agentes por máquinas hackeadas
                    </p>
                </div>

                <div className="bunker-rank-content">
                    {loading && <p style={{ textAlign: 'center', color: '#cbd5e1' }}>Cargando datos del búnker...</p>}

                    {error && (
                        <p style={{ color: '#f87171', textAlign: 'center' }}>
                            Fallo en los sistemas. No se pudo cargar el ranking.
                        </p>
                    )}

                    {!loading && !error && (
                        <ul className="bunker-rank-list">
                            {ranking.map((user, i) => {
                                const posClass = i === 0 ? 'rank-1' : i === 1 ? 'rank-2' : i === 2 ? 'rank-3' : ''
                                const icon = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : i + 1

                                return (
                                    <li key={i} className="bunker-rank-item">
                                        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                            <div className={`bunker-rank-pos ${posClass}`}>{icon}</div>
                                            <span style={{ fontWeight: 600, fontSize: '0.95rem' }}>{user.nombre}</span>
                                        </div>
                                        <span style={{ fontWeight: 800, color: '#a78bfa', fontSize: '0.9rem' }}>
                                            {user.puntos} <small style={{ fontWeight: 400, opacity: 0.6 }}>PTS</small>
                                        </span>
                                    </li>
                                )
                            })}
                        </ul>
                    )}
                </div>
            </div>
        </div>
    )
}
