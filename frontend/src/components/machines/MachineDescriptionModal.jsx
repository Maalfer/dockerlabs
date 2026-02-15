import React from 'react'
import './MachineDescriptionModal.css'

export default function MachineDescriptionModal({ machineName, description, onClose }) {
    if (!machineName) return null

    return (
        <div className="desc-overlay" onClick={onClose}>
            <div className="desc-popup" onClick={e => e.stopPropagation()}>
                <button className="desc-modal-close-button" onClick={onClose}>&times;</button>

                <div className="desc-popup-header">
                    <h2 className="desc-popup-title">
                        <i className="bi bi-info-circle-fill" style={{ color: '#3b82f6' }}></i>
                        Aprendizaje previsto
                    </h2>
                </div>

                {(!description || description.trim() === '') ? (
                    <p className="desc-popup-description" style={{ fontStyle: 'italic', color: '#64748b' }}>
                        No hay descripción disponible para {machineName}.
                    </p>
                ) : (
                    <div className="desc-popup-description">
                        {description}
                    </div>
                )}
            </div>
        </div>
    )
}
