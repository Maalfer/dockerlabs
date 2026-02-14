import React, { useEffect, useState, useRef } from 'react'
import './DashboardPage.css'

/* ── helpers ────────────────────────────────────────────── */
const getCsrf = () =>
  fetch('/api/csrf', { credentials: 'include' })
    .then(r => r.ok ? r.json() : {})
    .then(d => d.csrf_token || '')

function Alert({ msg, type, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 5000); return () => clearTimeout(t) }, [onClose])
  return (
    <div className={`dash-alert ${type}`}>
      {msg}
      <button className="close-btn" onClick={onClose}><i className="bi bi-x-lg" /></button>
    </div>
  )
}

/* ── password helpers ───────────────────────────────────── */
function calcStrength(pw) {
  let s = 0
  if (pw.length >= 8) s += 25
  if (/[A-Z]/.test(pw)) s += 25
  if (/[0-9]/.test(pw)) s += 25
  if (/[^A-Za-z0-9]/.test(pw)) s += 25
  return s
}
function strengthLabel(s) {
  if (s >= 75) return { text: 'Fuerte', color: '#10b981' }
  if (s >= 50) return { text: 'Media', color: '#f59e0b' }
  return { text: 'Débil', color: '#ef4444' }
}

/* ── social link validators ─────────────────────────────── */
const DANGEROUS = ['"', "'", '<', '>', '`']
const urlRegexes = {
  linkedin: /^https:\/\/(www\.)?linkedin\.com\/.*$/,
  github: /^https:\/\/(www\.)?github\.com\/.*$/,
  youtube: /^https:\/\/(www\.)?(youtube\.com|youtu\.be)\/.*$/
}
function validateSocial(val, which) {
  if (!val) return null
  for (const c of DANGEROUS) if (val.includes(c)) return `Contiene carácter no permitido: ${c}`
  if (!urlRegexes[which].test(val)) return `URL de ${which} no válida`
  return null
}

