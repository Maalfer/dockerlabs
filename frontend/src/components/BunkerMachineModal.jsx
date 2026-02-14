import React from 'react'
import './BunkerModals.css'

function escapeHtml(str) {
    if (!str) return ''
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

export default function BunkerMachineModal({ machine, onClose }) {
    if (!machine) return null

    const claseMapping = {
        'Muy Fácil': 'muy-facil',
        'Fácil': 'facil',
        'Medio': 'medio',
        'Difícil': 'dificil'
    }
    const badgeClass = claseMapping[machine.dificultad] || ''

    return (
        <div className="bunker-overlay" onClick={onClose}>
            <div className="bunker-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 520 }}>
                <button className="bunker-modal-close" onClick={onClose}>×</button>

                {machine.imagen && (
                    <img src={machine.imagen} alt={machine.nombre} className="bunker-machine-img" />
                )}

                <h2 style={{ textAlign: 'center' }}>{escapeHtml(machine.nombre)}</h2>

                <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
                    <span className={`bunker-badge ${badgeClass}`}>{escapeHtml(machine.dificultad)}</span>
                </div>

                <div className="bunker-machine-meta">
                    <div className="bunker-machine-meta-item">
                        <span className="label">Autor</span>
                        <span className="value">{escapeHtml(machine.autor)}</span>
                    </div>
                    <div className="bunker-machine-meta-item">
                        <span className="label">Fecha</span>
                        <span className="value">{escapeHtml(machine.fecha)}</span>
                    </div>
                </div>

                {machine.descripcion && (
                    <div style={{
                        background: 'var(--bunker-surface-soft)', borderRadius: 10,
                        padding: '1rem', border: '1px solid var(--bunker-border-soft)', fontSize: '0.9rem',
                        lineHeight: 1.7, color: 'var(--bunker-text-secondary)'
                    }}>
                        {escapeHtml(machine.descripcion)}
                    </div>
                )}
            </div>
        </div>
    )
}
