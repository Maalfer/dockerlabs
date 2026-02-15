import React, { useEffect, useState } from 'react'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import './Header.css'

import { useAuth } from '../context/AuthContext'

export default function Header({ openModal }) {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const isAuth = !!user.is_authenticated
  const location = useLocation()

  // Determine base and alternate names depending on current route
  const baseName = location.pathname.startsWith('/bunkerlabs') ? 'BunkerLabs' : 'DockerLabs'
  const altName = baseName === 'DockerLabs' ? 'BunkerLabs' : 'DockerLabs'
  const [displayName, setDisplayName] = useState(baseName)

  useEffect(() => {
    setDisplayName(baseName)
  }, [baseName])
  // small animation: toggle classes to fade out/in when swapping name
  const animateSwap = (newName) => {
    const el = document.getElementById('dockerlabs-link')
    if (!el) {
      setDisplayName(newName)
      return
    }
    el.classList.add('fade-out')
    setTimeout(() => {
      setDisplayName(newName)
      el.classList.remove('fade-out')
      el.classList.add('fade-in')
      setTimeout(() => el.classList.remove('fade-in'), 180)
    }, 120)
  }

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
        <Link
          to="/bunkerlabs"
          id="dockerlabs-link"
          onMouseEnter={() => animateSwap(altName)}
          onMouseLeave={() => animateSwap(baseName)}
        >
          {displayName}
        </Link>
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

            <button id="logout-button" className="btn-auth btn-logout" onClick={logout}>
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
