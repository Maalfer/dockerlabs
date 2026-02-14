import React, { useEffect, useState } from 'react'
import './MachineModal.css'

function getCsrfToken() {
  return fetch('/api/csrf', { credentials: 'include' }).then(r => r.ok ? r.json() : {}).then(d => d.csrf_token || '')
}

export default function MachineModal({ open, data, onClose }){
  const [visible, setVisible] = useState(false)
  const [author, setAuthor] = useState({})
  const [rating, setRating] = useState({ average: null, user_rating: null })
  const [completed, setCompleted] = useState(false)
  const [showRatingModal, setShowRatingModal] = useState(false)
  const [scores, setScores] = useState({})

  useEffect(()=>{
    if (open) {
      setVisible(true)
    } else {
      setVisible(false)
    }
  }, [open])

  useEffect(()=>{
    if (!open || !data) return
    // fetch author profile
    fetch(`/api/author_profile?nombre=${encodeURIComponent(data.autor)}`)
      .then(r => r.ok ? r.json() : {})
      .then(d => setAuthor(d || {}))
      .catch(()=>{})
    // fetch rating
    fetch(`/api/get_machine_rating/${encodeURIComponent(data.nombre)}`)
      .then(r => r.ok ? r.json() : {})
      .then(d => setRating(d || {}))
      .catch(()=>{})
    // fetch completed status
    fetch(`/api/completed_machines/${encodeURIComponent(data.nombre)}`)
      .then(r => r.ok ? r.json() : {})
      .then(d => setCompleted(!!d.completed))
      .catch(()=>{})
    // fetch current user info to determine login state
    fetch('/api/me', { credentials: 'include' })
      .then(r => r.ok ? r.json() : {})
      .then(u => { if (u && u.username) window.currentUser = u; else window.currentUser = null })
      .catch(()=> { window.currentUser = null })
  }, [open, data])

  function close() {
    setVisible(false)
    setTimeout(()=> onClose && onClose(), 250)
  }

  async function toggleCompleted(){
    // require login (server will check)
    const prev = completed
    setCompleted(!prev)
    try{
      const token = await getCsrfToken()
      const res = await fetch('/api/toggle_completed_machine', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token },
        body: JSON.stringify({ machine_name: data.nombre })
      })
      const j = await res.json()
      if (j && j.success) setCompleted(!!j.completed)
      else setCompleted(prev)
    }catch(e){ setCompleted(prev) }
  }

  function openRating(){
    if (!completed) {
      alert('Debes marcar la máquina como completada antes de poder puntuarla.')
      return
    }
    setShowRatingModal(true)
  }

  async function submitRating(){
    // ensure all 4 criteria present
    if (Object.keys(scores).length < 4) { alert('Por favor valora todos los puntos.'); return }
    try{
      const token = await getCsrfToken()
      const res = await fetch('/api/rate_machine', {
        method: 'POST',
        headers: { 'Content-Type':'application/json', 'X-CSRFToken': token },
        body: JSON.stringify({ maquina_nombre: data.nombre, ...scores })
      })
      const j = await res.json()
      if (j && j.success) {
        alert('¡Puntuación registrada con éxito!')
        setShowRatingModal(false)
        // refresh rating
        fetch(`/api/get_machine_rating/${encodeURIComponent(data.nombre)}`).then(r=>r.ok?r.json():{}).then(d=>setRating(d||{}))
      } else {
        alert('Error: ' + (j.message || ''))
      }
    }catch(e){ alert('Error de red') }
  }

  if (!open || !data) return null

  const imgUrl = data.imagen ? `/static/${data.imagen.replace(/^\/+/, '')}` : '/static/dockerlabs/images/logos/logo.png'
  const diffLower = (data.dificultad || '').toLowerCase()
  const diffClass = diffLower === 'muy fácil' ? 'diff-muy-facil' : diffLower === 'fácil' ? 'diff-facil' : diffLower === 'medio' ? 'diff-medio' : diffLower === 'difícil' ? 'diff-dificil' : ''

  return (
    <div className={`overlay ${visible? 'visible' : ''}`} onClick={(e)=>{ if (e.target === e.currentTarget) close() }}>
      <div className={`popup ${visible? 'visible' : ''}`} style={ data.color ? { border: `2px solid ${data.color}`, boxShadow: `0 0 20px -5px ${data.color}, 0 25px 50px -12px rgba(0,0,0,0.5)` } : {} }>
        <div className="popup-image-container">
          <img className="popup-machine-image" src={imgUrl} alt={data.nombre} />
        </div>
        <div className="popup-content">
          <button className="modal-close-button" onClick={close}>&times;</button>
          <div className="header-row">
            <h1 className="machine-title">{data.nombre}</h1>
            <div className="rating-badge"><i className="bi bi-star-fill"></i> <span>{rating && rating.average ? parseFloat(rating.average).toFixed(1) : '--'}</span></div>
          </div>
          <div className={`difficulty-pill ${diffClass}`}>{data.dificultad}</div>

          <div className="creator-card">
            <img src={author.profile_image_url || '/static/dockerlabs/images/balu.webp'} className="creator-avatar" alt="avatar" />
            <div className="creator-info">
              <div className="creator-label">Creada por</div>
              <div className="creator-name"><a href={author.url || '#'} style={{color:'inherit', textDecoration:'none'}}>{data.autor}</a>
                <span className="creator-socials">{author.github_url? <a href={author.github_url} target="_blank" rel="noreferrer" className="social-icon"><i className="bi bi-github"></i></a> : null}</span>
              </div>
            </div>
            <div className="creation-date"><i className="bi bi-calendar3"></i> {data.fecha}</div>
          </div>

          <div className="action-area">
            { typeof window.currentUser === 'undefined' || !window.currentUser ? null : (
              <button className={`btn-mark-completed ${completed? 'completed':''}`} onClick={toggleCompleted}>{completed? (<><i className="bi bi-check-circle-fill"></i> Completada</>) : (<><i className="bi bi-circle"></i> Marcar como hecha</>) }</button>
            )}
            { (typeof window.currentUser === 'undefined' || !window.currentUser) ? <div style={{marginTop: '0.75rem', color:'#94a3b8'}}>Inicia sesión para marcar como hecha o puntuar.</div> : null }
          </div>

          <div className="modal-footer">
            <div>
              <div className="user-rating-label">Tu valoración:</div>
              <div id="modal-user-rating-stars" className="user-rating-stars">{rating && rating.user_rating ? Array.from({length:5}).map((_,i)=>(i < Math.round((Object.values(rating.user_rating||[]).reduce((a,b)=>a+b,0) || 0)/ (Object.values(rating.user_rating||[]).length||1)) ? <i key={i} className="bi bi-star-fill"></i> : <i key={i} className="bi bi-star"></i>)) : <i className="bi bi-star" /> }</div>
            </div>
            <div>
              <button className="btn-mark-completed" onClick={openRating} style={{width:'auto', padding:'0.6rem 1rem'}}><i className="bi bi-star"></i> Puntuar</button>
            </div>
          </div>

        </div>

        {showRatingModal && (
          <div className="overlay visible" style={{zIndex:11000}} onClick={(e)=>{ if (e.target === e.currentTarget) setShowRatingModal(false) }}>
            <div className="rating-modal-v2" style={{position:'relative'}}>
              <h3 style={{margin:0, marginBottom:'1rem'}}>Puntuar {data.nombre}</h3>
              {['dificultad_score','aprendizaje_score','recomendaria_score','diversion_score'].map((id,idx)=> (
                <div key={id} style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'1rem'}}>
                  <span style={{fontSize:'.9rem', color:'#cbd5e1'}}>{['Dificultad Acorde','Aprendizaje','Recomendaría','Diversión'][idx]}</span>
                  <div style={{color:'#f59e0b', cursor:'pointer'}}>
                    {Array.from({length:5}).map((_,i)=> (
                      <i key={i} className={ (scores[id]||0) > i ? 'bi bi-star-fill' : 'bi bi-star'} style={{marginLeft:4}} onClick={()=> setScores(s => ({...s, [id]: i+1}))} onMouseOver={()=>{}} />
                    ))}
                  </div>
                </div>
              ))}
              <div style={{display:'flex', gap:'1rem', marginTop:'1.5rem'}}>
                <button className="secondary-btn" onClick={()=> setShowRatingModal(false)}>Cancelar</button>
                <button className="primary-btn" onClick={submitRating}>Guardar</button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  )
}
