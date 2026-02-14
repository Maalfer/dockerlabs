import React, { useEffect, useState } from 'react'

export default function DashboardPage(){
  const [me, setMe] = useState(null)
  const [maquinas, setMaquinas] = useState([])

  useEffect(()=>{
    // load dashboard.css
    const id = 'dashboard-page-css'
    if (!document.getElementById(id)){
      const link = document.createElement('link')
      link.id = id
      link.rel = 'stylesheet'
      link.href = '/static/dockerlabs/css/dashboard.css'
      document.head.appendChild(link)
    }

    fetch('/api/me', { credentials: 'include' })
      .then(r=> r.ok ? r.json() : null)
      .then(d=> { if (d && d.authenticated) setMe(d) })
      .catch(()=>{})

    fetch('/api/maquinas')
      .then(r=> r.ok ? r.json() : [])
      .then(list => setMaquinas(list || []))
      .catch(()=>{})
  },[])

  if (!me) return (<div className="container" style={{paddingTop: '80px'}}><p>Cargando dashboard...</p></div>)

  return (
    <div className="dashboard-container" style={{paddingTop: '80px'}}>
      <div className="dashboard-header">
        <div className="welcome-section">
          <h1>Dashboard</h1>
          <p className="welcome-text">Bienvenido de nuevo, <span className="username">{me.username}</span></p>
        </div>
        <div className="dashboard-actions">
          <button type="button" className="btn-claim-machine" onClick={()=>{ document.getElementById('claimMachineModal')?.classList?.add('open') }}>
            <i className="bi bi-flag"></i> Reclamar Autoría Máquina
          </button>
        </div>
      </div>

      <div className="dashboard-content">
        <div className="profile-section">
          <div className="section-header"><h2><i className="bi bi-person-circle"></i> Perfil de Usuario</h2></div>
          <div className="profile-content">
            <div className="profile-picture-section">
              <div className="profile-picture-container">
                <img src={me.profile_image_url} alt="Foto de perfil" className="profile-picture" id="profilePicture" />
              </div>
              <p className="photo-help-text">Haz clic en la cámara para cambiar tu foto de perfil</p>
              <div className="social-links-section mt-4">
                <h5 style={{fontSize:'.9rem', marginBottom:'12px', color:'var(--text-primary)'}}><i className="bi bi-link-45deg"></i> Redes Sociales</h5>
                <div className="form-group mb-2">
                  <label style={{fontSize:'.85rem'}}><i className="bi bi-linkedin" style={{color:'#0077B5'}}></i> LinkedIn</label>
                  <input defaultValue={me.linkedin_url || ''} id="linkedin_url" className="form-control form-control-sm" />
                </div>
                <div className="form-group mb-2">
                  <label style={{fontSize:'.85rem'}}><i className="bi bi-github" style={{color:'#333'}}></i> GitHub</label>
                  <input defaultValue={me.github_url || ''} id="github_url" className="form-control form-control-sm" />
                </div>
                <div className="form-group mb-2">
                  <label style={{fontSize:'.85rem'}}><i className="bi bi-youtube" style={{color:'#FF0000'}}></i> YouTube</label>
                  <input defaultValue={me.youtube_url || ''} id="youtube_url" className="form-control form-control-sm" />
                </div>
                <div style={{marginTop:'1rem'}}>
                  <button className="btn-save" onClick={async ()=>{
                    const payload = { linkedin_url: document.getElementById('linkedin_url').value, github_url: document.getElementById('github_url').value, youtube_url: document.getElementById('youtube_url').value }
                    const token = await fetch('/api/csrf').then(r=>r.ok?r.json():{}).then(d=>d.csrf_token||'')
                    const res = await fetch('/api/update_social_links', { method:'POST', credentials:'include', headers: { 'Content-Type':'application/json', 'X-CSRFToken': token }, body: JSON.stringify(payload) })
                    if (res.ok) alert('Enlaces actualizados')
                    else alert('Error al actualizar')
                  }}>Guardar enlaces</button>
                </div>
              </div>
            </div>

            <div className="profile-info-section">
              <div className="form-group">
                <label><i className="bi bi-person"></i> Nombre de usuario</label>
                <div className="profile-display-field">{me.username}</div>
              </div>
              <div className="form-group">
                <label><i className="bi bi-envelope"></i> Correo electrónico</label>
                <div className="profile-display-field">{me.email || 'No especificado'}</div>
              </div>
              <div className="form-group">
                <label><i className="bi bi-card-text"></i> Biografía</label>
                <textarea id="bio" className="form-control" rows={3} defaultValue={me.biography || ''}></textarea>
                <div style={{marginTop:'.75rem'}}>
                  <button className="btn-save" onClick={async ()=>{
                    const token = await fetch('/api/csrf').then(r=>r.ok?r.json():{}).then(d=>d.csrf_token||'')
                    const res = await fetch('/api/update_profile', { method:'POST', credentials:'include', headers: { 'Content-Type':'application/json', 'X-CSRFToken': token }, body: JSON.stringify({ biography: document.getElementById('bio').value }) })
                    if (res.ok) alert('Perfil actualizado')
                    else { const j = await res.json(); alert(j.error||'Error') }
                  }}>Guardar biografía</button>
                </div>
            </div>
            </div>
        </div>

        <div className="security-section">
          <div className="section-header"><h2><i className="bi bi-shield-lock"></i> Seguridad</h2></div>
          <div className="security-content">
            <div className="form-group">
              <label><i className="bi bi-key"></i> Contraseña Actual</label>
              <input type="password" id="currentPassword" className="form-control" />
            </div>
            <div className="form-group">
              <label><i className="bi bi-key-fill"></i> Nueva Contraseña</label>
              <input type="password" id="newPassword" className="form-control" />
            </div>
            <div style={{marginTop:'.75rem'}}>
              <button id="btnChangePassword" className="btn-save" onClick={async ()=>{
                const token = await fetch('/api/csrf').then(r=>r.ok?r.json():{}).then(d=>d.csrf_token||'')
                const payload = { current_password: document.getElementById('currentPassword').value, new_password: document.getElementById('newPassword').value }
                const res = await fetch('/api/change_password', { method:'POST', credentials:'include', headers: { 'Content-Type':'application/json', 'X-CSRFToken': token }, body: JSON.stringify(payload) })
                if (res.ok) alert('Contraseña actualizada')
                else { const j = await res.json(); alert(j.error||'Error') }
              }}>Actualizar contraseña</button>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
