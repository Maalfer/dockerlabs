import React, { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import './RecoverPage.css'

export default function RecoverPage() {
  const [csrf, setCsrf] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    fetch('/api/csrf', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(data => { if (data?.csrf_token) setCsrf(data.csrf_token) })
      .catch(() => {})
  }, [])

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    const form = e.currentTarget
    const payload = {
      username: form.username.value.trim(),
      pin: form.pin.value.trim(),
      password: form.password.value,
      password2: form.password2.value
    }
    if (!payload.username || !payload.pin || !payload.password) {
      setError('Todos los campos son obligatorios.')
      return
    }
    setLoading(true)
    try {
      const res = await fetch('/auth/api_recover', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify(payload)
      })
      const j = await res.json().catch(() => ({}))
      if (res.ok && j.success) {
        setSuccess(j.message || 'Contraseña actualizada correctamente.')
        setTimeout(() => navigate('/login?success=' + encodeURIComponent(j.message || 'Contraseña actualizada.')), 1500)
      } else {
        setError(j.error || 'Error al restablecer la contraseña.')
      }
    } catch (err) {
      setError('Error de red.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="recover-container">
      <div className="recover-box">
        <div className="recover-header">
          <h2>Recuperar contraseña</h2>
          <p>Introduce tu usuario, PIN de recuperación y nueva contraseña</p>
        </div>

        {error && <div className="alert alert-danger"><i className="fas fa-exclamation-circle"></i> {error}</div>}
        {success && <div className="alert alert-success"><i className="fas fa-check-circle"></i> {success}</div>}

        <form onSubmit={handleSubmit} className="recover-form">
          <div className="form-group">
            <label htmlFor="username"><i className="fas fa-user"></i> Usuario</label>
            <input type="text" name="username" id="username" className="form-control" required autoComplete="username" />
          </div>
          <div className="form-group">
            <label htmlFor="pin"><i className="fas fa-key"></i> PIN de recuperación</label>
            <input type="text" name="pin" id="pin" className="form-control" required autoComplete="off" />
          </div>
          <div className="form-group">
            <label htmlFor="password"><i className="fas fa-lock"></i> Nueva contraseña</label>
            <input type="password" name="password" id="password" className="form-control" required autoComplete="new-password" />
          </div>
          <div className="form-group">
            <label htmlFor="password2"><i className="fas fa-lock"></i> Repetir nueva contraseña</label>
            <input type="password" name="password2" id="password2" className="form-control" required autoComplete="new-password" />
          </div>
          <button type="submit" className="btn-recover" disabled={loading}>
            {loading ? 'Procesando...' : 'Restablecer contraseña'}
          </button>
        </form>

        <div className="auth-footer-actions">
          <Link to="/login" className="footer-link"><i className="bi bi-box-arrow-in-right"></i> Volver a Iniciar sesión</Link>
        </div>
      </div>
    </div>
  )
}
