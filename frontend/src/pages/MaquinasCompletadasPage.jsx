import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './MaquinasCompletadasPage.css';

const MaquinasCompletadasPage = () => {
    const [data, setData] = useState({
        completed_machines: [],
        total_machines: 0,
        completed_count: 0,
        completion_percentage: 0
    });
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    useEffect(() => {
        fetch('/api/maquinas-hechas', { credentials: 'include' })
            .then(res => {
                if (res.status === 401 || res.status === 403) {
                    window.location.href = '/login';
                    throw new Error("Unauthorized");
                }
                return res.json();
            })
            .then(data => {
                setData(data);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching completed machines:", err);
                if (err.message === "Unauthorized") return;
                setLoading(false);
            });
    }, []);

    if (loading) {
        return (
            <div className="completed-machines-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
                <div className="loading-spinner"></div>
            </div>
        );
    }

    return (
        <div className="completed-machines-container">
            <div className="completed-header">
                <h1><i className="bi bi-check-circle-fill"></i> Máquinas Completadas</h1>
                <p>Tu progreso en DockerLabs</p>
            </div>

            {/* Progress Bar Section */}
            <div className="progress-section">
                <div className="progress-label">
                    <span>Progreso Total</span>
                    <span className="progress-percentage">{data.completion_percentage}%</span>
                </div>
                <div className="progress-bar-container">
                    <div
                        className="progress-bar-fill"
                        style={{ width: `${data.completion_percentage}%` }}
                    ></div>
                </div>
                <div className="progress-text">
                    {data.completed_count} de {data.total_machines} máquinas completadas
                </div>
            </div>

            {data.completed_machines.length > 0 ? (
                <>
                    <div className="completed-stats">
                        <div className="stat-card">
                            <div className="stat-number">{data.completed_machines.length}</div>
                            <div className="stat-label">Máquinas Completadas</div>
                        </div>
                    </div>

                    <div className="machines-grid">
                        {data.completed_machines.map((machine, index) => (
                            <div
                                key={index}
                                className="machine-card"
                                onClick={() => navigate('/')}
                            >
                                <div className="machine-card-content">
                                    <div className="machine-image-container">
                                        <img
                                            src={machine.imagen ? `/static/${machine.imagen}` : "/static/dockerlabs/images/logos/logo.png"}
                                            alt={machine.machine_name}
                                            className="machine-image"
                                            onError={(e) => { e.target.src = "/static/dockerlabs/images/logos/logo.png"; }}
                                        />
                                        <div className="machine-image-overlay"></div>
                                    </div>

                                    <div className="machine-card-body">
                                        <div className="machine-name">{machine.machine_name}</div>

                                        <div className="machine-info">
                                            {machine.dificultad && (
                                                <span
                                                    className={`difficulty-badge ${machine.clase || ''}`}
                                                    style={{ background: machine.color, color: '#000' }}
                                                >
                                                    {machine.dificultad}
                                                </span>
                                            )}
                                        </div>

                                        {machine.autor && (
                                            <div className="author-info">
                                                <i className="bi bi-person-fill"></i>{machine.autor}
                                            </div>
                                        )}

                                        <div className="completed-date">
                                            <i className="bi bi-check-circle-fill"></i>
                                            {machine.completed_at ?
                                                (machine.completed_at.includes('.') ?
                                                    `Completada el ${machine.completed_at.split('.')[0]}` :
                                                    `Completada el ${machine.completed_at}`
                                                ) : ''
                                            }
                                        </div>
                                    </div>
                                </div>
                            </div>
                        ))}
                    </div>
                </>
            ) : (
                <div className="empty-state">
                    <i className="bi bi-inbox"></i>
                    <h2>No has completado ninguna máquina todavía</h2>
                    <p>Explora el catálogo de máquinas y marca las que completes</p>
                    <button onClick={() => navigate('/')} className="btn-primary">
                        <i className="bi bi-grid-3x3-gap-fill"></i> Ver Máquinas
                    </button>
                </div>
            )}
        </div>
    );
};

export default MaquinasCompletadasPage;
