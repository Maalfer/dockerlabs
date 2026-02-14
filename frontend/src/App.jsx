import React, { useState } from 'react'
import Header from './components/Header'
import Home from './pages/HomePage'
import Footer from './components/Footer'
import Modals from './components/Modals'

export default function App() {
  const [modalState, setModalState] = useState({ menu: false, dashboard: false, messaging: false, gestion: false })

  const open = (key) => setModalState(s => ({ ...s, [key]: true }))
  const close = (key) => setModalState(s => ({ ...s, [key]: false }))

  return (
    <div>
      <Header openModal={open} />
      <main style={{ paddingTop: '100px' }}>
        <Home />
      </main>
      <Footer />
      <Modals state={modalState} open={open} close={close} />
    </div>
  )
}
