import React, { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import Header from './components/Header'
import Home from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import Footer from './components/Footer'
import Modals from './components/Modals'

export default function App() {
  const [modalState, setModalState] = useState({ menu: false, dashboard: false, messaging: false, gestion: false })

  const open = (key) => setModalState(s => ({ ...s, [key]: true }))
  const close = (key) => setModalState(s => ({ ...s, [key]: false }))

  return (
    <div>
      <Header openModal={open} />
      <main style={{ paddingTop: '48px' }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
        </Routes>
      </main>
      <Footer />
      <Modals state={modalState} open={open} close={close} />
    </div>
  )
}
