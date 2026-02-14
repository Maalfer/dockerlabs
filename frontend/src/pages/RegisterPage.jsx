import React, { useEffect, useState } from 'react'

export default function RegisterPage(){
  const [csrf, setCsrf] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [pendingMsg, setPendingMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')

  useEffect(()=>{
    try{
      const params = new URLSearchParams(window.location.search)
      if (params.get('error')) setErrorMsg(params.get('error'))
      if (params.get('pending_message')) setPendingMsg(params.get('pending_message'))
      if (params.get('success')) setSuccessMsg(params.get('success'))
    }catch(e){}

    fetch('/api/csrf', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data && data.csrf_token) setCsrf(data.csrf_token) })
      .catch(()=>{})
  }, [])

  // Load original registro.css for visual parity
  useEffect(() => {
    const id = 'register-page-css'
    if (document.getElementById(id)) return
    const link = document.createElement('link')
    link.id = id
    link.rel = 'stylesheet'
    link.href = '/static/dockerlabs/css/registro.css'
    document.head.appendChild(link)
    return () => {
      const el = document.getElementById(id)
      if (el) el.remove()
    }
  }, [])

  return (
    <div className="register-container">
      <div className="register-box">
        <div className="register-header">
          <h2>Crear Cuenta</h2>
          <p>Únete a la comunidad de DockerLabs</p>
        </div>

        {errorMsg && <div className="alert alert-danger"><i className="fas fa-exclamation-circle"></i> <span>{errorMsg}</span></div>}
        {pendingMsg && <div className="alert alert-info"><i className="fas fa-info-circle"></i> <span>{pendingMsg}</span></div>}
        {successMsg && <div className="alert alert-success"><i className="fas fa-check-circle"></i> <span>{successMsg}</span></div>}

        <form method="post" action="/auth/register" className="register-form">
          <input type="hidden" name="csrf_token" value={csrf} />

          <div className="auth-grid">
            <div className="auth-column-left">
              <div className="form-group">
                <label htmlFor="username"><i className="fas fa-user"></i> Nombre de usuario</label>
                <input type="text" name="username" id="username" placeholder="Elige tu nombre de usuario" required autoComplete="username" autoFocus minLength={3} maxLength={20} />
              </div>

              <div className="form-group">
                <label htmlFor="email"><i className="fas fa-envelope"></i> Correo electrónico</label>
                <input type="email" name="email" id="email" placeholder="tu@correo.com" required autoComplete="email" maxLength={35} />
              </div>

              <div className="form-group">
                <label htmlFor="password"><i className="fas fa-lock"></i> Contraseña</label>
                <input type="password" name="password" id="password" placeholder="Crea una contraseña segura" required autoComplete="new-password" />
              </div>

              <div className="form-group">
                <label htmlFor="password2"><i className="fas fa-lock"></i> Confirmar contraseña</label>
                <input type="password" name="password2" id="password2" placeholder="Repite tu contraseña" required autoComplete="new-password" />
              </div>

              <div className="password-requirements">
                <h6><i className="fas fa-info-circle"></i> Requisitos de la contraseña:</h6>
                <ul>
                  <li><i className="fas fa-check-circle"></i> Mínimo 8 caracteres</li>
                  <li><i className="fas fa-check-circle"></i> Al menos una mayúscula</li>
                  <li><i className="fas fa-check-circle"></i> Al menos un número</li>
                  <li><i className="fas fa-check-circle"></i> Al menos un carácter especial</li>
                </ul>
              </div>

              <div className="terms-checkbox">
                <label>
                  <input type="checkbox" id="terms" name="terms" required />
                  <span>
                    Al registrarme acepto los
                    <a href="/politicas/condiciones_uso.html" target="_blank"> Términos y Condiciones</a>
                  </span>
                </label>
              </div>
            </div>

            <div className="auth-column-right">
              <button type="submit" className="btn-register"><i className="fas fa-user-plus"></i> Crear cuenta</button>
              <div className="logo-display">
                <img src="/static/dockerlabs/images/logos/logo.png" alt="DockerLabs Logo" className="auth-logo" />
              </div>
            </div>
          </div>
        </form>

        <div className="auth-footer-actions">
          <span className="text-muted">¿Ya tienes cuenta?</span>
          <span className="auth-separator">/</span>
          <a href="/auth/login" className="footer-link"><i className="fas fa-sign-in-alt"></i> Iniciar sesión</a>
        </div>
      </div>
    </div>
  )
}
