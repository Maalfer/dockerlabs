import React from 'react'
import './ContentPage.css'

export default function InstruccionesUsoPage() {
  return (
    <div className="container content-page">
      <h1 className="title">Instrucciones de uso</h1>
      <div className="intrucciones_de_uso-card p-4 mt-4">
        <h2 className="subtitle">REQUISITOS PREVIOS</h2>
        <p>Para que las máquinas de DockerLabs puedan funcionar, Docker debe estar instalado en tu sistema:</p>
        <ul>
          <li>Debian: <a href="https://docs.docker.com/engine/install/debian/" target="_blank" rel="noreferrer">Instalar Docker Debian</a></li>
          <li>Arch Linux: <a href="https://docs.docker.com/desktop/setup/install/linux/archlinux/" target="_blank" rel="noreferrer">Instalar Docker Arch Linux</a></li>
          <li>Fedora: <a href="https://docs.docker.com/engine/install/fedora/" target="_blank" rel="noreferrer">Instalar Docker Fedora</a></li>
        </ul>
        <div className="alert-hint"><i className="bi bi-exclamation-circle-fill"></i> El <code>auto_deploy.sh</code> detecta si no tenemos Docker instalado y lo instalará automáticamente.</div>

        <h2 className="subtitle">CÓMO EJECUTAR LAS MÁQUINAS</h2>
        <p>Una vez hayamos descargado una máquina en formato <code>.tar</code>, veremos que hay un script llamado <code>auto_deploy.sh</code> junto con cada máquina, por lo que solamente tendremos que ejecutar ese script para desplegar o borrar el laboratorio.</p>
        <div className="content-center">
          <img src="/static/dockerlabs/images/instrucciones/1.png" alt="Instrucción 1" />
          <code>❯ sudo bash auto_deploy.sh laboratorio.tar</code>
        </div>

        <h2 className="subtitle">CÓMO EJECUTAR LAS MÁQUINAS DE PIVOTING</h2>
        <p>Una vez que hayamos descargado y descomprimido una máquina de pivoting veremos varios <code>.tar</code> etiquetados en orden <code>máquina1.tar máquina2.tar máquina3.tar</code> y su respectivo script <code>auto_deploy.sh</code> que montará la red pivoting automáticamente:</p>
        <div className="content-center">
          <img src="/static/dockerlabs/images/instrucciones/2.png" alt="Instrucción 2" />
          <code>❯ sudo bash auto_deploy.sh máquina1.tar máquina2.tar máquina3.tar máquina4.tar</code>
        </div>

        <h2 className="subtitle">CÓMO ELIMINAR LAS MÁQUINAS</h2>
        <p>Una vez hayamos terminado con el laboratorio, simplemente pulsamos <code>control + C</code> y todo el laboratorio se habrá eliminado del sistema.</p>
        <img src="/static/dockerlabs/images/instrucciones/3.png" alt="Instrucción 3" className="content-img" />
        <p>En el caso de una máquina de pivoting nos preguntará lo siguiente:</p>
        <img src="/static/dockerlabs/images/instrucciones/4.png" alt="Instrucción 4" className="content-img full-width" />
        <p>Si estamos de acuerdo y no nos preocupa perder otras imágenes docker que podamos tener le indicaremos que <b>Sí</b>. Si tiene imágenes de docker que le interesa mantener le indicamos que <b>No</b> y podrán borrar las imágenes manualmente.</p>
        <div className="content-center">
          <img src="/static/dockerlabs/images/instrucciones/5.png" alt="Instrucción 5" className="full-width" />
          <i>(Ejemplo con la opción Sí)</i>
        </div>

        <h2 className="subtitle">SOLUCIÓN DE ERRORES</h2>
        <p>Es posible que en algunos casos puntuales se pueda experimentar algún error. Proporcionamos una serie de comandos para solucionar la mayoría de errores:</p>
        <ul>
          <li><code>❯ sudo systemctl restart docker</code></li>
          <li><code>❯ sudo docker stop $(docker ps -q)</code></li>
          <li><code>❯ sudo docker container prune force</code></li>
        </ul>
      </div>
    </div>
  )
}
