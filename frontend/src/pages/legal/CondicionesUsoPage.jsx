import React from 'react'
import { Link } from 'react-router-dom'
import './PolicyPage.css'

export default function CondicionesUsoPage() {
  return (
    <div className="container policy-page">
      <div className="policy-card">
        <h1 className="policy-title">Condiciones de Uso</h1>
        <div className="policy-content">
          <p className="lead">Bienvenido a <strong>DockerLabs</strong>. Al acceder y utilizar nuestro sitio web, aceptas cumplir con los siguientes términos y condiciones. Si no estás de acuerdo con alguna parte de estos términos, no debes utilizar nuestra plataforma.</p>
          <h3>1. Titularidad del Sitio Web</h3>
          <p>En cumplimiento con el deber de información recogido en el artículo 10 de la Ley 34/2002, de 11 de julio, de Servicios de la Sociedad de la Información y del Comercio Electrónico:</p>
          <ul>
            <li><strong>Titular:</strong> Mario Álvarez Fernandez</li>
            <li><strong>Email:</strong> info@elrincondelhacker.es</li>
            <li><strong>Sitio Web:</strong> DockerLabs.es</li>
            <li><strong>Actividad:</strong> Plataforma educativa de ciberseguridad y despliegue de laboratorios vulnerables.</li>
          </ul>
          <h3>2. Objeto y Uso de la Plataforma</h3>
          <p>DockerLabs es una plataforma diseñada exclusivamente con fines <strong>educativos y de aprendizaje</strong> en el ámbito de la ciberseguridad. Proporcionamos entornos controlados (laboratorios vulnerables basados en Docker) para que los usuarios puedan practicar y mejorar sus habilidades de hacking ético.</p>
          <p><strong>Queda terminantemente prohibido:</strong></p>
          <ul>
            <li>Utilizar los conocimientos adquiridos en esta plataforma para realizar ataques a sistemas reales sin autorización, actividades delictivas o cualquier acción que vulnere la ley vigente.</li>
            <li>Realizar ataques de denegación de servicio (DoS/DDoS) o cualquier acción que comprometa la integridad, disponibilidad o seguridad de la infraestructura de DockerLabs.</li>
            <li>Intentar acceder a cuentas de otros usuarios o extraer información de la base de datos de la plataforma.</li>
          </ul>
          <h3>3. Exención de Responsabilidad</h3>
          <p>DockerLabs proporciona laboratorios intencionalmente vulnerables. El usuario reconoce que el uso de estas herramientas y entornos conlleva riesgos inherentes. <strong>Mario Álvarez Fernandez</strong> no se hace responsable del mal uso que los usuarios puedan dar a la información o herramientas proporcionadas, ni de los daños que puedan causar a sus propios sistemas o a terceros derivados de la práctica fuera de los entornos controlados.</p>
          <h3>4. Propiedad Intelectual</h3>
          <p>Todos los contenidos del sitio web (textos, logotipos, laboratorios, código fuente) son propiedad de DockerLabs o de sus respectivos autores si se trata de contribuciones de la comunidad, y están protegidos por las leyes de propiedad intelectual.</p>
          <h3>5. Modificaciones</h3>
          <p>Nos reservamos el derecho de modificar estos términos en cualquier momento. Las modificaciones entrarán en vigor desde su publicación en este sitio web.</p>
        </div>
        <div className="policy-actions">
          <Link to="/" className="btn-home"><i className="bi bi-arrow-left"></i> Volver al Inicio</Link>
        </div>
      </div>
    </div>
  )
}