/* ══════════════════════════════════════════════════════════ */
export default function DashboardPage() {
  const [me, setMe] = useState(null)
  const [dashData, setDashData] = useState({ machines: [], claims: [] })
  const [alert, setAlert] = useState(null)

  /* profile form */
  const [bio, setBio] = useState('')
  const [linkedin, setLinkedin] = useState('')
  const [github, setGithub] = useState('')
  const [youtube, setYoutube] = useState('')

  /* password form */
  const [curPw, setCurPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confPw, setConfPw] = useState('')

  /* modals */
  const [showClaimModal, setShowClaimModal] = useState(false)
  const [showNameModal, setShowNameModal] = useState(false)

  /* claim form */
  const [claimMachine, setClaimMachine] = useState('')
  const [claimContact, setClaimContact] = useState('')
  const [claimProof, setClaimProof] = useState('')

  /* username change form */
  const [reqUsername, setReqUsername] = useState('')
  const [reqReason, setReqReason] = useState('')
  const [reqContact, setReqContact] = useState('')

  const fileRef = useRef(null)

  const showAlert = (msg, type = 'info') => setAlert({ msg, type })

  /* ── fetch data ─────────────────────────────────────── */
  const loadUser = () =>
    fetch('/api/me', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(d => {
        if (d && d.authenticated) {
          setMe(d)
          setBio(d.biography || '')
          setLinkedin(d.linkedin_url || '')
          setGithub(d.github_url || '')
          setYoutube(d.youtube_url || '')
        }
      }).catch(() => { })

  const loadDash = () =>
    fetch('/api/dashboard-data', { credentials: 'include' })
      .then(r => r.ok ? r.json() : { machines: [], claims: [] })
      .then(setDashData)
      .catch(() => { })

  useEffect(() => { loadUser(); loadDash() }, [])

  /* ── photo upload ───────────────────────────────────── */
  const handlePhoto = async e => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.type.startsWith('image/')) return showAlert('Selecciona una imagen válida.', 'error')
    if (file.size > 5 * 1024 * 1024) return showAlert('La imagen no debe superar los 5MB.', 'error')

    showAlert('Subiendo foto de perfil...', 'info')
    const csrf = await getCsrf()
    const fd = new FormData()
    fd.append('photo', file)
    try {
      const res = await fetch('/upload-profile-photo', {
        method: 'POST', body: fd, credentials: 'include',
        headers: { 'X-CSRFToken': csrf }
      })
      const data = await res.json()
      if (!res.ok) return showAlert(data.error || 'Error al subir la foto.', 'error')
      if (data.image_url) setMe(prev => ({ ...prev, profile_image_url: data.image_url }))
      showAlert(data.message || 'Foto actualizada.', 'success')
    } catch { showAlert('Error de conexión al subir la foto.', 'error') }
  }

  /* ── save profile (bio + social) ────────────────────── */
  const saveProfile = async () => {
    const lErr = validateSocial(linkedin, 'linkedin')
    if (lErr) return showAlert(lErr, 'error')
    const gErr = validateSocial(github, 'github')
    if (gErr) return showAlert(gErr, 'error')
    const yErr = validateSocial(youtube, 'youtube')
    if (yErr) return showAlert(yErr, 'error')

    showAlert('Guardando perfil...', 'info')
    const csrf = await getCsrf()
    const headers = { 'Content-Type': 'application/json', 'X-CSRFToken': csrf }

    try {
      const r1 = await fetch('/api/update_profile', {
        method: 'POST', credentials: 'include', headers,
        body: JSON.stringify({ biography: bio })
      })
      const d1 = await r1.json()
      if (!r1.ok) return showAlert(d1.error || 'Error al actualizar.', 'error')

      const r2 = await fetch('/api/update_social_links', {
        method: 'POST', credentials: 'include', headers,
        body: JSON.stringify({ linkedin_url: linkedin, github_url: github, youtube_url: youtube })
      })
      const d2 = await r2.json()
      if (!r2.ok) return showAlert(d2.error || 'Error al actualizar enlaces.', 'error')

      showAlert('Perfil y enlaces actualizados correctamente.', 'success')
    } catch { showAlert('Error de conexión.', 'error') }
  }

  /* ── change password ────────────────────────────────── */
  const changePassword = async () => {
    if (!curPw || !newPw || !confPw) return showAlert('Todos los campos son obligatorios.', 'error')
    if (newPw !== confPw) return showAlert('Las contraseñas nuevas no coinciden.', 'error')
    if (calcStrength(newPw) < 75) return showAlert('La contraseña no cumple los requisitos.', 'error')

    showAlert('Cambiando contraseña...', 'info')
    const csrf = await getCsrf()
    try {
      const res = await fetch('/api/change_password', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ current_password: curPw, new_password: newPw })
      })
      const data = await res.json()
      if (!res.ok) return showAlert(data.error || 'Error.', 'error')
      setCurPw(''); setNewPw(''); setConfPw('')
      showAlert(data.message || 'Contraseña actualizada.', 'success')
    } catch { showAlert('Error de conexión.', 'error') }
  }

  /* ── claim machine ──────────────────────────────────── */
  const submitClaim = async () => {
    if (!claimMachine || !claimContact || !claimProof) return showAlert('Todos los campos son obligatorios.', 'error')
    const csrf = await getCsrf()
    try {
      const res = await fetch('/api/reclamar-maquina', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ maquina_nombre: claimMachine, contacto: claimContact, prueba: claimProof })
      })
      const data = await res.json()
      if (!res.ok) return showAlert(data.error || 'Error.', 'error')
      showAlert(data.message || 'Reclamación enviada.', 'success')
      setShowClaimModal(false); setClaimMachine(''); setClaimContact(''); setClaimProof('')
      loadDash()
    } catch { showAlert('Error de conexión.', 'error') }
  }

  /* ── request username change ────────────────────────── */
  const submitNameChange = async () => {
    if (!reqUsername) return showAlert('Debes escribir un nombre nuevo.', 'error')
    const csrf = await getCsrf()
    try {
      const res = await fetch('/api/request_username_change', {
        method: 'POST', credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        body: JSON.stringify({ requested_username: reqUsername, reason: reqReason, contacto_opcional: reqContact })
      })
      const data = await res.json()
      if (!res.ok) return showAlert(data.error || 'Error.', 'error')
      showAlert(data.message || 'Solicitud enviada.', 'success')
      setShowNameModal(false); setReqUsername(''); setReqReason(''); setReqContact('')
    } catch { showAlert('Error de conexión.', 'error') }
  }

  /* ── approve / reject claim ─────────────────────────── */
  const handleClaim = async (id, action) => {
    const csrf = await getCsrf()
    try {
      const res = await fetch(`/api/claims/${id}/${action}`, {
        method: 'POST', credentials: 'include',
        headers: { 'X-CSRFToken': csrf }
      })
      const data = await res.json()
      if (!res.ok) return showAlert(data.error || 'Error.', 'error')
      showAlert(data.message, 'success')
      loadDash()
    } catch { showAlert('Error de conexión.', 'error') }
  }

  /* ── render ─────────────────────────────────────────── */
  if (!me) return <div className="dashboard-container"><p>Cargando dashboard...</p></div>

  const strength = calcStrength(newPw)
  const { text: sText, color: sColor } = strengthLabel(strength)
  const isAdmin = me.role === 'admin' || me.role === 'moderador'

  return (
    <div className="dashboard-container">
      {alert && <Alert msg={alert.msg} type={alert.type} onClose={() => setAlert(null)} />}

      {/* ── Welcome ── */}
      <div className="welcome-section">
        <h1>Panel de Control</h1>
        <p className="welcome-text">Bienvenido, <span className="username">{me.username}</span></p>
      </div>

      <div className="dashboard-content">

        {/* ═══ PROFILE ═══ */}
        <section className="profile-section">
          <div className="section-header">
            <h2><i className="bi bi-person-circle" /> Mi Perfil</h2>
          </div>

          <div className="profile-content">
            {/* Photo */}
            <div className="profile-picture-section">
              <div className="profile-picture-container" onClick={() => fileRef.current?.click()}>
                <img className="profile-picture" src={me.profile_image_url} alt="Perfil" />
                <div className="profile-picture-overlay">
                  <button type="button" className="change-photo-btn"><i className="bi bi-camera" /></button>
                </div>
              </div>
              <input ref={fileRef} type="file" accept="image/*" hidden onChange={handlePhoto} />
              <p className="photo-help-text">Haz clic para cambiar</p>
            </div>

            {/* Fields */}
            <div className="profile-form">
              {/* username (read-only) */}
              <div className="form-group">
                <label><i className="bi bi-person" /> Nombre de usuario</label>
                <div className="input-group">
                  <div className="profile-display-field" style={{ flex: 1 }}>{me.username}</div>
                  <button className="btn-edit" title="Solicitar cambio de nombre" onClick={() => setShowNameModal(true)}>
                    <i className="bi bi-pencil" />
                  </button>
                </div>
              </div>

              {/* email (read-only) */}
              <div className="form-group">
                <label><i className="bi bi-envelope" /> Correo electrónico</label>
                <div className="profile-display-field">{me.email}</div>
              </div>

              {/* bio */}
              <div className="form-group">
                <label><i className="bi bi-chat-text" /> Biografía</label>
                <textarea className="dash-input" maxLength={500} value={bio} onChange={e => setBio(e.target.value)}
                  placeholder="Escribe algo sobre ti..." />
              </div>

              {/* social links */}
              <div className="form-group">
                <label><i className="bi bi-linkedin" /> LinkedIn</label>
                <input className="dash-input" value={linkedin} onChange={e => setLinkedin(e.target.value)}
                  placeholder="https://linkedin.com/in/..." />
              </div>
              <div className="form-group">
                <label><i className="bi bi-github" /> GitHub</label>
                <input className="dash-input" value={github} onChange={e => setGithub(e.target.value)}
                  placeholder="https://github.com/..." />
              </div>
              <div className="form-group">
                <label><i className="bi bi-youtube" /> YouTube</label>
                <input className="dash-input" value={youtube} onChange={e => setYoutube(e.target.value)}
                  placeholder="https://youtube.com/..." />
              </div>

              <div className="form-actions">
                <button className="btn-save" onClick={saveProfile}>
                  <i className="bi bi-check-lg" /> Guardar Cambios
                </button>
                <button className="btn-cancel" onClick={loadUser}>
                  <i className="bi bi-x-lg" /> Cancelar
                </button>
              </div>
            </div>
          </div>
        </section>

        {/* ═══ SECURITY ═══ */}
        <section className="security-section">
          <div className="section-header">
            <h2><i className="bi bi-shield-lock" /> Seguridad</h2>
          </div>

          <div className="security-form">
            <div className="form-group">
              <label><i className="bi bi-lock" /> Contraseña actual</label>
              <input type="password" className="dash-input" value={curPw} onChange={e => setCurPw(e.target.value)} />
            </div>
            <div className="form-group">
              <label><i className="bi bi-key" /> Nueva contraseña</label>
              <input type="password" className="dash-input" value={newPw} onChange={e => setNewPw(e.target.value)} />
              {newPw && (
                <div className="password-strength">
                  <div className="strength-bar-track">
                    <div className="strength-bar" style={{ width: `${strength}%`, background: sColor }} />
                  </div>
                  <span className="strength-text" style={{ color: sColor }}>Seguridad: {sText}</span>
                </div>
              )}
            </div>
            <div className="form-group">
              <label><i className="bi bi-key-fill" /> Confirmar nueva contraseña</label>
              <input type="password" className="dash-input" value={confPw} onChange={e => setConfPw(e.target.value)} />
            </div>

            <div className="password-requirements">
              <h4>Requisitos de la contraseña</h4>
              <ul>
                <li className={`requirement ${newPw.length >= 8 ? 'met' : ''}`}>
                  <i className={`bi ${newPw.length >= 8 ? 'bi-check-circle' : 'bi-dash-circle'}`} /> Mínimo 8 caracteres
                </li>
                <li className={`requirement ${/[A-Z]/.test(newPw) ? 'met' : ''}`}>
                  <i className={`bi ${/[A-Z]/.test(newPw) ? 'bi-check-circle' : 'bi-dash-circle'}`} /> Al menos una mayúscula
                </li>
                <li className={`requirement ${/[0-9]/.test(newPw) ? 'met' : ''}`}>
                  <i className={`bi ${/[0-9]/.test(newPw) ? 'bi-check-circle' : 'bi-dash-circle'}`} /> Al menos un número
                </li>
                <li className={`requirement ${/[^A-Za-z0-9]/.test(newPw) ? 'met' : ''}`}>
                  <i className={`bi ${/[^A-Za-z0-9]/.test(newPw) ? 'bi-check-circle' : 'bi-dash-circle'}`} /> Al menos un carácter especial
                </li>
              </ul>
            </div>

            <button className="btn-change-password" onClick={changePassword}>
              <i className="bi bi-shield-check" /> Cambiar Contraseña
            </button>
          </div>
        </section>

        {/* ═══ CLAIM MACHINE ═══ */}
        <section className="claims-section">
          <div className="section-header">
            <h2><i className="bi bi-award" /> Reclamación de Autoría</h2>
            <p className="section-subtitle">Si eres el creador original de una máquina, reclámala aquí.</p>
          </div>
          <button className="btn-claim-machine" onClick={() => setShowClaimModal(true)}>
            <i className="bi bi-patch-plus" /> Reclamar Máquina
          </button>

          {/* admin: pending claims */}
          {isAdmin && dashData.claims.length > 0 && (
            <>
              <div className="section-header" style={{ marginTop: '2rem' }}>
                <h2><i className="bi bi-clipboard-check" /> Claims Pendientes</h2>
              </div>
              <div className="claims-list">
                {dashData.claims.map(c => (
                  <div key={c.id} className="claim-card">
                    <div className="claim-machine">{c.maquina_nombre}</div>
                    <ul className="claim-details">
                      <li><strong>Usuario:</strong> {c.username}</li>
                      <li><strong>Contacto:</strong> {c.contacto}</li>
                      <li className="claim-proof"><strong>Prueba:</strong> {c.prueba}</li>
                    </ul>
                    <div className="claim-date">{c.created_at ? new Date(c.created_at).toLocaleDateString('es-ES') : ''}</div>
                    <div className="claim-actions">
                      <button className="btn-approve" onClick={() => handleClaim(c.id, 'approve')}>
                        <i className="bi bi-check-lg" /> Aprobar
                      </button>
                      <button className="btn-reject" onClick={() => handleClaim(c.id, 'reject')}>
                        <i className="bi bi-x-lg" /> Rechazar
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      </div>

      {/* ═══ CLAIM MODAL ═══ */}
      {showClaimModal && (
        <div className="claim-modal" onClick={e => e.target === e.currentTarget && setShowClaimModal(false)}>
          <div className="claim-modal-dialog">
            <h2><i className="bi bi-patch-plus" /> Reclamar Máquina</h2>
            <p className="modal-description">Selecciona la máquina que creaste, proporciona tu contacto y una prueba de autoría.</p>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Máquina</label>
              <select className="dash-input" value={claimMachine} onChange={e => setClaimMachine(e.target.value)}>
                <option value="">-- Selecciona --</option>
                {dashData.machines.map(m => (
                  <option key={m.id} value={m.nombre}>{m.nombre} (autor actual: {m.autor || 'Sin autor'})</option>
                ))}
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Contacto (email, Twitter, Discord...)</label>
              <input className="dash-input" value={claimContact} onChange={e => setClaimContact(e.target.value)} />
            </div>
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Prueba de autoría</label>
              <textarea className="dash-input" rows={4} value={claimProof} onChange={e => setClaimProof(e.target.value)}
                placeholder="Describe la prueba de que eres el creador de esta máquina..." />
            </div>

            <div className="form-actions">
              <button className="btn-save" onClick={submitClaim}><i className="bi bi-send" /> Enviar</button>
              <button className="btn-cancel" onClick={() => setShowClaimModal(false)}><i className="bi bi-x-lg" /> Cancelar</button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ USERNAME CHANGE MODAL ═══ */}
      {showNameModal && (
        <div className="claim-modal" onClick={e => e.target === e.currentTarget && setShowNameModal(false)}>
          <div className="claim-modal-dialog">
            <h2><i className="bi bi-person-badge" /> Solicitar Cambio de Nombre</h2>
            <p className="modal-description">Solicita un nuevo nombre de usuario. Un administrador revisará tu petición.</p>

            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Nuevo nombre de usuario</label>
              <input className="dash-input" maxLength={20} value={reqUsername} onChange={e => setReqUsername(e.target.value)}
                placeholder="3-20 caracteres (letras, números, guion, guion bajo)" />
            </div>
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Motivo (opcional)</label>
              <textarea className="dash-input" rows={3} value={reqReason} onChange={e => setReqReason(e.target.value)} />
            </div>
            <div className="form-group" style={{ marginBottom: '1rem' }}>
              <label>Contacto alternativo (opcional)</label>
              <input className="dash-input" value={reqContact} onChange={e => setReqContact(e.target.value)} />
            </div>

            <div className="form-actions">
              <button className="btn-save" onClick={submitNameChange}><i className="bi bi-send" /> Enviar Solicitud</button>
              <button className="btn-cancel" onClick={() => setShowNameModal(false)}><i className="bi bi-x-lg" /> Cancelar</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
