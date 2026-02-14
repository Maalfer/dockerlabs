import React from 'react'

function Overlay({ visible, children, onClose, style }){
  return (
    <div className={`overlay ${visible ? 'visible' : ''}`} onClick={(e)=>{ if(e.target === e.currentTarget) onClose() }}>
      <div className="popup" style={style}>
        <button className="modal-close-button" type="button" onClick={onClose}>&times;</button>
        {children}
      </div>
    </div>
  )
}

export default function Modals({ state, close }){
  return (
    <>
      <Overlay visible={state.gestion} onClose={()=>close('gestion')} style={{width:'min(400px,90%)'}}>
        <div className="modal-header"><h2 className="modal-title">Gestión writeups</h2></div>
        <div className="ranking-list"> <a className="ranking-item">Writeups publicados</a> </div>
      </Overlay>

      <Overlay visible={state.menu} onClose={()=>close('menu')} style={{width:'min(700px,95%)'}}>
        <div className="modal-header"><h2 className="modal-title">Menú</h2></div>
        <div className="ranking-list two-columns">
          <a className="ranking-item">Instrucciones de Uso</a>
        </div>
      </Overlay>

      <Overlay visible={state.dashboard} onClose={()=>close('dashboard')} style={{width:'min(700px,95%)'}}>
        <div className="modal-header"><h2 className="modal-title">Dashboard</h2></div>
        <div className="ranking-list two-columns">
          <a className="ranking-item">Ir al Dashboard</a>
        </div>
      </Overlay>

      <Overlay visible={state.messaging} onClose={()=>close('messaging')} style={{width:'min(800px,95%)', padding:0}}>
        <div className="modal-header"><h2 className="modal-title">Mensajes</h2></div>
        <div className="modal-body"><p>Mensajería integrada (implementar)</p></div>
      </Overlay>
    </>
  )
}
