import React, { useState, useEffect, useMemo } from 'react'
import BunkerLayout, { useBunkerSession } from '../../components/layout/BunkerLayout'
import BunkerMachineModal from '../../components/bunker/BunkerMachineModal'
import BunkerRankingModal from '../../components/bunker/BunkerRankingModal'
import BunkerFlagModal from '../../components/bunker/BunkerFlagModal'
import BunkerWriteupModal from '../../components/bunker/BunkerWriteupModal'
import { useNavigate } from 'react-router-dom'

// No import './BunkerHomePage.css' needed as we use global styles from BunkerLayout.css (bunkerlabs.css)

const DIFICULTAD_MAP = {
    'Muy Fácil': 'muy-facil',
    'Fácil': 'facil',
    'Medio': 'medio',
    'Difícil': 'dificil'
}

const ITEMS_PER_PAGE = 50

function BunkerHomeContent() {
    const [machines, setMachines] = useState([])
    const [loading, setLoading] = useState(true)
    const [search, setSearch] = useState('')
    const [filter, setFilter] = useState('todos')
    const [isGuest, setIsGuest] = useState(false)
    const [isAnonymous, setIsAnonymous] = useState(false)
    const [currentPage, setCurrentPage] = useState(1)

    // Modals
    const [machineModal, setMachineModal] = useState(null)
    const [showRanking, setShowRanking] = useState(false)
    const [flagModal, setFlagModal] = useState(null)
    const [writeupModal, setWriteupModal] = useState(null)

    const sess = useBunkerSession()
    const navigate = useNavigate()

    useEffect(() => {
        if (!sess.loaded) return
        // If the user is logged into DockerLabs but not into BunkerLabs, force PIN login.
        if (sess.docker_logged_in && !sess.logged_in && !sess.is_guest && !sess.is_anonymous) {
            navigate('/bunkerlabs/login')
            return
        }

        // Fetch machines
        fetch('/bunkerlabs/api/machines', { credentials: 'include' })
            .then(r => r.ok ? r.json() : { machines: [] })
            .then(data => {
                setMachines(data.machines || [])
                setIsGuest(data.is_guest || false)
                setIsAnonymous(data.is_anonymous || false)
            })
            .catch(() => setMachines([]))
            .finally(() => setLoading(false))
    }, [sess.loaded, sess.docker_logged_in, sess.logged_in, sess.is_guest, sess.is_anonymous, navigate])

    // Filtering Logic
    const filtered = useMemo(() => {
        const q = search.trim().toLowerCase()
        return machines.filter(m => {
            const nameMatch = (m.nombre || '').toLowerCase().includes(q)
            if (!nameMatch) return false

            if (filter === 'todos') return true
            if (filter === 'real') return (m.clase || '') === 'real'

            // Map text difficulty to class name
            const clase = DIFICULTAD_MAP[m.dificultad] || m.clase || ''
            return clase === filter
        })
    }, [machines, search, filter])

    useEffect(() => {
        setCurrentPage(1)
    }, [search, filter])

    const totalItems = filtered.length
    const totalPages = useMemo(() => Math.max(1, Math.ceil(totalItems / ITEMS_PER_PAGE)), [totalItems])

    const pageItems = useMemo(() => {
        const page = Math.min(Math.max(currentPage, 1), totalPages)
        const start = (page - 1) * ITEMS_PER_PAGE
        const end = start + ITEMS_PER_PAGE
        return filtered.slice(start, end)
    }, [filtered, currentPage, totalPages])

    const goToPage = (page) => {
        if (page < 1 || page > totalPages) return
        setCurrentPage(page)
    }

    const visiblePages = useMemo(() => {
        const maxVisible = 5
        let pageStart = Math.max(1, currentPage - Math.floor(maxVisible / 2))
        let pageEnd = Math.min(totalPages, pageStart + maxVisible - 1)
        if (pageEnd - pageStart < maxVisible - 1) pageStart = Math.max(1, pageEnd - maxVisible + 1)
        const pages = []
        for (let i = pageStart; i <= pageEnd; i++) pages.push(i)
        return pages
    }, [currentPage, totalPages])

    // Determine lock state
    const isLocked = (m) => isGuest && !m.guest_access

    return (
        <div className="container">
            {/* Header: Search & Filters */}
            <div className="header">
                {/* Left: Search & Ranking */}
                <div className="header-left d-flex align-items-center gap-2" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <input
                        type="text"
                        id="search"
                        placeholder="Buscar en BunkerLabs..."
                        value={search}
                        onChange={e => setSearch(e.target.value)}
                    />
                    <button id="btn-ranking" className="btn btn-sm btn-action" onClick={() => setShowRanking(true)}>
                        Ranking👑
                    </button>
                </div>

                {/* Right: Filters */}
                <div className="header-right d-flex align-items-center gap-1 flex-wrap justify-content-end" style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <div id="difficulty-filter">
                        {[
                            { id: 'todos', label: 'Todos' },
                            { id: 'muy-facil', label: 'Muy Fácil' },
                            { id: 'facil', label: 'Fácil' },
                            { id: 'medio', label: 'Medio' },
                            { id: 'dificil', label: 'Difícil' },
                            { id: 'real', label: 'Entornos Reales' }
                        ].map(btn => (
                            <button
                                key={btn.id}
                                className={`btn-filter ${filter === btn.id ? 'active' : ''}`}
                                data-difficulty={btn.id}
                                onClick={() => setFilter(btn.id)}
                            >
                                {btn.label}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* Real Env Banner */}
            {/* Logic: Show banner if filter is 'real' OR if specific machine logic dictates? 
                In original HTML it was hidden by default and toggled by JS. 
                Here we'll show it if the user is filtering by Real Environments. */}
            <div id="real-env-banner" className="alert alert-info real-env-info" style={{ display: filter === 'real' ? 'block' : 'none' }}>
                <div className="d-flex align-items-start" style={{ display: 'flex', alignItems: 'flex-start' }}>
                    <i className="bi bi-info-circle-fill me-3 mt-1" style={{ fontSize: '1.5rem', marginRight: '1rem', marginTop: '0.25rem' }}></i>
                    <div>
                        <h6 className="mb-2 fw-bold" style={{ fontWeight: 'bold', marginBottom: '0.5rem' }}>Entornos Reales</h6>
                        <p className="mb-0">
                            Estos laboratorios son entornos reales donde se han encontrado vulnerabilidades,
                            se han reportado y a su vez se han convertido en máquinas para que puedas practicar
                            hacking ético en entornos reales.
                        </p>
                    </div>
                </div>
            </div>

            {/* Anonymous Banner */}
            {isAnonymous && (
                <div className="alert alert-info text-center" style={{ borderLeft: '4px solid #0dcaf0', textAlign: 'center', marginBottom: '1rem', background: 'rgba(13, 202, 240, 0.1)', color: '#0dcaf0', padding: '1rem' }}>
                    <i className="bi bi-info-circle-fill me-2" style={{ marginRight: '0.5rem' }}></i>
                    <strong>Accediendo como usuario anónimo. </strong>
                    Se recomienda <Link to="/bunkerlabs/login" className="fw-bold text-decoration-underline" style={{ fontWeight: 'bold', textDecoration: 'underline' }}>iniciar sesión en DockerLabs</Link> para una mejor experiencia y guardar tu progreso.
                </div>
            )}

            {/* Guest Banner */}
            {isGuest && (
                <div className="alert alert-warning text-center" style={{ textAlign: 'center', marginBottom: '1rem', background: 'rgba(255, 193, 7, 0.1)', color: '#ffc107', padding: '1rem', border: '1px solid rgba(255, 193, 7, 0.2)' }}>
                    Estas máquinas son de acceso exclusivo para los miembros del <a href="https://skool.com/bunkerpinguino" target="_blank" rel="noreferrer" className="fw-bold" style={{ fontWeight: 'bold', textDecoration: 'underline' }}>bunker</a>
                </div>
            )}

            {loading && <p className="loading-text">Cargando máquinas...</p>}

            {/* Machines Grid */}
            <div className="machines-grid">
                {pageItems.map(maquina => {
                    const locked = isLocked(maquina)
                    const clase = (maquina.clase || '').toLowerCase()
                    const isReal = clase === 'real'

                    return (
                        <div
                            key={maquina.id}
                            className={`item ${clase} ${locked ? 'locked-guest-item' : ''}`}
                            onClick={() => {
                                if (locked) window.open('https://skool.com/bunkerpinguino', '_blank')
                                else setMachineModal(maquina)
                            }}
                            style={{ cursor: 'pointer' }}
                        >
                            {locked && (
                                <>
                                    <div className="guest-lock-overlay" style={{
                                        position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
                                        zIndex: 10, color: '#333', fontSize: '3rem', pointerEvents: 'none',
                                        textShadow: '0 0 10px rgba(255,255,255,0.5)'
                                    }}>
                                        <i className="bi bi-lock-fill"></i>
                                    </div>
                                    <div style={{
                                        position: 'absolute', top: 0, left: 0, width: '100%', height: '100%',
                                        backgroundColor: 'rgba(128,128,128,0.3)', zIndex: 5, borderRadius: 'inherit', pointerEvents: 'none'
                                    }}></div>
                                </>
                            )}

                            <span><strong>{maquina.nombre}</strong></span>
                            {/* Badge removed in original template, but css has .badge styles. Original HTML commented out badge. */}

                            <div className="actions icon-container">
                                {/* Download Button */}
                                <button
                                    className="download btn-download"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        if (!locked && maquina.link_descarga) window.open(maquina.link_descarga, '_blank')
                                    }}
                                    disabled={locked}
                                >
                                    <i className="bi bi-cloud-arrow-down-fill"></i>
                                </button>

                                {/* Upload Flag (Only if not real) */}
                                {!isReal && (
                                    <button
                                        className="upload btn-upload"
                                        title="Subir Flag"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            setFlagModal({ name: maquina.nombre, id: maquina.id })
                                        }}
                                        disabled={locked}
                                    >
                                        <i className="bi bi-flag-fill"></i>
                                    </button>
                                )}

                                {/* Writeups (Only if real) */}
                                {isReal && (
                                    <button
                                        className="btn-writeup"
                                        title="Ver Writeups"
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            setWriteupModal(maquina.nombre)
                                        }}
                                    >
                                        <i className="bi bi-book-fill"></i>
                                    </button>
                                )}
                            </div>
                        </div>
                    )
                })}
            </div>

            <div className="pagination-container" id="pagination-container" style={{ display: totalItems > 0 ? 'flex' : 'none' }}>
                <div className="pagination-wrapper">
                    <span className="pagination-info">
                        {totalItems === 0
                            ? '0-0 de 0'
                            : `${(currentPage - 1) * ITEMS_PER_PAGE + 1}-${Math.min(currentPage * ITEMS_PER_PAGE, totalItems)} de ${totalItems}`}
                    </span>

                    <nav className="pagination-nav" aria-label="Paginación">
                        <button className="pagination-btn" disabled={currentPage <= 1} onClick={() => goToPage(currentPage - 1)}>
                            &laquo; Anterior
                        </button>

                        <span className="pagination-pages">
                            {visiblePages.map(p => (
                                <button
                                    key={p}
                                    className={`pagination-btn${p === currentPage ? ' active' : ''}`}
                                    onClick={() => goToPage(p)}
                                >
                                    {p}
                                </button>
                            ))}
                        </span>

                        <button className="pagination-btn" disabled={currentPage >= totalPages} onClick={() => goToPage(currentPage + 1)}>
                            Siguiente &raquo;
                        </button>
                    </nav>
                </div>
            </div>

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
