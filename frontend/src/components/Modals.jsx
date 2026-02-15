import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import MachineModal from './MachineModal'
import './Modals.css'

export default function Modals({ state, open, close }) {
  const [machineModalOpen, setMachineModalOpen] = useState(false)
  const [machineData, setMachineData] = useState(null)

  useEffect(() => {
    function handler(e) {
      setMachineData(e.detail)
      setMachineModalOpen(true)
    }
    window.addEventListener('open-machine-modal', handler)
    return () => window.removeEventListener('open-machine-modal', handler)
  }, [])

  const closeAndNavigate = (key) => { close(key) }
  const [user, setUser] = useState({ role: null, username: null });

  useEffect(() => {
    if (state.dashboard || state.gestion) {
      fetch('/api/user/info')
        .then(res => {
          if (res.ok) return res.json();
          return { user: { role: null } };
        })
        .then(data => setUser(data.user || { role: null }))
        .catch(err => console.error("Error fetching user info", err));
    }
  }, [state.dashboard, state.gestion]);

  return (
    <>
      <div id="gestionWriteupsModal" className={`overlay ${state.gestion ? 'visible' : ''}`} onClick={(e) => { if (e.target === e.currentTarget) close('gestion') }}>
        <div className="popup" style={{ width: 'min(400px,90%)' }}>
          <button className="modal-close-button" type="button" onClick={() => close('gestion')}>&times;</button>
          <div className="modal-header"><h2 className="modal-title">Gestión writeups</h2></div>
          <div className="ranking-list">
            <Link to="/writeups-publicados" className="ranking-item" onClick={() => closeAndNavigate('gestion')}>
              <div className="user-info"><span className="user-name">Writeups publicados</span></div>
              <i className="bi bi-chevron-right" style={{ color: '#64748b' }}></i>
            </Link>
            {['admin', 'moderador'].includes(user.role) && (
              <Link to="/writeups-recibidos" className="ranking-item" onClick={() => closeAndNavigate('gestion')}>
                <div className="user-info"><span className="user-name">Writeups recibidos</span></div>
                <i className="bi bi-chevron-right" style={{ color: '#64748b' }}></i>
              </Link>
            )}
          </div>
        </div>
      </div>

      <div id="menuModal" className={`overlay ${state.menu ? 'visible' : ''}`} onClick={(e) => { if (e.target === e.currentTarget) close('menu') }}>
        <div className="popup" style={{ width: 'min(700px,95%)' }}>
          <button className="modal-close-button" type="button" onClick={() => close('menu')}>&times;</button>
          <div className="modal-header"><h2 className="modal-title">Menú</h2></div>
          <div className="ranking-list two-columns">
            <a href="https://app.secur0.com/vulnerability-disclosure/Dockerlabs" target="_blank" rel="noreferrer" className="ranking-item">
              <div className="user-info"><span className="user-name">Programa VDP</span></div>
              <i className="bi bi-box-arrow-up-right" style={{ color: '#64748b', fontSize: '0.9rem' }}></i>
            </a>

            <Link to="/instrucciones-uso" className="ranking-item" onClick={() => closeAndNavigate('menu')}>
              <div className="user-info"><span className="user-name">Instrucciones de Uso</span></div>
              <i className="bi bi-file-earmark-pdf" style={{ color: '#64748b' }}></i>
            </Link>

            <Link to="/enviar-maquina" className="ranking-item" onClick={() => closeAndNavigate('menu')}>
              <div className="user-info"><span className="user-name">Enviar Máquina</span></div>
              <i className="bi bi-chevron-right" style={{ color: '#64748b' }}></i>
            </Link>

            <Link to="/como-se-crea-una-maquina" className="ranking-item" onClick={() => closeAndNavigate('menu')}>
              <div className="user-info"><span className="user-name">Cómo se Crea una Máquina</span></div>
              <i className="bi bi-chevron-right" style={{ color: '#64748b' }}></i>
            </Link>

            <Link to="/estadisticas" className="ranking-item" onClick={() => closeAndNavigate('menu')}>
              <div className="user-info"><span className="user-name">Estadísticas</span></div>
              <i className="bi bi-bar-chart-line" style={{ color: '#64748b' }}></i>
            </Link>

            <a href="/docs/" target="_blank" rel="noreferrer" className="ranking-item">
              <div className="user-info"><span className="user-name">Swagger UI</span></div>
              <i className="bi bi-file-code" style={{ color: '#64748b' }}></i>
            </a>

            <Link to="/agradecimientos" className="ranking-item" onClick={() => closeAndNavigate('menu')}>
              <div className="user-info"><span className="user-name">Agradecimientos</span></div>
              <i className="bi bi-heart" style={{ color: '#64748b' }}></i>
            </Link>
          </div>
        </div>
      </div>

      <div id="dashboardModal" className={`overlay ${state.dashboard ? 'visible' : ''}`} onClick={(e) => { if (e.target === e.currentTarget) close('dashboard') }}>
        <div className="popup" style={{ width: 'min(700px,95%)' }}>
          <button className="modal-close-button" type="button" onClick={() => close('dashboard')}>&times;</button>
          <div className="modal-header">
            <h2 className="modal-title">Dashboard</h2>
            <div className="modal-subtitle">Opciones de usuario</div>
          </div>
          <div className="ranking-list two-columns">
            <Link to="/dashboard" className="ranking-item" onClick={() => closeAndNavigate('dashboard')}>
              <div className="user-info"><span className="user-name">Ir al Dashboard</span></div>
              <i className="bi bi-speedometer2" style={{ color: '#64748b' }}></i>
            </Link>

            <a href="/maquinas-hechas" className="ranking-item">
              <div className="user-info"><span className="user-name">Máquinas Completadas</span></div>
              <i className="bi bi-check-circle" style={{ color: '#64748b' }}></i>
            </a>

            {['admin', 'moderador'].includes(user.role) && (
              <>
                <a href="/peticiones" className="ranking-item">
                  <div className="user-info"><span className="user-name">Peticiones</span></div>
                  <i className="bi bi-inbox" style={{ color: '#64748b' }}></i>
                </a>
                <a href="/gestion-usuarios" className="ranking-item">
                  <div className="user-info"><span className="user-name">Gestión Usuarios</span></div>
                  <i className="bi bi-people" style={{ color: '#64748b' }}></i>
                </a>
              </>
            )}

            <Link to="/gestion-maquinas" className="ranking-item" onClick={() => closeAndNavigate('dashboard')}>
              <div className="user-info"><span className="user-name">Gestión Máquinas</span></div>
              <i className="bi bi-gear" style={{ color: '#64748b' }}></i>
            </Link>

            {user.role === 'admin' && (
              <>
                <Link to="/gestion-maquinas" className="ranking-item" onClick={() => closeAndNavigate('dashboard')}>
                  <div className="user-info"><span className="user-name">Añadir Máquina</span></div>
                  <i className="bi bi-plus-lg" style={{ color: '#64748b' }}></i>
                </Link>
                <Link to="/bunkerlabs/accesos" className="ranking-item" onClick={() => closeAndNavigate('dashboard')}>
                  <div className="user-info"><span className="user-name">Accesos Bunkerlabs</span></div>
                  <i className="bi bi-key" style={{ color: '#64748b' }}></i>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      <div id="messagingModal" className={`overlay ${state.messaging ? 'visible' : ''}`} onClick={(e) => { if (e.target === e.currentTarget) close('messaging') }}>
        <div className="popup" style={{ width: 'min(800px,95%)', padding: 0, overflow: 'hidden', borderRadius: 15 }}>
          <div className="modal-header" style={{ padding: '1rem', borderBottom: '1px solid #334155', background: '#0f172a' }}>
            <h2 className="modal-title" style={{ fontSize: '1.25rem' }}>Mensajes</h2>
          </div>
          <div className="modal-body">
            <div className="msg-sidebar" id="msgSidebar">
              <button className="msg-new-btn" onClick={() => { }}><i className="bi bi-pencil-square"></i> Nuevo Mensaje</button>
              <div id="msgNew" style={{ display: 'none', padding: '1rem' }}>
                <input type="text" id="newMsgUser" className="msg-input" placeholder="Buscar usuario..." autoComplete="off" />
                <div id="searchResults" className="search-results"></div>
                <button className="btn-auth" style={{ padding: '0.5rem', marginTop: '0.5rem', width: '100%', background: '#ef4444', color: '#fff', fontWeight: 'bold' }} onClick={() => { }}>Cancelar</button>
              </div>
              <div className="msg-list" id="msgList"><div style={{ padding: '1rem', textAlign: 'center', color: '#94a3b8' }}>Cargando...</div></div>
            </div>
            <div className="msg-content" id="msgContent">
              <div className="msg-chat-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center' }}><i className="bi bi-arrow-left msg-back-btn"></i><span id="chatUserName">Selecciona un chat</span></div>
                <i className="bi bi-trash" id="deleteChatBtn" style={{ cursor: 'pointer', color: '#ef4444', display: 'none', fontSize: '1.2rem' }} title="Eliminar conversación"></i>
              </div>
              <div className="msg-chat-messages" id="chatMessages"><div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: '#64748b' }}><p>Selecciona una conversación para empezar</p></div></div>
              <div className="msg-input-area" id="inputArea" style={{ display: 'none' }}>
                <input type="text" id="messageInput" className="msg-input" placeholder="Escribe un mensaje..." />
                <button className="msg-send-btn"><i className="bi bi-send"></i></button>
              </div>
            </div>
          </div>
        </div>
      </div>
      {machineModalOpen && (
        <MachineModal open={machineModalOpen} data={machineData} onClose={() => { setMachineModalOpen(false); setMachineData(null) }} />
      )}
    </>
  )
}
