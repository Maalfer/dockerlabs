import React, { useState, useEffect, useRef } from 'react';
import './AddMachine.css';

// Helper to get CSRF token
const getCsrf = () =>
    fetch('/api/csrf', { credentials: 'include' })
        .then(r => r.ok ? r.json() : {})
        .then(d => d.csrf_token || '');

const AddMachine = ({ onMachineAdded }) => {
    const [formData, setFormData] = useState({
        destino: 'docker',
        nombre: '',
        dificultad: '',
        autor: '',
        fecha: '',
        descripcion: '',
        link_descarga: '',
        pin: '',
        entorno_real: false
    });

    const [imageFile, setImageFile] = useState(null);
    const [previewUrl, setPreviewUrl] = useState(null);

    // Author search state
    const [allUsers, setAllUsers] = useState([]);
    const [filteredUsers, setFilteredUsers] = useState([]);
    const [showDropdown, setShowDropdown] = useState(false);
    const [authorSearch, setAuthorSearch] = useState('');
    const [loadingUsers, setLoadingUsers] = useState(false);

    const [loading, setLoading] = useState(false);
    const [message, setMessage] = useState({ text: '', type: '' });

    // Refs for clicking outside
    const dropdownRef = useRef(null);
    const searchInputRef = useRef(null);

    useEffect(() => {
        // Load users for author dropdown
        setLoadingUsers(true);
        fetch('/api/get_users')
            .then(res => res.json())
            .then(data => {
                if (data.users) {
                    setAllUsers(data.users);
                    setFilteredUsers(data.users);
                }
            })
            .catch(err => console.error("Error loading users:", err))
            .finally(() => setLoadingUsers(false));

        // Click outside listener
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target) &&
                searchInputRef.current && !searchInputRef.current.contains(event.target)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const handleAuthorSearchChange = (e) => {
        const term = e.target.value;
        setAuthorSearch(term);
        setShowDropdown(true);

        if (term.trim() === '') {
            setFilteredUsers(allUsers);
        } else {
            setFilteredUsers(allUsers.filter(u =>
                u.username.toLowerCase().includes(term.toLowerCase())
            ));
        }

        // If user clears input, clear selected author
        if (term === '') setFormData(prev => ({ ...prev, autor: '' }));
    };

    const selectAuthor = (username) => {
        setAuthorSearch(username);
        setFormData(prev => ({ ...prev, autor: username }));
        setShowDropdown(false);
    };

    const handleImageChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            setImageFile(file);
            // Create preview
            const url = URL.createObjectURL(file);
            setPreviewUrl(url);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setMessage({ text: '', type: '' });
        setLoading(true);

        const csrf = await getCsrf();

        const data = new FormData();
        Object.keys(formData).forEach(key => {
            if (key === 'entorno_real') {
                if (formData[key]) data.append(key, '1');
            } else {
                data.append(key, formData[key]);
            }
        });

        if (imageFile) {
            data.append('imagen', imageFile);
        }

        try {
            const response = await fetch('/api/add-maquina', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrf
                },
                body: data,
                credentials: 'include'
            });

            const result = await response.json();

            if (response.ok) {
                setMessage({ text: result.message || 'Máquina añadida correctamente', type: 'success' });
                // Reset form
                setFormData({
                    destino: 'docker', nombre: '', dificultad: '', autor: '',
                    fecha: '', descripcion: '', link_descarga: '', pin: '', entorno_real: false
                });
                setAuthorSearch('');
                setImageFile(null);
                setPreviewUrl(null);
                if (onMachineAdded) onMachineAdded();
            } else {
                setMessage({ text: result.error || 'Error al añadir máquina', type: 'error' });
            }
        } catch (error) {
            setMessage({ text: 'Error de conexión', type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const isBunker = formData.destino === 'bunker';
    const isEntornoReal = isBunker && formData.entorno_real;

    return (
        <div className="add-machine-container">
            <h2 className="add-machine-title">
                <i className="bi bi-plus-circle-dotted"></i> Añadir Nueva Máquina
            </h2>

            {message.text && (
                <div className={`alert alert-${message.type === 'error' ? 'danger' : 'success'}`}>
                    {message.text}
                </div>
            )}

            <div className="add-machine-grid">
                <form onSubmit={handleSubmit} className="add-machine-main">
                    <div className="form-group">
                    <label className="form-label">Enviar a</label>
                    <select
                        name="destino"
                        className="form-select"
                        value={formData.destino}
                        onChange={handleChange}
                    >
                        <option value="docker">DockerLabs (página principal)</option>
                        <option value="bunker">BunkerLabs (zona protegida)</option>
                    </select>
                </div>

                {isBunker && (
                    <div className="form-group">
                        <div className="form-check">
                            <input
                                type="checkbox"
                                name="entorno_real"
                                id="entorno_real"
                                className="form-check-input"
                                checked={formData.entorno_real}
                                onChange={handleChange}
                            />
                            <label className="form-check-label" htmlFor="entorno_real">
                                <strong>Marcar como Entorno Real</strong>
                                <div className="form-text" style={{ marginTop: 0 }}>Esta máquina simula un entorno de producción real</div>
                            </label>
                        </div>
                    </div>
                )}

                {isBunker && !isEntornoReal && (
                    <div className="form-group">
                        <label className="form-label">PIN de la máquina (Flag)</label>
                        <input
                            type="text"
                            name="pin"
                            className="form-control"
                            placeholder="Introduce el PIN/Flag para esta máquina"
                            value={formData.pin}
                            onChange={handleChange}
                            required
                        />
                    </div>
                )}

                <div className="form-group">
                    <label className="form-label">Nombre de la máquina</label>
                    <input
                        type="text"
                        name="nombre"
                        className="form-control"
                        value={formData.nombre}
                        onChange={handleChange}
                        required
                    />
                </div>

                {!isEntornoReal && (
                    <div className="form-group">
                        <label className="form-label">Dificultad</label>
                        <select
                            name="dificultad"
                            className="form-select"
                            value={formData.dificultad}
                            onChange={handleChange}
                            required
                        >
                            <option value="">Selecciona una dificultad</option>
                            <option value="Muy Fácil">Muy fácil</option>
                            <option value="Fácil">Fácil</option>
                            <option value="Medio">Medio</option>
                            <option value="Difícil">Difícil</option>
                        </select>
                    </div>
                )}

                <div className="form-group">
                    <label className="form-label">Autor</label>
                    <div className="custom-select-wrapper">
                        <input
                            type="text"
                            ref={searchInputRef}
                            className="form-control"
                            placeholder="Buscar usuario..."
                            value={authorSearch}
                            onChange={handleAuthorSearchChange}
                            onFocus={() => setShowDropdown(true)}
                            required
                        />
                        {showDropdown && (
                            <div className="custom-select-dropdown" ref={dropdownRef}>
                                {loadingUsers ? (
                                    <div className="p-3 text-muted text-center">Cargando...</div>
                                ) : filteredUsers.length > 0 ? (
                                    filteredUsers.map(user => (
                                        <div
                                            key={user.id}
                                            className={`custom-select-option ${user.username === formData.autor ? 'selected' : ''}`}
                                            onClick={() => selectAuthor(user.username)}
                                        >
                                            <i className="bi bi-person-circle"></i> {user.username}
                                        </div>
                                    ))
                                ) : (
                                    <div className="p-3 text-muted text-center">No se encontraron usuarios</div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                <div className="form-group">
                    <label className="form-label">Fecha</label>
                    <input
                        type="date"
                        name="fecha"
                        className="form-control"
                        value={formData.fecha}
                        onChange={handleChange}
                        required
                    />
                </div>

                <div className="form-group">
                    <label className="form-label">Imagen de la máquina</label>
                    <input
                        type="file"
                        name="imagen"
                        className="form-control"
                        accept="image/*"
                        onChange={handleImageChange}
                    />
                    {previewUrl && (
                        <div className="mt-2 text-center">
                            <img src={previewUrl} alt="Preview" style={{ maxHeight: '100px', borderRadius: '4px' }} />
                        </div>
                    )}
                </div>

                <div className="form-group">
                    <label className="form-label">Descripción</label>
                    <textarea
                        name="descripcion"
                        className="form-control"
                        rows="4"
                        value={formData.descripcion}
                        onChange={handleChange}
                        placeholder="Descripción de lo que se aprende en esta máquina"
                        required
                    ></textarea>
                </div>

                <div className="form-group">
                    <label className="form-label">Link de descarga</label>
                    <input
                        type="url"
                        name="link_descarga"
                        className="form-control"
                        placeholder="https://..."
                        value={formData.link_descarga}
                        onChange={handleChange}
                        required
                    />
                </div>

                <button type="submit" className="btn-submit" disabled={loading}>
                    {loading ? <div className="loading-spinner"></div> : <i className="bi bi-save"></i>}
                    {loading ? ' Guardando...' : ' Guardar máquina'}
                </button>
            </form>

                <aside className="add-machine-side">
                    <div className="preview-box">
                        {previewUrl ? (
                            <img src={previewUrl} alt="Preview" />
                        ) : (
                            <div style={{textAlign: 'center', color: 'var(--text-muted)'}}>Vista previa de la imagen</div>
                        )}
                        <div style={{width: '100%'}}>
                            <small className="form-text">La imagen se subirá junto con la máquina y se mostrará en la ficha.</small>
                        </div>
                    </div>

                    <div style={{height: '12px'}} />

                    <div className="meta-list">
                        <div className="meta-item"><span>Destino</span><strong>{formData.destino}</strong></div>
                        <div className="meta-item"><span>Autor</span><strong>{formData.autor || '-'}</strong></div>
                        <div className="meta-item"><span>Fecha</span><strong>{formData.fecha || '-'}</strong></div>
                        {!isEntornoReal && <div className="meta-item"><span>Dificultad</span><strong>{formData.dificultad || '-'}</strong></div>}
                        {isBunker && !isEntornoReal && <div className="meta-item"><span>PIN</span><strong>{formData.pin || '-'}</strong></div>}
                        <div className="meta-item"><span>Link</span><a style={{color: 'var(--primary-color)'}} href={formData.link_descarga || '#'} target="_blank" rel="noreferrer">{formData.link_descarga ? 'Abrir' : '-'}</a></div>
                    </div>
                </aside>
            </div>
        </div>
    );
};

export default AddMachine;
