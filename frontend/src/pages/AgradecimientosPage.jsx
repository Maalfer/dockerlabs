import React from 'react'
import './ContentPage.css'

const colaboradores = [
  { name: 'D1se0', url: 'https://github.com/D1se0', img: '/static/dockerlabs/images/agradecimientos/diseo.png', glow: 'glow-dise0' },
  { name: 'The Hackers Labs', url: 'https://thehackerslabs.com/', img: '/static/dockerlabs/images/agradecimientos/thl.png', glow: 'glow-thl' },
  { name: 'HackMyVM', url: 'https://hackmyvm.eu/', img: '/static/dockerlabs/images/agradecimientos/hmv.png', glow: 'glow-hackmyvm' },
  { name: 'Pylon', url: 'https://github.com/Pylonet', img: '/static/dockerlabs/images/agradecimientos/pylon.jpg', glow: 'glow-pylon' },
  { name: 'Santitub', url: 'https://github.com/Santitub', img: '/static/dockerlabs/images/agradecimientos/santitub.png', glow: 'glow-santitub' },
  { name: 'Maciiii__', url: 'https://github.com/Maciferna', img: '/static/dockerlabs/images/agradecimientos/maci.png', glow: 'glow-maciferna' }
]

export default function AgradecimientosPage() {
  return (
    <div className="container content-page">
      <h1 className="title">Agradecimientos</h1>
      <p className="mt-4">
        Queremos dar las gracias a todas las personas y comunidades que colaboran con DockerLabs,
        ya sea creando máquinas, aportando ideas, ayudando a mejorar la plataforma o detectando bugs.
        Sin su apoyo, este proyecto no sería posible.
      </p>
      <div className="card p-4 mt-4 mb-5 colaboradores-card">
        <div className="colaboradores-grid">
          {colaboradores.map((c) => (
            <a key={c.name} href={c.url} target="_blank" rel="noreferrer" className={`colaborador ${c.glow}`}>
              <img src={c.img} alt={c.name} />
              <span>{c.name}</span>
            </a>
          ))}
        </div>
      </div>
    </div>
  )
}
