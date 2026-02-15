import React, { useState } from 'react'
import { Routes, Route, Outlet } from 'react-router-dom'
import Header from './components/layout/Header'
import Home from './pages/general/HomePage'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import DashboardPage from './pages/dashboard/DashboardPage'
import RecoverPage from './pages/auth/RecoverPage'
import EstadisticasPage from './pages/info/EstadisticasPage'
import InstruccionesUsoPage from './pages/info/InstruccionesUsoPage'
import EnviarMaquinaPage from './pages/admin/EnviarMaquinaPage'
import ComoSeCreaUnaMaquinaPage from './pages/info/ComoSeCreaUnaMaquinaPage'
import AgradecimientosPage from './pages/info/AgradecimientosPage'
import PoliticaPrivacidadPage from './pages/legal/PoliticaPrivacidadPage'
import PoliticaCookiesPage from './pages/legal/PoliticaCookiesPage'
import CondicionesUsoPage from './pages/legal/CondicionesUsoPage'
import NotFoundPage from './pages/general/NotFoundPage'
import ForbiddenPage from './pages/auth/ForbiddenPage'
import Footer from './components/layout/Footer'
import Modals from './components/layout/Modals'
import WriteupsPublicadosPage from './pages/writeups/WriteupsPublicadosPage'
import WriteupsRecibidosPage from './pages/writeups/WriteupsRecibidosPage'
import GestionMaquinasPage from './pages/admin/GestionMaquinasPage';
import MaquinasCompletadasPage from './pages/machines/MaquinasCompletadasPage';
import AddMachinePage from './pages/admin/AddMachinePage';
import GestionUsuariosPage from './pages/admin/GestionUsuariosPage';
import PeticionesPage from './pages/admin/PeticionesPage';

// BunkerLabs pages (own layout)
import BunkerLoginPage from './pages/bunker/BunkerLoginPage'
import BunkerHomePage from './pages/bunker/BunkerHomePage'
import BunkerAccesosPage from './pages/bunker/BunkerAccesosPage'

/* Layout wrapper for DockerLabs routes (Header + Footer + Modals) */
function DockerLabsLayout({ modalState, open, close }) {
  return (
    <>
      <Header openModal={open} />
      <main>
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
          <Route path="/gestion-maquinas" element={<GestionMaquinasPage />} />
          <Route path="/add-maquina" element={<AddMachinePage />} />
          <Route path="/gestion-usuarios" element={<GestionUsuariosPage />} />
          <Route path="/peticiones" element={<PeticionesPage />} />
          <Route path="/maquinas-hechas" element={<MaquinasCompletadasPage />} />
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
