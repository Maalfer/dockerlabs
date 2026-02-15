import React, { useState, useEffect } from 'react';
import './GestionMaquinasPage.css';
import AddMachine from '../components/AddMachine';

const GestionMaquinasPage = () => {
    const [activeTab, setActiveTab] = useState('docker');
    const [machines, setMachines] = useState({ docker: [], bunker: [] });
    const [loading, setLoading] = useState(true);
    const [showAddModal, setShowAddModal] = useState(false);
    const [currentUser, setCurrentUser] = useState(null);

    const fetchMachines = () => {
        setLoading(true);
        fetch('/api/maquinas', { credentials: 'include' })
            .then(res => res.json())
            .then(data => {
                setMachines(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching machines:", err);
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

    const handleMachineAdded = () => {
        setShowAddModal(false);
        fetchMachines(); // Refresh list
    };

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
                            <th>Fecha</th>
                            <th>Imagen</th>
                            <th>Acciones</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.length === 0 ? (
                            <tr>
                                <td colSpan="7" style={{ textAlign: 'center', padding: '2rem' }}>
                                    No hay máquinas registradas.
                                </td>
                            </tr>
                        ) : (
                            data.map(m => (
                                <tr key={m.id}>
                                    <td>{m.id}</td>
                                    <td>
                                        <strong>{m.nombre}</strong>
                                    </td>
                                    <td>
                                        <span className={`badge ${m.dificultad.toLowerCase().replace(' ', '-').replace('á', 'a').replace('í', 'i')}`}>
                                            {m.dificultad}
                                        </span>
                                    </td>
                                    <td>{m.autor}</td>
                                    <td>{m.fecha}</td>
                                    <td>
                                        {m.imagen ? (
                                            <img src={`/static/${m.imagen}`} alt={m.nombre} className="logo-preview" onError={(e) => e.target.style.display = 'none'} />
                                        ) : (
                                            <div className="logo-preview" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc' }}>?</div>
                                        )}
                                    </td>
                                    <td>
                                        {/* Edit/Delete actions would go here - keeping it simple for now as requested task was specifically about ADDING machines */}
                                        <button className="action-btn edit" title="Editar (Próximamente)">
                                            <i className="bi bi-pencil"></i>
                                        </button>
                                        <button className="action-btn delete" title="Eliminar (Próximamente)">
                                            <i className="bi bi-trash"></i>
                                        </button>
                                    </td>
                                </tr>
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
