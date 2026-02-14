import React from 'react'
import { Link } from 'react-router-dom'
import './ErrorPage.css'

export default function ForbiddenPage() {
  return (
    <div className="error-page-container">
      <div className="error-card error-card-403">
        <div className="error-content-flex">
          <div className="error-image-wrapper">
            <img src="/static/dockerlabs/images/errores/balu_enfadado.jpg" alt="Acceso prohibido" className="error-image" />
          </div>
          <div className="error-text-wrapper">
            <h1 className="error-title">403</h1>
            <h2 className="error-subtitle">Acceso Prohibido</h2>
            <p className="error-text">
              Lo siento, pero no tienes permiso para acceder a esta página. Balu está un poco molesto por tu intento.
            </p>
            <Link to="/" className="btn-home btn-home-403"><i className="bi bi-house-door"></i> Volver al inicio</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
