import React, { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import './Header.css'

export default function Header({ openModal }) {
  const [user, setUser] = useState({ is_authenticated: false, user: null })
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/user/info', { credentials: 'include' })
      .then(r => r.ok ? r.json() : Promise.resolve({ is_authenticated: false }))
      .then(data => setUser(data || { is_authenticated: false }))
      .catch(() => setUser({ is_authenticated: false }))
  }, [])

  const isAuth = !!user.is_authenticated



  return (
    <header className="position-fixed fixed-top" style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', alignItems: 'center', gap: '15px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
        <div className="logo-container">
          <a href="https://dockerlabs.es">
            <img src="/static/dockerlabs/images/logos/logo.png" alt="DockerLabs" width="60" height="55" />
          </a>
        </div>

        <div className="raiola-container">
          <a href="https://raiolanetworks.com/landing/hosting-...io/?utm_medium=affiliate&utm_source=5855&utm_campaign=Afiliados" target="_blank" rel="noreferrer">
            <img src="/static/dockerlabs/images/raiola.png" alt="Raiola Networks" width="290" height="50" />
          </a>
        </div>
      </div>

      <h1 style={{ margin: 0, textAlign: 'center' }}>
        <Link to="/bunkerlabs/login" id="dockerlabs-link">DockerLabs</Link>
      </h1>

      <div className="auth-buttons" style={{ justifySelf: 'end', display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <button id="menu-button" type="button" onClick={() => openModal('menu')} className="btn-auth">
          <i className="bi bi-list" />
          Menú
        </button>

        {isAuth ? (
          <>
            <button id="messaging-button" type="button" onClick={() => openModal('messaging')} className="btn-auth msg-btn">
              <i className="bi bi-envelope" />
              <span id="msg-badge" className="msg-badge">0</span>
            </button>

            <button id="gestion-button" type="button" onClick={() => openModal('gestion')} className="btn-auth">
              <i className="bi bi-file-text" /> Gestión writeups
            </button>

            <button id="dashboard-button" type="button" onClick={() => openModal('dashboard')} className="btn-auth">
              <i className="bi bi-speedometer2" /> Dashboard
            </button>

            <button id="logout-button" className="btn-auth btn-logout" onClick={() => window.location.href = '/auth/logout'}>
              <i className="bi bi-box-arrow-right" /> Cerrar sesión
            </button>
          </>
        ) : (
          <>
            <button id="login-button" onClick={() => navigate('/login')} className="btn-auth">
              <i className="bi bi-box-arrow-in-right" /> Iniciar sesión
            </button>
            <button id="register-button" onClick={() => navigate('/register')} className="btn-auth">
              <i className="bi bi-person-plus" /> Registro
            </button>
          </>
        )}
      </div>
    </header>
  )
}
