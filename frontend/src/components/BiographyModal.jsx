import React from 'react'
import './RankingModals.css'

export default function BiographyModal({ open, onClose, authorName, biography, profileImageUrl }) {
  if (!open) return null

  const bioText = (biography || 'Este usuario aún no ha agregado una biografía.').trim()

  return (
    <div className="ranking-overlay visible" style={{ zIndex: 10060 }} onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="ranking-popup visible" style={{ width: 'min(440px, 90%)', zIndex: 10061 }} onClick={e => e.stopPropagation()}>
        <button type="button" className="ranking-close-btn" onClick={onClose}>&times;</button>
        <div className="ranking-modal-header">
          <h2 className="ranking-modal-title">Biografía</h2>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem', textAlign: 'center' }}>
          {profileImageUrl && (
            <img src={profileImageUrl} alt="" style={{ width: 80, height: 80, borderRadius: '50%', border: '2px solid #3b82f6', objectFit: 'cover' }} />
          )}
          <div>
            <h3 style={{ margin: 0, color: '#f1f5f9', fontSize: '1.1rem' }}>{authorName}</h3>
          </div>
          <div style={{
            background: 'rgba(15, 23, 42, 0.5)',
            padding: '1rem',
            borderRadius: 8,
            border: '1px solid #334155',
            width: '100%',
            textAlign: 'left',
            fontSize: '0.9rem',
            lineHeight: 1.6,
            color: '#cbd5e1',
            whiteSpace: 'pre-wrap'
          }}>
            {bioText}
          </div>
        </div>
      </div>
    </div>
  )
}
