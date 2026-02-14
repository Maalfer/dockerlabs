import React from 'react'
import './ContentPage.css'

export default function EnviarMaquinaPage() {
  return (
    <div className="container content-page">
      <h1 className="title">Enviar Máquina</h1>
      <p className="mt-4">
        En DockerLabs, las máquinas enviadas por la comunidad son una parte fundamental del proyecto.
        Actualmente, las máquinas se suben de forma manual una por una por <strong>El Pingüino de Mario</strong>,
        por lo que el proceso puede tardar un poco dependiendo de su disponibilidad.
      </p>

      <div className="enviar_maquina-card p-4 mt-4">
        <h2 className="subtitle">¿Cómo avisar correctamente de que tienes una máquina lista?</h2>
        <p className="mt-3">
          La forma más recomendada y rápida es avisar a través del servidor oficial de Discord,
          en el canal <strong>#dockerlabs</strong>, mencionando a los moderadores. Esto garantiza que el equipo
          se entere cuanto antes y pueda revisar tu máquina para publicarla.
        </p>
        <p className="mt-3">
          También es posible contactar directamente a El Pingüino de Mario mediante LinkedIn, pero al ser un
          mensaje privado es posible que tarde más tiempo en verlo.
        </p>
        <div className="mt-4 text-center">
          <a href="https://discord.com/invite/dD3yVejBUR" target="_blank" rel="noreferrer" className="btn btn-primary">
            <i className="bi bi-discord"></i> Unirse al servidor de Discord
          </a>
        </div>
      </div>

      <div className="enviar_maquina-card p-4 mt-4">
        <h2 className="subtitle">Requisitos</h2>
        <ul className="mt-3">
          <li>La máquina debe ser original.</li>
          <li>Debe incluir un PDF/documento explicando su resolución.</li>
          <li>Debe contener al menos una vulnerabilidad explotable en cada fase <i>(Intrusión/Escalada de privilegios)</i>.</li>
          <li>Debe enviarse en formato ZIP <i>(Con su auto_deploy.sh y .tar)</i> o TAR.</li>
          <li>No se requieren flags en la máquina.</li>
        </ul>
        <div className="alert-warning">
          <i className="bi bi-exclamation-octagon-fill"></i> Si se envía una máquina sin writeup puede ser rechazada.
        </div>
      </div>

      <div className="enviar_maquina-card p-4 mt-4 mb-5">
        <h2 className="subtitle">Proceso de Envío</h2>
        <p className="mt-3">
          Para aportar tu máquina, súbela a cualquier servicio de alojamiento (Drive, Mega, etc.)
          y comparte el enlace con el equipo a través de Discord o LinkedIn. Una vez revisada,
          será añadida a la plataforma manualmente.
        </p>
        <div className="alert-hint">
          <i className="bi bi-exclamation-circle-fill"></i> Si quieres ver un ejemplo de writeup puedes darle un vistazo a{' '}
          <a href="https://mega.nz/file/7cNzjJBL#74J4tjoHRF_URnduGxixoaB8MOrMnAE5eZQnLlwDoxY" target="_blank" rel="noreferrer">la plantilla de ejemplo Dockerlabs</a>.
        </div>
      </div>
    </div>
  )
}
