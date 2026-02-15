import React from 'react';
import { useNavigate } from 'react-router-dom';
import AddMachine from '../components/AddMachine';
import './AddMachinePage.css';

const AddMachinePage = () => {
    const navigate = useNavigate();

    const handleMachineAdded = () => {
        // Option 1: Stay on page to add another
        // Option 2: Navigate to list
        // Let's scroll to top and show message (handled by component), 
        // maybe ask user if they want to go to list?
        // For now, let component handle success message.
        window.scrollTo(0, 0);
    };

    return (
        <div className="add-machine-page-container">
            <div className="add-machine-page-header">
                <h1><i className="bi bi-hdd-network"></i> Gestión de Añadir Máquinas</h1>
                <p>Añade nuevas máquinas a DockerLabs o BunkerLabs</p>
            </div>

            <div className="add-machine-wrapper">
                <div className="add-machine-intro">
                    <strong>Consejos rápidos</strong>
                    <ul style={{marginTop: '0.5rem', paddingLeft: '1rem'}}>
                        <li>Mantén un nombre descriptivo y único.</li>
                        <li>Incluye un enlace de descarga válido (HTTPS preferible).</li>
                        <li>Sube una imagen clara para la vista previa.</li>
                        <li>Selecciona correctamente destino y entorno.</li>
                    </ul>
                </div>

                <AddMachine onMachineAdded={handleMachineAdded} />
            </div>
        </div>
    );
};

export default AddMachinePage;
