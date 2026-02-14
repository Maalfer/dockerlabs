import React, { useEffect, useState, useMemo } from 'react'
import './RankingModals.css'

const RANK_ICONS = ['🥇', '🥈', '🥉']

export default function RankingAutoresModal({ open, onClose, onOpenAuthor }) {
  const [list, setList] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')

  useEffect(() => {
    if (!open) return
    setSearch('')
    setLoading(true)
    setError(null)
    fetch('/api/ranking_autores', { credentials: 'include' })
      .then(r => {
        if (!r.ok) throw new Error('Error API')
        return r.json()
      })
      .then(data => {
        data.sort((a, b) => (b.maquinas ?? 0) - (a.maquinas ?? 0))
        setList(data)
      })
      .catch(() => setError('Error cargando ranking.'))
      .finally(() => setLoading(false))
  }, [open])

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    if (!q) return list
    const name = (item) => (item.autor || item.nombre || '').toLowerCase()
    return list.filter(item => name(item).includes(q))
  }, [list, search])

  if (!open) return null

  return (
    <div className="ranking-overlay visible" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="ranking-popup visible" onClick={e => e.stopPropagation()}>
        <button type="button" className="ranking-close-btn" onClick={onClose}>&times;</button>

        <div className="ranking-modal-header">
          <h1 className="ranking-modal-title">Clasificación Autores</h1>
          <div className="ranking-modal-subtitle">Máquinas Creadas</div>
        </div>

        <div className="ranking-search-container">
          <span style={{ fontSize: '0.8rem', color: '#64748b', fontWeight: 500 }}>Filtrar</span>
          <div className="ranking-search-wrapper">
            <input
              type="text"
              className="ranking-search-input"
              placeholder="Buscar autor..."
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
              const name = item.autor || item.nombre
              return (
                <li
                  key={item.id ?? name}
                  className="ranking-item-li"
                  onClick={() => onOpenAuthor(name)}
                >
                  <div className={`ranking-rank-badge ${badgeClass}`}>{icon}</div>
                  {(item.imagen || item.imagen_url) && (
                    <img src={item.imagen || item.imagen_url} alt="" className="ranking-item-avatar" />
                  )}
                  <div className="ranking-item-user-info">
                    <span className="ranking-item-name">{name}</span>
                  </div>
                  <div className="ranking-item-maquinas">{item.maquinas ?? 0} máq.</div>
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
