import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import BunkerLayout from '../../components/layout/BunkerLayout'
import { useAuth } from '../../context/AuthContext'
import './BunkerAccesosPage.css'
import '../../components/common/BunkerModals.css'

function BunkerAccesosContent() {
    const { user: authUser, loading: authLoading } = useAuth()
    const navigate = useNavigate()
    const [data, setData] = useState({ tokens: [], real_machines: [], writeups: [], bunker_machines: [] })
    const [loading, setLoading] = useState(true)
    const [alert, setAlert] = useState(null)
    const [createdToken, setCreatedToken] = useState(null)

    // Form states
    const [newName, setNewName] = useState('')
    const [newPass, setNewPass] = useState('')
    const [wMaquina, setWMaquina] = useState('')
    const [wAutor, setWAutor] = useState('')
    const [wUrl, setWUrl] = useState('')
    const [wTipo, setWTipo] = useState('texto')
    const [wLocked, setWLocked] = useState(false)

    // Flags editing
    const [flagEdits, setFlagEdits] = useState({}) // { machineId: newValue }

    // Logs modal
    const [logsModal, setLogsModal] = useState(null) // { tokenId, tokenName, logs }

    const fetchData = useCallback(() => {
        fetch('/bunkerlabs/api/accesos', { credentials: 'include' })
            .then(r => r.ok ? r.json() : null)
            .then(d => { if (d) setData(d) })
            .catch(() => { })
            .finally(() => setLoading(false))
    }, [])

    useEffect(() => {
        if (!authLoading) {
            if (!authUser?.is_authenticated) {
                navigate('/login')
                return
            }
            if (authUser?.user?.role !== 'admin') {
                navigate('/403')
                return
            }
            fetchData()
        }
    }, [authUser, authLoading, navigate, fetchData])

    const showAlert = (type, text) => {
        setAlert({ type, text })
        setTimeout(() => setAlert(null), 4000)
    }

    const getCsrf = async () => {
        const r = await fetch('/api/csrf', { credentials: 'include' })
        const d = await r.json()
        return d.csrf_token || ''
    }

    // ─── Token CRUD ───
    const handleCreateToken = async (e) => {
        e.preventDefault()
        if (!newName.trim() || !newPass.trim()) return
        const csrf = await getCsrf()
        const res = await fetch('/bunkerlabs/api/accesos', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ nombre: newName.trim(), password: newPass.trim() })
        })
        const d = await res.json()
        if (res.ok && d.success) {
            showAlert('success', d.message)
            setNewName(''); setNewPass('')
            // show created token so admin can copy it
            if (d.token) setCreatedToken(d.token)
            fetchData()
        } else {
            showAlert('error', d.error || 'Error')
        }
    }

    const handleDeleteToken = async (id) => {
        if (!confirm('¿Eliminar este token?')) return
        const csrf = await getCsrf()
        const res = await fetch(`/bunkerlabs/api/accesos/${id}`, {
            method: 'DELETE', credentials: 'include',
            headers: { 'X-CSRFToken': csrf }
        })
        const d = await res.json()
        if (res.ok && d.success) { showAlert('success', d.message); fetchData() }
        else showAlert('error', d.error || 'Error')
    }

    const handleViewLogs = async (tokenId, tokenName) => {
        const res = await fetch(`/bunkerlabs/api/logs/${tokenId}`, { credentials: 'include' })
        const d = await res.json()
        setLogsModal({ tokenId, tokenName, logs: d.logs || d || [] })
    }

    const handleClearLogs = async (tokenId) => {
        if (!confirm('¿Eliminar TODO el historial de accesos para este usuario?')) return
        const csrf = await getCsrf()
        const res = await fetch(`/bunkerlabs/api/logs/${tokenId}/delete`, {
            method: 'POST', credentials: 'include', headers: { 'X-CSRFToken': csrf }
        })
        const d = await res.json()
        if (res.ok) {
            showAlert('success', d.message || 'Historial eliminado')
            setLogsModal(prev => prev ? { ...prev, logs: [] } : prev)
        } else {
            showAlert('error', d.error || 'Error al eliminar historial')
        }
    }

    // copy utilities
    const copyToClipboard = async (text) => {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text)
            } else {
                const textArea = document.createElement('textarea')
                textArea.value = text
                textArea.style.position = 'fixed'
                textArea.style.left = '-9999px'
                document.body.appendChild(textArea)
                textArea.focus()
                textArea.select()
                document.execCommand('copy')
                document.body.removeChild(textArea)
            }
            showAlert('success', 'Copiado al portapapeles')
        } catch (err) {
            console.error('Copy failed', err)
            showAlert('error', 'No se pudo copiar')
        }
    }

    const copyDirectLink = (token) => {
        const url = window.location.origin + '/bunkerlabs/?token=' + token
        copyToClipboard(url)
    }

    // ─── Writeup CRUD ───
    const handleAddWriteup = async (e) => {
        e.preventDefault()
        if (!wMaquina || !wAutor.trim() || !wUrl.trim()) return
        const csrf = await getCsrf()
        const res = await fetch('/bunkerlabs/api/writeups/add', {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ maquina: wMaquina, autor: wAutor.trim(), url: wUrl.trim(), tipo: wTipo, locked: wLocked })
        })
        const d = await res.json()
        if (res.ok && d.success) {
            showAlert('success', d.message)
            setWAutor(''); setWUrl(''); setWLocked(false)
            fetchData()
        } else {
            showAlert('error', d.error || 'Error')
        }
    }

    const handleToggleLock = async (id) => {
        const csrf = await getCsrf()
        await fetch(`/bunkerlabs/admin/writeups/toggle_lock/${id}`, {
            method: 'POST', credentials: 'include',
            headers: { 'X-CSRFToken': csrf }
        })
        fetchData()
    }

    const handleDeleteWriteup = async (id) => {
        if (!confirm('¿Eliminar este writeup?')) return
        const csrf = await getCsrf()
        const res = await fetch(`/bunkerlabs/api/writeups/${id}`, {
            method: 'DELETE', credentials: 'include',
            headers: { 'X-CSRFToken': csrf }
        })
        const d = await res.json()
        if (res.ok && d.success) { showAlert('success', d.message); fetchData() }
        else showAlert('error', d.error || 'Error')
    }

    // ─── Flag update ───
    const handleUpdateFlag = async (machineId) => {
        const newFlag = (flagEdits[machineId] || '').trim()
        if (!newFlag) return
        const csrf = await getCsrf()
        const res = await fetch(`/bunkerlabs/admin/machines/update_flag/${machineId}`, {
            method: 'POST', credentials: 'include',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
            body: JSON.stringify({ flag: newFlag })
        })
        const d = await res.json()
        if (res.ok && d.success) {
            showAlert('success', d.message)
            setFlagEdits(prev => { const n = { ...prev }; delete n[machineId]; return n })
            fetchData()
        } else {
            showAlert('error', d.error || 'Error')
        }
    }

    if (loading) return <div className="bunker-accesos-container"><p style={{ color: 'var(--bunker-text-muted)' }}>Cargando datos...</p></div>

    return (
        <div className="bunker-accesos-container">
            <h1 className="bunker-accesos-title"><i className="bi bi-gear"></i> Gestión BunkerLabs</h1>

            {alert && <div className={`bunker-page-alert ${alert.type}`}>{alert.text}</div>}

            {/* ── SECTION: New Token ── */}
            <div className="bunker-glass-card">
                <h3><i className="bi bi-key"></i> Nuevo Acceso</h3>
                <form onSubmit={handleCreateToken}>
                    <div className="bunker-form-row">
                        <input className="bunker-input" placeholder="Nombre del usuario" value={newName} onChange={e => setNewName(e.target.value)} />
                        <input className="bunker-input" placeholder="Contraseña de acceso" value={newPass} onChange={e => setNewPass(e.target.value)} />
                        <button type="submit" className="bunker-btn-primary" disabled={!newName.trim() || !newPass.trim()}>
                            <i className="bi bi-plus-circle"></i> Crear
                        </button>
                    </div>
                </form>
            </div>

            {/* ── SECTION: Tokens Table ── */}
            <div className="bunker-glass-card">
                <h3><i className="bi bi-people"></i> Tokens de Acceso ({data.tokens.length})</h3>
                <div className="bunker-table-wrapper">
                    <table className="bunker-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Usuario</th>
                                <th>Token</th>
                                <th>Estado</th>
                                <th>Puntos</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.tokens.map(t => (
                                <tr key={t.id}>
                                    <td>{t.id}</td>
                                    <td>{t.nombre}</td>
                                    <td><code className="bunker-token-code">{t.token}</code></td>
                                    <td><span className={t.activo ? 'status-active' : 'status-inactive'}>{t.activo ? 'Activo' : 'Inactivo'}</span></td>
                                    <td>{t.puntos}</td>
                                    <td>
                                        <div style={{ display: 'flex', gap: '0.4rem' }}>
                                            <button className="bunker-btn-sm" onClick={() => handleViewLogs(t.id, t.nombre)} title="Ver historial">
                                                <i className="bi bi-clock-history"></i>
                                            </button>
                                            <button className="bunker-btn" onClick={() => copyDirectLink(t.token)} title="Copiar enlace">
                                                <i className="bi bi-link-45deg"></i>
                                            </button>
                                            <button className="bunker-btn-danger" onClick={() => handleDeleteToken(t.id)} title="Eliminar">
                                                <i className="bi bi-trash"></i>
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                            {data.tokens.length === 0 && <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--bunker-text-muted)' }}>No hay tokens</td></tr>}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* ── SECTION: Writeups ── */}
            <div className="bunker-glass-card">
                <h3><i className="bi bi-journal-text"></i> Gestión de Writeups</h3>
                <form onSubmit={handleAddWriteup}>
                    <div className="bunker-form-row">
                        <select className="bunker-input" value={wMaquina} onChange={e => setWMaquina(e.target.value)}>
                            <option value="">Seleccionar máquina...</option>
                            {data.real_machines.map(m => <option key={m.id} value={m.nombre}>{m.nombre}</option>)}
                        </select>
                        <input className="bunker-input" placeholder="Autor" value={wAutor} onChange={e => setWAutor(e.target.value)} />
                        <input className="bunker-input" placeholder="URL" value={wUrl} onChange={e => setWUrl(e.target.value)} />
                        <select className="bunker-input" value={wTipo} onChange={e => setWTipo(e.target.value)} style={{ maxWidth: 120 }}>
                            <option value="texto">Texto</option>
                            <option value="video">Video</option>
                        </select>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: 'var(--bunker-text-secondary)', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                            <input type="checkbox" checked={wLocked} onChange={e => setWLocked(e.target.checked)} /> Bloqueado
                        </label>
                        <button type="submit" className="bunker-btn-primary" disabled={!wMaquina || !wAutor.trim() || !wUrl.trim()}>
                            <i className="bi bi-plus-circle"></i> Añadir
                        </button>
                    </div>
                </form>

                <div className="bunker-table-wrapper">
                    <table className="bunker-table">
                        <thead>
                            <tr>
                                <th>Máquina</th>
                                <th>Autor</th>
                                <th>URL</th>
                                <th>Tipo</th>
                                <th>Estado</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.writeups.map(w => (
                                <tr key={w.id}>
                                    <td>{w.maquina}</td>
                                    <td>{w.autor}</td>
                                    <td><a href={w.url} target="_blank" rel="noreferrer" style={{ color: 'var(--bunker-primary-light)' }}>{w.url.length > 40 ? w.url.substring(0, 40) + '...' : w.url}</a></td>
                                    <td>{w.tipo === 'video' ? '🎬 Video' : '📝 Texto'}</td>
                                    <td>
                                        <button className="bunker-toggle-lock" onClick={() => handleToggleLock(w.id)} title={w.locked ? 'Desbloquear' : 'Bloquear'}>
                                            {w.locked ? '🔒' : '🔓'}
                                        </button>
                                    </td>
                                    <td>
                                        <button className="bunker-btn-danger" onClick={() => handleDeleteWriteup(w.id)}>
                                            <i className="bi bi-trash"></i>
                                        </button>
                                    </td>
                                </tr>
                            ))}
                            {data.writeups.length === 0 && <tr><td colSpan={6} style={{ textAlign: 'center', color: 'var(--bunker-text-muted)' }}>No hay writeups</td></tr>}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* ── SECTION: Flags ── */}
            <div className="bunker-glass-card">
                <h3><i className="bi bi-flag"></i> Gestión de Flags</h3>
                <div className="bunker-table-wrapper">
                    <table className="bunker-table">
                        <thead>
                            <tr>
                                <th>ID</th>
                                <th>Máquina</th>
                                <th>Dificultad</th>
                                <th>Flag Actual</th>
                                <th>Acciones</th>
                            </tr>
                        </thead>
                        <tbody>
                            {data.bunker_machines.map(m => (
                                <tr key={m.id}>
                                    <td>{m.id}</td>
                                    <td>{m.nombre}</td>
                                    <td>
                                        <span style={{ color: m.color || 'var(--bunker-text-secondary)' }}>{m.dificultad}</span>
                                    </td>
                                    <td>
                                        <div className="bunker-flag-inline">
                                            <input
                                                type="text"
                                                defaultValue={m.pin || ''}
                                                placeholder="Sin flag"
                                                onChange={e => setFlagEdits(prev => ({ ...prev, [m.id]: e.target.value }))}
                                            />
                                        </div>
                                    </td>
                                    <td>
                                        <button
                                            className="bunker-btn-primary"
                                            style={{ padding: '0.4rem 0.8rem', fontSize: '0.78rem' }}
                                            onClick={() => handleUpdateFlag(m.id)}
                                            disabled={!flagEdits[m.id]?.trim()}
                                        >
                                            <i className="bi bi-check-lg"></i> Guardar
                                        </button>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>

            {/* ── MODAL: Access Logs ── */}
            {logsModal && (
                <div className="bunker-overlay" onClick={() => setLogsModal(null)}>
                    <div className="bunker-modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 500 }}>
                        <button className="bunker-modal-close" onClick={() => setLogsModal(null)}>×</button>
                        <h2>📋 Historial de Accesos</h2>
                        <h3>{logsModal.tokenName}</h3>
                        {Array.isArray(logsModal.logs) && logsModal.logs.length > 0 ? (
                            <ul className="bunker-logs-list">
                                {logsModal.logs.map((log, i) => (
                                    <li key={i} className="bunker-logs-item">
                                        <span>{log.user_nombre || log.nombre || '???'}</span>
                                        <span style={{ fontFamily: "'Fira Code', monospace", fontSize: '0.8rem' }}>{log.accessed_at || log.fecha || ''}</span>
                                    </li>
                                ))}
                            </ul>
                        ) : (
                            <p style={{ color: 'var(--bunker-text-muted)', textAlign: 'center' }}>No hay registros de acceso.</p>
                        )}
                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end', marginTop: 12 }}>
                            <button className="bunker-btn-danger" onClick={() => handleClearLogs(logsModal.tokenId)}>Limpiar historial</button>
                            <button className="bunker-btn" onClick={() => setLogsModal(null)}>Cerrar</button>
                        </div>
                    </div>
                </div>
            )}

            {/* Show created token box so admin can copy it easily */}
            {createdToken && (
                <div style={{ marginTop: 12 }}>
                    <div className="bunker-created-token">
                        <strong>Contraseña generada:</strong>
                        <code style={{ marginLeft: 8 }}>{createdToken}</code>
                        <button className="bunker-btn" style={{ marginLeft: 8 }} onClick={() => copyToClipboard(createdToken)}>Copiar</button>
                        <small style={{ display: 'block', color: 'var(--bunker-text-muted)', marginTop: 6 }}>Entrega esta contraseña al usuario (debe estar registrado en DockerLabs).</small>
                    </div>
                </div>
            )}
        </div>
    )
}

export default function BunkerAccesosPage() {
    return (
        <BunkerLayout>
            <BunkerAccesosContent />
        </BunkerLayout>
    )
}
