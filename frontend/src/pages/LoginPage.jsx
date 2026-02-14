import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './LoginPage.css'

import { useAuth } from '../context/AuthContext'

export default function LoginPage() {
  const [csrf, setCsrf] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const navigate = useNavigate()
  const { login } = useAuth()

  useEffect(() => {
    // read optional messages from query params (server sometimes redirects with ?error=...)
    try {
      const params = new URLSearchParams(window.location.search)
      if (params.get('error')) setErrorMsg(params.get('error'))
      if (params.get('success')) setSuccessMsg(params.get('success'))
    } catch (e) { }

    // fetch CSRF token (sets session cookie)
    fetch('/api/csrf', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data && data.csrf_token) setCsrf(data.csrf_token) })
      .catch(() => { })
  }, [])

  return (
    <div className="login-container">
      <div className="login-box">
        <div className="login-header">
          <h2>Iniciar Sesión</h2>
          <p>Accede a tu cuenta de DockerLabs</p>
        </div>

        {errorMsg && <div className="alert alert-danger"><i className="fas fa-exclamation-circle"></i> {errorMsg}</div>}
        {successMsg && <div className="alert alert-success"><i className="fas fa-check-circle"></i> {successMsg}</div>}

        <form method="post" className="login-form" onSubmit={async (e) => {
          e.preventDefault()
          setErrorMsg('')
          const fd = new FormData(e.currentTarget)
          const payload = { username: fd.get('username'), password: fd.get('password') }
          try {
            const res = await fetch('/auth/api_login', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }, body: JSON.stringify(payload) })
            const j = await res.json()
            if (res.ok && j.success) {
              login() // Update global auth state
              navigate('/dashboard')
            } else {
              setErrorMsg(j.message || 'Error al iniciar sesión')
            }
          } catch (err) { setErrorMsg('Error de red') }
        }}>
          <input type="hidden" name="csrf_token" value={csrf} />

          <div className="auth-grid">
            <div className="auth-column-left">
              <div className="form-group">
                <label htmlFor="username"><i className="fas fa-user"></i> Usuario</label>
                <input type="text" name="username" id="username" placeholder="Ingresa tu usuario" required autoComplete="username" autoFocus />
              </div>

              <div className="form-group">
                <label htmlFor="password"><i className="fas fa-lock"></i> Contraseña</label>
                <input type="password" name="password" id="password" placeholder="Ingresa tu contraseña" required autoComplete="current-password" />
              </div>
            </div>

            <div className="auth-column-right">
              <button type="submit" className="btn-login"><i className="fas fa-sign-in-alt"></i> Entrar</button>
              <div className="logo-display">
                <img src="/static/dockerlabs/images/logos/logo.png" alt="DockerLabs Logo" className="auth-logo" />
              </div>
            </div>
          </div>
        </form>

        <div className="auth-footer-actions">
          <a href="/recover" className="footer-link"><i className="bi bi-key"></i> ¿Olvidaste tu contraseña?</a>
          <span className="auth-separator">/</span>
          <a href="/register" className="footer-link"><i className="bi bi-person-plus"></i> Crear cuenta nueva</a>
        </div>
      </div>
    </div>
  )
}
