import React, { useState, useEffect, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import BunkerLayout, { useBunkerSession } from '../components/BunkerLayout'
import BunkerMachineModal from '../components/BunkerMachineModal'
import BunkerRankingModal from '../components/BunkerRankingModal'
import BunkerFlagModal from '../components/BunkerFlagModal'
import BunkerWriteupModal from '../components/BunkerWriteupModal'
import './BunkerHomePage.css'

const DIFICULTAD_MAP = {
    'Muy Fácil': 'muy-facil',
    'Fácil': 'facil',
    'Medio': 'medio',
    'Difícil': 'dificil'
}

function BunkerHomeContent() {
    const [machines, setMachines] = useState([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [filter, setFilter] = useState('todos')
    const [isGuest, setIsGuest] = useState(false)

    // Modal states
    const [machineModal, setMachineModal] = useState(null)
    const [showRanking, setShowRanking] = useState(false)
    const [flagModal, setFlagModal] = useState(null) // { name, id }
    const [writeupModal, setWriteupModal] = useState(null) // machine name

    const sess = useBunkerSession()
    const navigate = useNavigate()

    useEffect(() => {
        if (!sess.logged_in && sess.docker_logged_in) {
            navigate('/bunkerlabs/login')
            return
        }
        fetch('/bunkerlabs/api/machines', { credentials: 'include' })
            .then(r => r.ok ? r.json() : { machines: [] })
            .then(data => {
                setMachines(data.machines || [])
                setIsGuest(data.is_guest || false)
            })
            .catch(() => setMachines([]))
            .finally(() => setLoading(false))
    }, [sess.logged_in])

    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase()
        return machines.filter(m => {
            const nameMatch = (m.nombre || '').toLowerCase().includes(q)
            if (!nameMatch) return false
            if (filter === 'todos') return true
            if (filter === 'real') return (m.clase || '') === 'real'
            const clase = DIFICULTAD_MAP[m.dificultad] || m.clase || ''
            return clase === filter
        })
    }, [machines, search, filter])

    const counts = useMemo(() => {
        const q = search.trim().toLowerCase()
        const c = { 'muy-facil': 0, 'facil': 0, 'medio': 0, 'dificil': 0, 'real': 0, 'todos': 0 }
        machines.forEach(m => {
            if (!(m.nombre || '').toLowerCase().includes(q)) return
            c.todos++
            if ((m.clase || '') === 'real') { c.real++; return }
            const cl = DIFICULTAD_MAP[m.dificultad] || m.clase || ''
            if (c[cl] !== undefined) c[cl]++
        })
        return c
    }, [machines, search])

    const hasRealMachines = counts.real > 0

    return (
        <div className="bunker-home-container">
            {/* Guest banner */}
            {isGuest && (
                <div className="bunker-guest-banner">
                    <i className="bi bi-exclamation-triangle" style={{ fontSize: '1.3rem' }}></i>
                    Estás en modo invitado. No puedes descargar máquinas ni guardar tu progreso.
                </div>
            )}

            {/* Filter bar */}
            <div className="bunker-filters-bar">
                <input
                    type="text"
                    className="bunker-search-input"
                    placeholder="Buscar máquina..."
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                />

                <div className="bunker-action-buttons">
                    <button className="bunker-action-btn" onClick={() => setShowRanking(true)}>
                        🏆 Ranking
                    </button>
                </div>

                <div className="bunker-filter-buttons">
                    {[
                        { key: 'todos', label: 'Todos' },
                        { key: 'muy-facil', label: 'Muy Fácil' },
                        { key: 'facil', label: 'Fácil' },
                        { key: 'medio', label: 'Medio' },
                        { key: 'dificil', label: 'Difícil' },
                        ...(hasRealMachines ? [{ key: 'real', label: 'Entornos Reales' }] : [])
                    ].map(f => (
                        <button
                            key={f.key}
                            className={`bunker-filter-btn ${filter === f.key ? 'selected' : ''}`}
                            onClick={() => setFilter(f.key)}
                        >
                            {f.label} ({counts[f.key] || 0})
                        </button>
                    ))}
                </div>
            </div>

            {/* Real env banner */}
            {filter === 'real' && (
                <div className="bunker-real-banner">
                    <i className="bi bi-shield-lock" style={{ fontSize: '2rem', color: 'var(--bunker-primary-light)' }}></i>
                    <span>Entornos Reales — Máquinas con escenarios de empresa real</span>
                </div>
            )}

            {/* Loading */}
            {loading && <div className="bunker-loading">Cargando máquinas...</div>}

            {/* Machine grid */}
            {!loading && (
                <div className="bunker-machines-grid">
                    {filtered.length === 0 ? (
                        <p style={{ color: 'var(--bunker-text-muted)', gridColumn: '1/-1', textAlign: 'center', padding: '2rem' }}>
                            No hay máquinas que mostrar.
                        </p>
                    ) : (
                        filtered.map(m => {
                            const clase = (m.clase || '') === 'real' ? 'real' : (DIFICULTAD_MAP[m.dificultad] || m.clase || '')
                            return (
                                <div
                                    key={m.id}
                                    className={`bunker-machine-item ${clase}`}
                                    onClick={() => setMachineModal(m)}
                                >
                                    <span className="bunker-machine-name">{m.nombre}</span>
                                    <span className={`bunker-machine-badge ${clase !== 'real' ? clase : ''}`}>
                                        {m.dificultad || 'Real'}
                                    </span>
                                    <div className="bunker-machine-actions">
                                        {!isGuest && m.link_descarga && (
                                            <button className="download" title="Descargar" onClick={e => { e.stopPropagation(); window.open(m.link_descarga, '_blank') }}>
                                                <i className="bi bi-cloud-arrow-down-fill"></i>
                                            </button>
                                        )}
                                        <button className="upload" title="Subir flag" onClick={e => { e.stopPropagation(); setFlagModal({ name: m.nombre, id: m.id }) }}>
                                            <i className="bi bi-flag-fill"></i>
                                        </button>
                                        {(m.clase === 'real') && (
                                            <button title="Ver writeups" onClick={e => { e.stopPropagation(); setWriteupModal(m.nombre) }}>
                                                <i className="bi bi-book"></i>
                                            </button>
                                        )}
                                    </div>
                                </div>
                            )
                        })
                    )}
                </div>
            )}

            {/* Modals */}
            {machineModal && <BunkerMachineModal machine={machineModal} onClose={() => setMachineModal(null)} />}
            {showRanking && <BunkerRankingModal onClose={() => setShowRanking(false)} />}
            {flagModal && (
                <BunkerFlagModal
                    machineName={flagModal.name}
                    machineId={flagModal.id}
                    onClose={() => setFlagModal(null)}
                />
            )}
            {writeupModal && <BunkerWriteupModal machineName={writeupModal} onClose={() => setWriteupModal(null)} />}
        </div>
    )
}

export default function BunkerHomePage() {
    return (
        <BunkerLayout>
            <BunkerHomeContent />
        </BunkerLayout>
    )
}
