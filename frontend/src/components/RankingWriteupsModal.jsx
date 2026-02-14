import React, { useEffect, useState, useMemo } from 'react'
import './RankingModals.css'

const RANK_ICONS = ['🥇', '🥈', '🥉']

export default function RankingWriteupsModal({ open, onClose, onOpenAuthor }) {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!open) return
    setSearch('')
    setLoading(true)
    setError(null)
    fetch('/api/ranking_writeups', { credentials: 'include' })
      .then(r => {
        if (!r.ok) throw new Error('Error API')
        return r.json()
      })
      .then(data => {
        data.sort((a, b) => (b.puntos ?? 0) - (a.puntos ?? 0))
        setList(data)
      })
      .catch(() => setError('Error cargando ranking.'))
      .finally(() => setLoading(false))
  }, [open])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return list
    return list.filter(item => (item.nombre || '').toLowerCase().includes(q))
  }, [list, search])

  if (!open) return null

  return (
    <div className="ranking-overlay visible" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="ranking-popup visible" onClick={e => e.stopPropagation()}>
        <button type="button" className="ranking-close-btn" onClick={onClose}>&times;</button>

        <div className="ranking-modal-header">
          <h1 className="ranking-modal-title">Clasificación</h1>
          <div className="ranking-modal-subtitle">Writeups de la comunidad</div>
        </div>

        <div className="ranking-search-container">
          <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 500 }}>Filtrar</span>
          <div className="ranking-search-wrapper">
            <input
              type="text"
              className="ranking-search-input"
              placeholder="Buscar usuario..."
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
            <span style={{ color: '#64748b', display: 'flex' }}><i className="bi bi-search"></i></span>
          </div>
        </div>

        {loading && <p className="ranking-loading-msg">Cargando ranking...</p>}
        {error && <p className="ranking-error-msg">{error}</p>}

        {!loading && !error && (
          <ul className="ranking-list-ul">
            {filtered.map((item, index) => {
              const badgeClass = ['ranking-rank-1', 'ranking-rank-2', 'ranking-rank-3'][index] || ''
              const icon = RANK_ICONS[index] ?? '#' + (index + 1)
              return (
                <li
                  key={item.id ?? item.nombre}
                  className="ranking-item-li"
                  onClick={() => onOpenAuthor(item.nombre)}
                >
                  <div className={`ranking-rank-badge ${badgeClass}`}>{icon}</div>
                  {item.imagen_url && <img src={item.imagen_url} alt="" className="ranking-item-avatar" />}
                  <div className="ranking-item-user-info">
                    <span className="ranking-item-name">{item.nombre}</span>
                  </div>
                  <div className="ranking-item-points">{item.puntos ?? 0} pts</div>
                </li>
              )
            })}
          </ul>
        )}

        {!loading && !error && filtered.length === 0 && (
          <p className="ranking-loading-msg">No hay resultados</p>
        )}
      </div>
    </div>
  )
}
