import React, { useState, useEffect } from 'react';
import './GestionMaquinasPage.css';
import AddMachine from '../components/AddMachine';
import MachineRow from '../components/MachineRow';

const GestionMaquinasPage = () => {
    const [activeTab, setActiveTab] = useState('docker');
    const [machines, setMachines] = useState({ docker: [], bunker: [] });
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [currentUser, setCurrentUser] = useState(null);

    const fetchMachines = () => {
        setLoading(true);
        fetch('/api/maquinas', { credentials: 'include' })
            .then(res => {
                if (res.status === 401 || res.status === 403) {
                    window.location.href = '/login';
                    throw new Error("Unauthorized");
                }
                return res.json();
            })
            .then(data => {
                setMachines(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching machines:", err);
                if (err.message === "Unauthorized") window.location.href = "/login";
                setLoading(false);
            });
    };

    useEffect(() => {
        fetchMachines();
        // Get current user info for permission checks (optional, but good for UI state)
        fetch('/api/me', { credentials: 'include' })
            .then(res => res.json())
            .then(data => setCurrentUser(data))
            .catch(err => console.error(err));
    }, []);

    const handleUpdate = async (machineData) => {
        try {
            const response = await fetch('/api/maquina', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken() // Need to implement or grab from cookie/meta
                },
                body: JSON.stringify(machineData),
                credentials: 'include'
            });
            if (response.ok) {
                fetchMachines();
            } else {
                const err = await response.json();
                alert("Error al actualizar: " + (err.error || "Desconocido"));
            }
        } catch (error) {
            console.error("Update failed", error);
        }
    };

    const handleDelete = async (id, origen) => {
        if (!window.confirm("¿Seguro que quieres eliminar esta máquina?")) return;

        try {
            const response = await fetch('/api/maquina', {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ id, origen }),
                credentials: 'include'
            });
            if (response.ok) {
                fetchMachines();
            } else {
                alert("Error al eliminar");
            }
        } catch (error) {
            console.error("Delete failed", error);
        }
    };

    const handleUploadLogo = async (id, origen, file) => {
        const formData = new FormData();
        formData.append('logo', file);
        formData.append('machine_id', id);
        formData.append('origen', origen);
        formData.append('csrf_token', getCsrfToken()); // Form data needs this

        const response = await fetch('/gestion-maquinas/upload-logo', {
            method: 'POST',
            body: formData,
            credentials: 'include',
            headers: {
                'X-CSRFToken': getCsrfToken() // Double measure
            }
        });

        if (response.ok) {
            fetchMachines(); // Refresh to see new logo
        } else {
            throw new Error("Upload failed");
        }
    };

    const handleToggleGuest = async (id) => {
        if (!window.confirm("¿Seguro que quieres cambiar el estado de acceso para invitados?")) return;

        const formData = new FormData();
        formData.append('id', id);
        formData.append('csrf_token', getCsrfToken());

        try {
            const response = await fetch('/gestion-maquinas/toggle-guest-access', {
                method: 'POST',
                body: formData,
                credentials: 'include'
            });

            if (response.ok) {
                fetchMachines();
            } else {
                const err = await response.json();
                alert("Error: " + (err.error || "Desconocido"));
            }
        } catch (error) {
            console.error("Toggle guest failed", error);
        }
    };

    // Helper to get CSRF token (usually in meta tag or cookie)
    // For now, simpler to fetch it or rely on cookie if configured.
    // The previous implementation used a local getCsrf in AddMachine. Let's start with that pattern.
    const [csrf, setCsrf] = useState('');
    useEffect(() => {
        fetch('/api/csrf', { credentials: 'include' })
            .then(r => r.json())
            .then(d => setCsrf(d.csrf_token || ''));
    }, []);

    const getCsrfToken = () => csrf;

    const MachineTable = ({ data, type }) => (
        <div className="table-card">
            <div className="table-responsive">
                <table className="custom-table">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Nombre</th>
                            <th>Dificultad</th>
                            <th>Autor</th>
                            <th>Enlace Autor</th>
                            <th>Fecha</th>
                            <th>Imagen</th>
                            <th>Descripción</th>
                            <th>Link Descarga</th>
                            <th>Categoría</th>
                            {type === 'bunker' && <th>Guest</th>}
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.length === 0 ? (
                            <tr>
                                <td colSpan="12" style={{ textAlign: 'center', padding: '2rem' }}>
                                    No hay máquinas registradas.
                                </td>
                            </tr>
                        ) : (
                            data.map(m => (
                                <MachineRow
                                    key={m.id}
                                    machine={m}
                                    type={type}
                                    onUpdate={handleUpdate}
                                    onDelete={handleDelete}
                                    onUploadLogo={handleUploadLogo}
                                    onToggleGuest={handleToggleGuest}
                                />
                            ))
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );

    return (
        <div className="gestion-maquinas-container">
            <header className="page-header">
                <h2 className="page-title">Gestión de Máquinas</h2>

                <div className="header-actions">
                    <div className="platform-switcher">
                        <button
                            className={`platform-btn ${activeTab === 'docker' ? 'active' : ''}`}
                            onClick={() => setActiveTab('docker')}
                        >
                            <i className="bi bi-box-seam"></i> DockerLabs
                        </button>
                        <button
                            className={`platform-btn ${activeTab === 'bunker' ? 'active' : ''}`}
                            onClick={() => setActiveTab('bunker')}
                        >
                            <i className="bi bi-shield-lock"></i> BunkerLabs
                        </button>
                    </div>

                    <button className="btn-add-machine" onClick={() => setShowAddModal(true)}>
                        <i className="bi bi-plus-lg"></i> Añadir Máquina
                    </button>
                </div>
            </header>

            {loading ? (
                <div style={{ textAlign: 'center', padding: '3rem' }}>
                    <div className="loading-spinner" style={{ width: '3rem', height: '3rem', margin: '0 auto' }}></div>
                    <p style={{ marginTop: '1rem', color: 'var(--text-secondary)' }}>Cargando máquinas...</p>
                </div>
            ) : (
                <div className="tab-content">
                    {activeTab === 'docker' && <MachineTable data={machines.docker} type="docker" />}
                    {activeTab === 'bunker' && <MachineTable data={machines.bunker} type="bunker" />}
                </div>
            )}

            {showAddModal && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <button className="modal-close" onClick={() => setShowAddModal(false)}>
                            <i className="bi bi-x"></i>
                        </button>
                        <AddMachine onMachineAdded={handleMachineAdded} />
                    </div>
                </div>
            )}
        </div>
    );
};

export default GestionMaquinasPage;
