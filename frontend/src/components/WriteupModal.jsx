import React, { useEffect, useState } from 'react'
import '../components/BunkerModals.css' // Reusing Bunker modal styles for consistency

export default function WriteupModal({ machineName, onClose }) {
    const [writeups, setWriteups] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        if (!machineName) return
        setLoading(true)
        setError(null)

        // Endpoint from writeups.py: /api/writeups/<maquina_nombre>
        // Note: The backend endpoint is @writeups_bp.route('/api/writeups/<maquina_nombre>')
        // which is registered under the app directly or via blueprint.
        // In app.py: app.register_blueprint(writeups_bp) -> NO url_prefix
        // So /api/writeups/... is correct.
        fetch(`/api/writeups/${encodeURIComponent(machineName)}`)
            .then(r => {
                if (!r.ok) throw new Error('Error al cargar writeups')
                return r.json()
            })
            .then(data => {
                // data is array of objects: { id, name, url, type, es_usuario_registrado }
                setWriteups(data || [])
            })
            .catch((err) => {
                console.error(err)
                setError('No se pudieron cargar los writeups.')
            })
            .finally(() => setLoading(false))
    }, [machineName])

    if (!machineName) return null

    return (
        <div className="bunker-overlay" onClick={onClose}>
            <div className="bunker-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 500 }}>
                <button className="bunker-modal-close" onClick={onClose}>×</button>
                <h2>📝 Writeups</h2>
                <h3>{machineName}</h3>

                {loading && <p style={{ textAlign: 'center', color: 'var(--bunker-text-muted)' }}>Cargando...</p>}
                {error && <p style={{ textAlign: 'center', color: '#ef4444' }}>{error}</p>}

                {!loading && !error && writeups.length === 0 && (
                    <p style={{ textAlign: 'center', color: 'var(--bunker-text-muted)' }}>No hay writeups disponibles.</p>
                )}

                {!loading && !error && writeups.length > 0 && (
                    <div className="bunker-writeups-list">
                        {writeups.map((w, idx) => {
                            // Backend types: video (🎥), text (📝)
                            // But here in main app get_writeups returns: { name: autor, type: emoji... }
                            // Wait, let's double check writeups.py api_writeups_maquina
                            /*
                              writeups.append({
                                  "id": wid,
                                  "name": autor,
                                  "url": url,
                                  "type": tipo_emoji, // 🎥 or 📝
                                  "es_usuario_registrado": bool(uid),
                              })
                            */
                            const isVideo = w.type === '🎥' || w.type === '\U0001F3A5' || w.type === 'video'

                            return (
                                <div key={w.id || idx} className="bunker-writeup-item">
                                    <a href={w.url} target="_blank" rel="noreferrer" className={w.es_usuario_registrado ? 'autor-registrado' : ''}>
                                        <i className={`bi ${isVideo ? 'bi-play-circle-fill' : 'bi-file-earmark-text-fill'}`}
                                            style={{ marginRight: '0.5rem', color: isVideo ? '#ef4444' : '#3b82f6' }}></i>
                                        {w.name} — {isVideo ? 'Video' : 'Texto'}
                                        {w.es_usuario_registrado && <span title="Usuario Verificado" style={{ marginLeft: '0.5rem' }}>⭐</span>}
                                    </a>
                                </div>
                            )
                        })}
                    </div>
                )}
            </div>
        </div>
    )
}
