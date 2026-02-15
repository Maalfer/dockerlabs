import React from 'react'
import { Link } from 'react-router-dom'
import './PolicyPage.css'

export default function PoliticaPrivacidadPage() {
  return (
    <div className="container policy-page">
      <div className="policy-card">
        <h1 className="policy-title">Política de Privacidad</h1>
        <div className="policy-content">
          <p className="lead">En <strong>DockerLabs</strong>, nos comprometemos a proteger tu privacidad y tus datos personales. Esta Política de Privacidad explica cómo recopilamos, usamos y protegemos tu información, en cumplimiento con el Reglamento General de Protección de Datos (RGPD).</p>
          <h3>1. Responsable del Tratamiento</h3>
          <ul>
            <li><strong>Responsable:</strong> Mario Álvarez Fernandez</li>
            <li><strong>Email:</strong> info@elrincondelhacker.es</li>
            <li><strong>Contacto:</strong> A través de los canales oficiales de la plataforma.</li>
          </ul>
          <h3>2. Datos que Recopilamos</h3>
          <p>Para el funcionamiento de la plataforma y la gestión de usuarios, <strong>únicamente</strong> recopilamos y almacenamos los siguientes datos personales:</p>
          <ul>
            <li><strong>Nombre de usuario (Username):</strong> Para identificarte en la plataforma, rankings y resolución de máquinas.</li>
            <li><strong>Correo electrónico:</strong> Para la recuperación de contraseñas y notificaciones importantes del servicio.</li>
          </ul>
          <p>No recopilamos nombres reales, direcciones, teléfonos ni datos bancarios. La contraseña se almacena de forma encriptada (hasheada) y es inaccesible incluso para los administradores.</p>
          <h3>3. Finalidad del Tratamiento</h3>
          <ul>
            <li>Gestionar su registro y acceso a la plataforma "DockerLabs".</li>
            <li>Mantener un registro de su progreso en los laboratorios (puntos y rankings).</li>
            <li>Enviar comunicaciones relacionadas con la seguridad de su cuenta (ej. recuperación de contraseña).</li>
          </ul>
          <h3>4. Legitimación y Conservación</h3>
          <p>La base legal para el tratamiento de sus datos es el <strong>consentimiento</strong> del usuario al registrarse voluntariamente en la plataforma. Los datos se conservarán mientras el usuario mantenga su cuenta activa. Puede solicitar la eliminación de su cuenta y sus datos en cualquier momento.</p>
          <h3>5. Cesión de Datos</h3>
          <p>Sus datos (nombre de usuario y correo) <strong>no se cederán a terceros</strong> bajo ningún concepto, salvo obligación legal.</p>
          <h3>6. Derechos del Usuario</h3>
          <p>Tiene derecho a acceder, rectificar y suprimir sus datos, así como a limitar u oponerse a su tratamiento. Para ejercer estos derechos, puede ponerse en contacto con la administración de la plataforma.</p>
        </div>
        <div className="policy-actions">
          <Link to="/" className="btn-home"><i className="bi bi-arrow-left"></i> Volver al Inicio</Link>
        </div>
      </div>
    </div>
  )
}
