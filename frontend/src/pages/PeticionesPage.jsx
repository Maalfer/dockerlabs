
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../components/Header';
import './PeticionesPage.css';

const PeticionesPage = () => {
  const [data, setData] = useState({
    claims: [],
    name_claims: [],
    edit_requests: [],
    machine_edit_requests: [],
    username_change_requests: []
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedSections, setExpandedSections] = useState({
    claims: false,
    name_claims: false,
    edit_requests: false,
    machine_edit_requests: false,
    username_change_requests: false
  });
  const [rejectReasons, setRejectReasons] = useState({});

  const navigate = useNavigate();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await fetch('/api/peticiones');
      if (response.status === 401 || response.status === 403) {
        navigate('/login');
        return;
      }
      if (!response.ok) {
        throw new Error('Error al cargar peticiones');
      }
      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const getCsrfToken = () => {
    const match = document.cookie.match(new RegExp('(^| )csrf_access_token=([^;]+)'));
    return match ? match[2] : null;
  };

  const handleAction = async (endpoint, method = 'POST', body = null) => {
    try {
      const csrfToken = getCsrfToken();
      const headers = {
        'X-CSRF-TOKEN': csrfToken
      };
      if (body) {
        headers['Content-Type'] = 'application/json';
      }

      const response = await fetch(endpoint, {
        method,
        headers,
        body: body ? JSON.stringify(body) : null
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.error || 'Error en la acción');
      }

      // Refresh data
      fetchData();
    } catch (err) {
      alert(err.message);
    }
  };

  const toggleSection = (section) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section]
    }));
  };

  const handleRejectReasonChange = (id, value) => {
    setRejectReasons(prev => ({ ...prev, [id]: value }));
  };

  if (loading) return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <Header />
      <div className="peticiones-container">
        <div className="loading-spinner">Cargando peticiones...</div>
      </div>
    </div>
  );

  if (error) return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      <Header />
      <div className="peticiones-container">
        <div className="alert alert-warning">Error: {error}</div>
      </div>
    </div>
  )

  const renderStatusBadge = (status) => (
    <span className={`claim-status status-${status.toLowerCase()}`}>{status}</span>
  );

  const renderMachineClaims = () => {
    const pending = data.claims.filter(c => c.estado === 'pendiente');
    const others = data.claims.filter(c => c.estado !== 'pendiente');

    return (
      <div className="claims-section">
        <div className="section-header">
          <h2><i className="bi bi-flag"></i> Reclamaciones de autoría de máquinas</h2>
          <p className="section-subtitle">Revisa y gestiona las peticiones de autoría enviadas por los usuarios.</p>
        </div>

        {pending.length > 0 ? pending.map(c => (
          <div key={c.id} className="claim-card">
            <div className="claim-header">
              <span className="claim-title"><i className="bi bi-cpu"></i> {c.maquina_nombre}</span>
              {renderStatusBadge(c.estado)}
            </div>
            <div className="claim-body">
              <div className="claim-row"><span className="claim-label">Usuario:</span> {c.username}</div>
              <div className="claim-row"><span className="claim-label">Contacto:</span> {c.contacto}</div>
              <div className="claim-row"><span className="claim-label">Prueba:</span></div>
              <div className="claim-proof">{c.prueba}</div>
              <div className="claim-row"><small>Recibida: {c.created_at}</small></div>
            </div>
            <div className="claim-actions">
              <button className="btn-action btn-approve" onClick={() => handleAction(`/api/claims/${c.id}/approve`)}>
                <i className="bi bi-check-circle"></i> Aprobar
              </button>
              <button className="btn-action btn-reject" onClick={() => handleAction(`/api/claims/${c.id}/reject`)}>
                <i className="bi bi-x-circle"></i> Rechazar
              </button>
            </div>
          </div>
        )) : <p className="text-secondary text-sm mb-4">No hay reclamaciones pendientes.</p>}

        {others.length > 0 && (
          <>
            <button className="collapse-btn" onClick={() => toggleSection('claims')}>
              {expandedSections.claims ? 'Ocultar procesadas' : 'Mostrar procesadas'}
            </button>
            {expandedSections.claims && others.map(c => (
              <div key={c.id} className="claim-card opacity-75">
                <div className="claim-header">
                  <span className="claim-title"><i className="bi bi-cpu"></i> {c.maquina_nombre}</span>
                  <div className="flex items-center gap-2">
                    {renderStatusBadge(c.estado)}
                    <button className="btn-action btn-revert p-1" title="Revertir" onClick={() => handleAction(`/api/claims/${c.id}/revert`)}>
                      <i className="bi bi-arrow-counterclockwise"></i>
                    </button>
                  </div>
                </div>
                <div className="claim-body">
                  <div className="claim-row"><span className="claim-label">Usuario:</span> {c.username}</div>
                  <div className="claim-row"><small>Recibida: {c.created_at}</small></div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    );
  };

  const renderUsernameRequests = () => {
    const pending = data.username_change_requests.filter(r => r.estado === 'pendiente');
    const others = data.username_change_requests.filter(r => r.estado !== 'pendiente');

    return (
      <div className="claims-section">
        <div className="section-header">
          <h2><i className="bi bi-person-circle"></i> Cambios de nombre de usuario</h2>
          <p className="section-subtitle">Solicitudes enviadas por los usuarios que requieren aprobación.</p>
        </div>

        {pending.length > 0 ? pending.map(r => (
          <div key={r.id} className="claim-card">
            {r.conflict_count > 0 && (
              <div className="alert-warning">
                <strong>Advertencia:</strong> Coincide con {r.conflict_count} writeup(s).
                {r.conflict_examples && <div className="mt-1 text-xs">Ejemplos: {r.conflict_examples}</div>}
              </div>
            )}
            <div className="claim-header">
              <span className="claim-title">{r.old_username} → {r.requested_username}</span>
              {renderStatusBadge(r.estado)}
            </div>
            <div className="claim-body">
              <div className="claim-row"><span className="claim-label">Usuario ID:</span> {r.user_id}</div>
              <div className="claim-row"><span className="claim-label">Email:</span> {r.user_email}</div>
              <div className="claim-row"><span className="claim-label">Contacto:</span> {r.contacto_opcional || '—'}</div>
              <div className="claim-row"><span className="claim-label">Motivo:</span></div>
              <div className="claim-proof">{r.reason || '—'}</div>
            </div>
            <div className="claim-actions">
              <button className="btn-action btn-approve" onClick={() => handleAction(`/api/username-change/${r.id}/approve`)}>
                <i className="bi bi-check-circle"></i> Aprobar
              </button>
              <div className="reject-form">
                <input
                  type="text"
                  className="reject-reason-input"
                  placeholder="Motivo rechazo..."
                  value={rejectReasons[`username_${r.id}`] || ''}
                  onChange={(e) => handleRejectReasonChange(`username_${r.id}`, e.target.value)}
                />
                <button className="btn-action btn-reject" onClick={() => handleAction(`/api/username-change/${r.id}/reject`, 'POST', { decision_reason: rejectReasons[`username_${r.id}`] })}>
                  <i className="bi bi-x-circle"></i> Rechazar
                </button>
              </div>
            </div>
          </div>
        )) : <p className="text-secondary text-sm mb-4">No hay solicitudes pendientes.</p>}

        {others.length > 0 && (
          <>
            <button className="collapse-btn" onClick={() => toggleSection('username_change_requests')}>
              {expandedSections.username_change_requests ? 'Ocultar procesadas' : 'Mostrar procesadas'}
            </button>
            {expandedSections.username_change_requests && others.map(r => (
              <div key={r.id} className="claim-card opacity-75">
                <div className="claim-header">
                  <span className="claim-title">{r.old_username} → {r.requested_username}</span>
                  <div className="flex items-center gap-2">
                    {renderStatusBadge(r.estado)}
                    <button className="btn-action btn-revert p-1" title="Revertir" onClick={() => handleAction(`/api/username-change/${r.id}/revert`)}>
                      <i className="bi bi-arrow-counterclockwise"></i>
                    </button>
                  </div>
                </div>
                <div className="claim-body">
                  <div className="claim-row"><span className="claim-label">Motivo decisión:</span> {r.decision_reason}</div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    );
  };

  const renderMachineEdits = () => {
    const pending = data.machine_edit_requests.filter(r => r.estado === 'pendiente');
    const others = data.machine_edit_requests.filter(r => r.estado !== 'pendiente');

    return (
      <div className="claims-section">
        <div className="section-header">
          <h2><i className="bi bi-wrench-adjustable"></i> Peticiones de edición de máquinas</h2>
          <p className="section-subtitle">Cambios enviados por los autores que requieren aprobación.</p>
        </div>

        {pending.length > 0 ? pending.map(r => (
          <div key={r.id} className="claim-card">
            <div className="claim-header">
              <span className="claim-title">Máquina ID {r.machine_id} | {r.origen}</span>
              {renderStatusBadge(r.estado)}
            </div>
            <div className="claim-body">
              <div className="claim-row"><span className="claim-label">Autor:</span> {r.autor}</div>
              <div className="claim-row"><span className="claim-label">Fecha:</span> {r.fecha}</div>
              <div className="mt-2 text-sm font-semibold text-[var(--accent-cyan)]">Cambios propuestos:</div>
              <ul className="details-list">
                {Object.entries(r.nuevos || {}).map(([key, val]) => (
                  <li key={key}><strong>{key}:</strong> {val}</li>
                ))}
              </ul>
            </div>
            <div className="claim-actions">
              <button className="btn-action btn-approve" onClick={() => handleAction(`/api/machine_edits/${r.id}/approve`)}>
                <i className="bi bi-check-circle"></i> Aprobar
              </button>
              <button className="btn-action btn-reject" onClick={() => handleAction(`/api/machine_edits/${r.id}/reject`)}>
                <i className="bi bi-x-circle"></i> Rechazar
              </button>
            </div>
          </div>
        )) : <p className="text-secondary text-sm mb-4">No hay peticiones pendientes.</p>}

        {others.length > 0 && (
          <>
            <button className="collapse-btn" onClick={() => toggleSection('machine_edit_requests')}>
              {expandedSections.machine_edit_requests ? 'Ocultar archivadas' : 'Mostrar archivadas'}
            </button>
            {expandedSections.machine_edit_requests && others.map(r => (
              <div key={r.id} className="claim-card opacity-75">
                <div className="claim-header">
                  <span className="claim-title">Máquina ID {r.machine_id}</span>
                  <div className="flex items-center gap-2">
                    {renderStatusBadge(r.estado)}
                    <button className="btn-action btn-revert p-1" title="Revertir" onClick={() => handleAction(`/api/machine_edits/${r.id}/revert`)}>
                      <i className="bi bi-arrow-counterclockwise"></i>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    );
  };

  const renderNameClaims = () => {
    const pending = data.name_claims.filter(n => n.estado === 'pendiente');
    const others = data.name_claims.filter(n => n.estado !== 'pendiente');

    return (
      <div className="claims-section">
        <div className="section-header">
          <h2><i className="bi bi-person-badge"></i> Registro de nombres duplicados</h2>
          <p className="section-subtitle">Solicitudes de registro de nombres existentes o similares.</p>
        </div>

        {pending.length > 0 ? pending.map(p => (
          <div key={p.id} className="claim-card">
            <div className="claim-header">
              <span className="claim-title">{p.nombre_solicitado}</span>
              {renderStatusBadge(p.estado)}
            </div>
            <div className="claim-body">
              <div className="claim-row"><span className="claim-label">Usuario:</span> {p.username}</div>
              <div className="claim-row"><span className="claim-label">Email:</span> {p.email}</div>
              <div className="claim-row"><span className="claim-label">Motivo:</span></div>
              <div className="claim-proof">{p.motivo}</div>
            </div>
            <div className="claim-actions">
              <button className="btn-action btn-approve" onClick={() => handleAction(`/api/nombre-claims/${p.id}/approve`)}>
                <i className="bi bi-check-circle"></i> Aprobar
              </button>
              <button className="btn-action btn-reject" onClick={() => handleAction(`/api/nombre-claims/${p.id}/reject`)}>
                <i className="bi bi-x-circle"></i> Rechazar
              </button>
            </div>
          </div>
        )) : <p className="text-secondary text-sm mb-4">No hay peticiones pendientes.</p>}

        {others.length > 0 && (
          <>
            <button className="collapse-btn" onClick={() => toggleSection('name_claims')}>
              {expandedSections.name_claims ? 'Ocultar archivadas' : 'Mostrar archivadas'}
            </button>
            {expandedSections.name_claims && others.map(p => (
              <div key={p.id} className="claim-card opacity-75">
                <div className="claim-header">
                  <span className="claim-title">{p.nombre_solicitado}</span>
                  <div className="flex items-center gap-2">
                    {renderStatusBadge(p.estado)}
                    <button className="btn-action btn-revert p-1" title="Revertir" onClick={() => handleAction(`/api/nombre-claims/${p.id}/revert`)}>
                      <i className="bi bi-arrow-counterclockwise"></i>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    );
  };

  const renderWriteupEdits = () => {
    const pending = data.edit_requests.filter(r => r.estado === 'pendiente');
    const others = data.edit_requests.filter(r => r.estado !== 'pendiente');

    return (
      <div className="claims-section">
        <div className="section-header">
          <h2><i className="bi bi-pencil-square"></i> Edición de Writeups</h2>
          <p className="section-subtitle">Cambios solicitados en writeups publicados.</p>
        </div>

        {pending.length > 0 ? pending.map(r => (
          <div key={r.id} className="claim-card">
            <div className="claim-header">
              <span className="claim-title">Writeup ID {r.writeup_id}</span>
              {renderStatusBadge(r.estado)}
            </div>
            <div className="claim-body">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <h5 className="font-bold mb-2">Datos actuales</h5>
                  <ul className="details-list">
                    <li><strong>Máquina:</strong> {r.maquina_actual}</li>
                    <li><strong>Autor:</strong> {r.autor_actual}</li>
                    <li><strong>Tipo:</strong> {r.tipo_actual}</li>
                  </ul>
                </div>
                <div>
                  <h5 className="font-bold mb-2 text-[var(--accent-cyan)]">Propuesta nueva</h5>
                  <ul className="details-list">
                    <li><strong>Máquina:</strong> {r.maquina_nueva}</li>
                    <li><strong>Autor:</strong> {r.autor_nuevo}</li>
                    <li><strong>Tipo:</strong> {r.tipo_nuevo}</li>
                  </ul>
                </div>
              </div>
            </div>
            <div className="claim-actions">
              <button className="btn-action btn-approve" onClick={() => handleAction(`/api/writeup_edits/${r.id}/approve`)}>
                <i className="bi bi-check-circle"></i> Aprobar
              </button>
              <button className="btn-action btn-reject" onClick={() => handleAction(`/api/writeup_edits/${r.id}/reject`)}>
                <i className="bi bi-x-circle"></i> Rechazar
              </button>
            </div>
          </div>
        )) : <p className="text-secondary text-sm mb-4">No hay peticiones pendientes.</p>}

        {others.length > 0 && (
          <>
            <button className="collapse-btn" onClick={() => toggleSection('edit_requests')}>
              {expandedSections.edit_requests ? 'Ocultar archivadas' : 'Mostrar archivadas'}
            </button>
            {expandedSections.edit_requests && others.map(r => (
              <div key={r.id} className="claim-card opacity-75">
                <div className="claim-header">
                  <span className="claim-title">Writeup ID {r.writeup_id}</span>
                  <div className="flex items-center gap-2">
                    {renderStatusBadge(r.estado)}
                    <button className="btn-action btn-revert p-1" title="Revertir" onClick={() => handleAction(`/api/writeup_edits/${r.id}/revert`)}>
                      <i className="bi bi-arrow-counterclockwise"></i>
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    );
  }


  return (
    <div className="p-0 min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)] font-body">
      <Header />

      <div className="peticiones-container mt-20">
        <div className="peticiones-header">
          <h1>Centro de Peticiones</h1>
          <p className="peticiones-subtitle">
            Gestión de reclamaciones de autoría, peticiones de edición, cambios de username y registros duplicados.
          </p>
        </div>

        <div className="peticiones-content">
          {renderMachineClaims()}
          {renderUsernameRequests()}
          {renderMachineEdits()}
          {renderNameClaims()}
          {renderWriteupEdits()}
        </div>
      </div>
    </div>
  );
};

export default PeticionesPage;
