import React from 'react'
import { Link } from 'react-router-dom'
import './ErrorPage.css'

export default function NotFoundPage() {
  return (
    <div className="error-page-container">
      <div className="error-card error-card-404">
        <div className="error-content-flex">
          <div className="error-image-wrapper">
            <img src="/static/dockerlabs/images/errores/balu.webp" alt="Página no encontrada" className="error-image" />
          </div>
          <div className="error-text-wrapper">
            <h1 className="error-title">404</h1>
            <h2 className="error-subtitle">¡Ups! Página no encontrada</h2>
            <p className="error-text">
              Un cocker adorable ha estado buscando por todas partes, pero no ha encontrado lo que buscas.
            </p>
            <Link to="/" className="btn-home btn-home-404"><i className="bi bi-house-door"></i> Volver al inicio</Link>
          </div>
        </div>
      </div>
    </div>
  )
}
