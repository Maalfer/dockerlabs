import React from 'react'
// No CSS import needed as we use global styles from BunkerLayout.css (bunkerlabs.css)

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
        <div className="bunker-modal-overlay" onClick={onClose}>
            <div className="bunker-modal-popup" onClick={e => e.stopPropagation()}>
                <button className="bunker-modal-close" onClick={onClose}>×</button>

                <div className="bunker-modal-content">
                    <h2 className="bunker-modal-title">{escapeHtml(machine.nombre)}</h2>
                    <div className="bunker-modal-subtitle">
                        DIFICULTAD: <span className={badgeClass}>{escapeHtml(machine.dificultad)}</span>
                    </div>

                    <hr className="bunker-modal-separator" />

                    <div className="bunker-modal-body">
                        {machine.imagen && (
                            <img src={machine.imagen} alt={machine.nombre} className="bunker-modal-image" />
                        )}

                        <div className="bunker-modal-info">
                            <div className="bunker-modal-row">
                                <span className="bunker-modal-label">CREADOR</span>
                                <span className="bunker-modal-value">
                                    <a href={machine.enlace_autor || '#'} target="_blank" rel="noreferrer">
                                        {escapeHtml(machine.autor)}
                                    </a>
                                </span>
                            </div>

                            <div className="bunker-modal-row">
                                <span className="bunker-modal-label">FECHA DE SALIDA</span>
                                <span className="bunker-modal-value">{escapeHtml(machine.fecha)}</span>
                            </div>

                            {/* Assuming description might be handled differently or just added here */}
                            {machine.descripcion && (
                                <div style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#cbd5e1', lineHeight: 1.6 }}>
                                    {escapeHtml(machine.descripcion)}
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
