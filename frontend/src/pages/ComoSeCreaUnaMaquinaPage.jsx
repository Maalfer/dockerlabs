import React from 'react'
import './ContentPage.css'

export default function ComoSeCreaUnaMaquinaPage() {
  return (
    <div className="container content-page">
      <h1 className="title">Cómo se Crea una Máquina</h1>
      <p className="mt-4">
        En esta sección aprenderás el proceso completo para crear una máquina para DockerLabs.
        Además, al final de esta página encontrarás un vídeo donde se explica paso a paso cómo
        construir y preparar correctamente una máquina lista para publicar en la plataforma.
      </p>

      <div className="como_se_crea_una_maquina-card p-4 mt-4">
        <h2 className="subtitle">Pasos generales</h2>
        <ol className="mt-3">
          <li>Diseñar el flujo y la estructura de la máquina.</li>
          <li>Configurar los servicios vulnerables.</li>
          <li>Añadir pistas, detalles y la documentación necesaria.</li>
          <li>Realizar pruebas internas para verificar que todo funcione correctamente.</li>
          <li>Empaquetar la máquina en un archivo TAR o ZIP siguiendo las directrices de DockerLabs.</li>
        </ol>
      </div>

      <div className="como_se_crea_una_maquina-card p-4 mt-4">
        <h2 className="subtitle">Reglas para creadores</h2>
        <ul className="mt-3">
          <h4>1. EXCLUSIVIDAD CON LA PLATAFORMA</h4>
          <p>Las máquinas no podrán ser publicadas en otras plataformas.</p>
          <h4>2. LÍMITE DE FUERZA BRUTA</h4>
          <p>Si se emplea fuerza bruta para realizar la máquina la contraseña debe estar entre las primeras 5000 líneas del rockyou.txt.</p>
          <div className="alert-warning">
            <i className="bi bi-exclamation-octagon-fill"></i> Si la contraseña se encuentra +5000 líneas del rockyou.txt, la máquina será rechazada. Si es necesario para la explotación puede contactar con los Administradores/Moderadores mediante el servidor de Discord para solicitar una excepción.
          </div>
          <h4>3. ARCHIVOS DE REGISTRO</h4>
          <p>Elimina o redirige los archivos de historial <i>(.bash_history, .mysql_history...)</i> al <i>/dev/null</i> a menos que sea necesario para la explotación.</p>
          <h4>4. DOMINIO</h4>
          <p>Si la máquina requiere un dominio debe acabar en <code>.dl</code>.</p>
          <h4>5. ORIGINALIDAD</h4>
          <p>Innovar es nuestra prioridad. Evitar el uso de técnicas repetitivas <i>(como fuerza bruta al SSH)</i>.</p>
          <div className="alert-warning">
            <i className="bi bi-exclamation-octagon-fill"></i> Si ya existe una máquina con el mismo modo de explotación que la tuya será rechazada.
          </div>
        </ul>
      </div>

      <div className="como_se_crea_una_maquina-card p-4 mt-5 mb-5">
        <h2 className="subtitle"><i className="bi bi-youtube" style={{ color: 'red' }}></i> Cómo crear una máquina para DockerLabs</h2>
        <p className="mt-3">
          En el siguiente vídeo puedes ver de forma práctica y detallada todo el procedimiento necesario para crear tu propia máquina para DockerLabs:
        </p>
        <div className="ratio ratio-16x9 mt-4" style={{ maxWidth: 800, margin: '1rem auto' }}>
          <iframe
            src="https://www.youtube.com/embed/kDAK9Wc8o_k?si=rdVgMLVaYB7fLvc3"
            title="YouTube video player"
            allowFullScreen
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            style={{ border: 0, borderRadius: 10, width: '100%', height: '100%' }}
          />
        </div>
      </div>
    </div>
  )
}
