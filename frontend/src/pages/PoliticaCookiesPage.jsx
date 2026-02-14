import React from 'react'
import { Link } from 'react-router-dom'
import './PolicyPage.css'

export default function PoliticaCookiesPage() {
  return (
    <div className="container policy-page">
      <div className="policy-card">
        <h1 className="policy-title">Política de Cookies</h1>
        <div className="policy-content">
          <p className="lead">En <strong>DockerLabs</strong> utilizamos cookies para facilitar el uso de nuestra página web y mejorar la experiencia del usuario. A continuación, detallamos qué son las cookies, cuáles utilizamos y cómo puedes gestionarlas.</p>
          <h3>1. ¿Qué son las Cookies?</h3>
          <p>Las cookies son pequeños archivos de texto que los sitios web almacenan en su ordenador o dispositivo móvil cuando los visita. Permiten que el sitio web recuerde sus acciones y preferencias (como el inicio de sesión) durante un período de tiempo.</p>
          <h3>2. Cookies que Utilizamos</h3>
          <p>DockerLabs utiliza únicamente <strong>cookies técnicas y de sesión</strong>, necesarias para el correcto funcionamiento de la plataforma:</p>
          <ul>
            <li><strong>session:</strong> Una cookie esencial para gestionar su sesión de usuario una vez ha iniciado sesión. Nos permite identificarle mientras navega por la plataforma.</li>
          </ul>
          <p>No utilizamos cookies de terceros, publicitarias ni de rastreo de comportamiento para fines comerciales.</p>
          <h3>3. Gestión de Cookies</h3>
          <p>Dado que nuestras cookies son estrictamente necesarias para el funcionamiento del área de usuarios (login y registro), si decide bloquearlas a través de la configuración de su navegador, es posible que no pueda iniciar sesión o utilizar correctamente la plataforma.</p>
        </div>
        <div className="policy-actions">
          <Link to="/" className="btn-home"><i className="bi bi-arrow-left"></i> Volver al Inicio</Link>
        </div>
      </div>
    </div>
  )
}
