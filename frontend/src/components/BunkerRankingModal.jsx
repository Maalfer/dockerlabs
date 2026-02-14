import React, { useState, useEffect } from 'react'
import './BunkerModals.css'

export default function BunkerRankingModal({ onClose }) {
    const [ranking, setRanking] = useState([])
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        fetch('/bunkerlabs/api/ranking', { credentials: 'include' })
            .then(r => r.ok ? r.json() : [])
            .then(data => setRanking(Array.isArray(data) ? data : []))
            .catch(() => setRanking([]))
            .finally(() => setLoading(false))
    }, [])

    const medals = ['🥇', '🥈', '🥉']

    return (
        <div className="bunker-overlay" onClick={onClose}>
            <div className="bunker-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 500 }}>
                <button className="bunker-modal-close" onClick={onClose}>×</button>
                <h2>🏆 Ranking BunkerLabs</h2>

                {loading ? (
                    <p style={{ textAlign: 'center', color: 'var(--bunker-text-muted)' }}>Cargando ranking...</p>
                ) : ranking.length === 0 ? (
                    <p style={{ textAlign: 'center', color: 'var(--bunker-text-muted)' }}>No hay datos de ranking.</p>
                ) : (
                    <ul className="bunker-ranking-list">
                        {ranking.map((player, idx) => (
                            <li key={idx} className="bunker-ranking-item">
                                <span className="bunker-ranking-pos">{idx < 3 ? medals[idx] : `#${idx + 1}`}</span>
                                <span className="bunker-ranking-name">{player.nombre || player.name || '???'}</span>
                                <span className="bunker-ranking-pts">{player.puntos || player.points || 0} pts</span>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </div>
    )
}
