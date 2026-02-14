import React, { useState } from 'react'
import { Routes, Route, Outlet } from 'react-router-dom'
import Header from './components/Header'
import Home from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import RecoverPage from './pages/RecoverPage'
import EstadisticasPage from './pages/EstadisticasPage'
import InstruccionesUsoPage from './pages/InstruccionesUsoPage'
import EnviarMaquinaPage from './pages/EnviarMaquinaPage'
import ComoSeCreaUnaMaquinaPage from './pages/ComoSeCreaUnaMaquinaPage'
import AgradecimientosPage from './pages/AgradecimientosPage'
import PoliticaPrivacidadPage from './pages/PoliticaPrivacidadPage'
import PoliticaCookiesPage from './pages/PoliticaCookiesPage'
import CondicionesUsoPage from './pages/CondicionesUsoPage'
import NotFoundPage from './pages/NotFoundPage'
import ForbiddenPage from './pages/ForbiddenPage'
import Footer from './components/Footer'
import Modals from './components/Modals'
import WriteupsPublicadosPage from './pages/WriteupsPublicadosPage'
import WriteupsRecibidosPage from './pages/WriteupsRecibidosPage'

// BunkerLabs pages (own layout)
import BunkerLoginPage from './pages/BunkerLoginPage'
import BunkerHomePage from './pages/BunkerHomePage'
import BunkerAccesosPage from './pages/BunkerAccesosPage'

/* Layout wrapper for DockerLabs routes (Header + Footer + Modals) */
function DockerLabsLayout({ modalState, open, close }) {
  return (
    <>
      <Header openModal={open} />
      <main style={{ paddingTop: '48px' }}>
        <Outlet />
      </main>
      <Footer />
      <Modals state={modalState} open={open} close={close} />
    </>
  )
}

import { AuthProvider } from './context/AuthContext'

export default function App() {
  const [modalState, setModalState] = useState({ menu: false, dashboard: false, messaging: false, gestion: false })

  const open = (key) => setModalState(s => ({ ...s, [key]: true }))
  const close = (key) => setModalState(s => ({ ...s, [key]: false }))

  return (
    <AuthProvider>
      <Routes>
        {/* BunkerLabs routes (own layout, no DockerLabs header/footer) */}
        <Route path="/bunkerlabs/login" element={<BunkerLoginPage />} />
        <Route path="/bunkerlabs/accesos" element={<BunkerAccesosPage />} />
        <Route path="/bunkerlabs" element={<BunkerHomePage />} />

        {/* DockerLabs routes (wrapped with Header/Footer via layout route) */}
        <Route element={<DockerLabsLayout modalState={modalState} open={open} close={close} />}>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/recover" element={<RecoverPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/estadisticas" element={<EstadisticasPage />} />
          <Route path="/writeups-publicados" element={<WriteupsPublicadosPage />} />
          <Route path="/writeups-recibidos" element={<WriteupsRecibidosPage />} />
          <Route path="/instrucciones-uso" element={<InstruccionesUsoPage />} />
          <Route path="/enviar-maquina" element={<EnviarMaquinaPage />} />
          <Route path="/como-se-crea-una-maquina" element={<ComoSeCreaUnaMaquinaPage />} />
          <Route path="/agradecimientos" element={<AgradecimientosPage />} />
          <Route path="/politica-privacidad" element={<PoliticaPrivacidadPage />} />
          <Route path="/politica-cookies" element={<PoliticaCookiesPage />} />
          <Route path="/condiciones-uso" element={<CondicionesUsoPage />} />
          <Route path="/403" element={<ForbiddenPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </AuthProvider>
  )
}


