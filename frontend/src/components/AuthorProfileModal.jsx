import React, { useEffect, useState } from 'react'
import BiographyModal from './BiographyModal'
import './RankingModals.css'

export default function AuthorProfileModal({ open, authorName, onClose }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [showBiography, setShowBiography] = useState(false)

  useEffect(() => {
    if (!open || !authorName) return
    setLoading(true)
    setError(null)
    fetch('/api/author_profile?nombre=' + encodeURIComponent(authorName))
      .then(r => r.json().then(d => ({ ok: r.ok, data: d })))
      .then(({ ok, data }) => {
        if (ok) setData(data)
        else setError(data?.error || 'Error al cargar perfil')
      })
      .catch(() => setError('Error de red'))
      .finally(() => setLoading(false))
  }, [open, authorName])

  if (!open) return null

  const openBio = () => setShowBiography(true)

  return (
    <>
      <div className="ranking-overlay visible" style={{ zIndex: 10050 }} onClick={(e) => e.target === e.currentTarget && onClose()}>
        <div className="ranking-popup visible" style={{ zIndex: 10051 }} onClick={e => e.stopPropagation()}>
          <button type="button" className="ranking-close-btn" onClick={onClose}>&times;</button>

          {loading && <p className="ranking-loading-msg">Cargando perfil...</p>}
          {error && <p className="ranking-error-msg">{error}</p>}

          {data && !loading && (
            <>
              <div className="ranking-profile-header">
                <img
                  src={data.profile_image_url}
                  alt=""
                  className="ranking-profile-avatar"
                  onClick={openBio}
                />
                <div className="ranking-profile-details">
                  <h2 onClick={openBio}>{data.nombre}</h2>
                  <div className="ranking-profile-stats">
                    Máquinas: <b>{data.maquinas?.length ?? 0}</b> · Writeups: <b>{data.writeups?.length ?? 0}</b>
                  </div>
                </div>
              </div>

              {(data.linkedin_url || data.github_url || data.youtube_url) && (
                <div className="ranking-social-bar">
                  {data.linkedin_url && (
                    <a href={data.linkedin_url} target="_blank" rel="noreferrer" style={{ color: '#0077b5', fontSize: '1.25rem' }}><i className="bi bi-linkedin"></i></a>
                  )}
                  {data.github_url && (
                    <a href={data.github_url} target="_blank" rel="noreferrer" style={{ color: '#f1f5f9', fontSize: '1.25rem' }}><i className="bi bi-github"></i></a>
                  )}
                  {data.youtube_url && (
                    <a href={data.youtube_url} target="_blank" rel="noreferrer" style={{ color: '#ef4444', fontSize: '1.25rem' }}><i className="bi bi-youtube"></i></a>
                  )}
                </div>
              )}

              <div className="ranking-divider" />

              <div style={{ marginTop: '1.5rem' }}>
                <div className="ranking-section-title">Máquinas Creadas</div>
                {data.maquinas?.length > 0 ? (
                  data.maquinas.map((m) => (
                    <div key={m.nombre} className="ranking-mini-list-item">
                      {m.imagen_url && <img src={m.imagen_url} alt="" className="ranking-mini-img" />}
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#f1f5f9' }}>{m.nombre}</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b', textTransform: 'uppercase' }}>{m.dificultad}</div>
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic' }}>Sin máquinas registradas.</p>
                )}
              </div>

              <div style={{ marginTop: '1.5rem' }}>
                <div className="ranking-section-title">Writeups Enviados</div>
                {data.writeups?.length > 0 ? (
                  data.writeups.map((w) => (
                    <div key={w.maquina + (w.url || '')} className="ranking-mini-list-item" style={{ justifyContent: 'space-between' }}>
                      <div>
                        <div style={{ fontWeight: 600, fontSize: '0.9rem', color: '#f1f5f9' }}>{w.maquina}</div>
                        <div style={{ fontSize: '0.75rem', color: '#64748b' }}>{w.tipo || ''}</div>
                      </div>
                      <a href={w.url} target="_blank" rel="noreferrer" style={{ fontSize: '0.8rem', color: '#3b82f6', textDecoration: 'none' }}>Ver ↗</a>
                    </div>
                  ))
                ) : (
                  <p style={{ fontSize: '0.85rem', color: '#64748b', fontStyle: 'italic' }}>Sin writeups enviados.</p>
                )}
              </div>
            </>
          )}
        </div>
      </div>

      <BiographyModal
        open={showBiography}
        onClose={() => setShowBiography(false)}
        authorName={data?.nombre}
        biography={data?.biography}
        profileImageUrl={data?.profile_image_url}
      />
    </>
  )
}
