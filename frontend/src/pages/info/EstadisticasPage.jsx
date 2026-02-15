import React, { useEffect, useState } from 'react'
import './EstadisticasPage.css'

function StatCard({ title, icon, iconColor, stats }) {
  const labels = Object.keys(stats)
  const values = Object.values(stats)
  const max = Math.max(...values, 1)

  return (
    <div className="stats-chart-card">
      <div className="stats-chart-title">
        <i className={icon} style={{ color: iconColor }}></i>
        {title}
      </div>
      <div className="stats-chart-bars">
        {labels.length === 0 ? (
          <p className="stats-empty">No hay datos</p>
        ) : (
          labels.map((year, i) => (
            <div key={year} className="stats-bar-row">
              <span className="stats-bar-label">{year}</span>
              <div className="stats-bar-track">
                <div className="stats-bar-fill" style={{ width: `${(values[i] / max) * 100}%` }} />
              </div>
              <span className="stats-bar-value">{values[i]}%</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default function EstadisticasPage() {
  const [data, setData] = useState({ machine_stats: {}, writeup_stats: {}, user_stats: {} })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/estadisticas', { credentials: 'include' })
      .then(r => r.ok ? r.json() : Promise.reject(new Error('Error al cargar')))
      .then(d => setData(d))
      .catch(err => setError(err.message))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="stats-container">
        <p className="stats-loading">Cargando estadísticas...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="stats-container">
        <div className="alert alert-danger">{error}</div>
      </div>
    )
  }

  return (
    <div className="stats-container">
      <div className="stats-header">
        <h1>Estadísticas de la Plataforma</h1>
        <p>Crecimiento y métricas anuales de DockerLabs</p>
      </div>

      <div className="stats-charts-grid">
        <StatCard
          title="Máquinas Subidas"
          icon="bi bi-pc-display-horizontal"
          iconColor="#3b82f6"
          stats={data.machine_stats || {}}
        />
        <StatCard
          title="Writeups Publicados"
          icon="bi bi-file-text"
          iconColor="#10b981"
          stats={data.writeup_stats || {}}
        />
        <StatCard
          title="Usuarios Registrados"
          icon="bi bi-people"
          iconColor="#f59e0b"
          stats={data.user_stats || {}}
        />
      </div>
    </div>
  )
}
