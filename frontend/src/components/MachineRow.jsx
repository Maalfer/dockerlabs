
import React, { useState } from 'react';

const MachineRow = ({ machine, type, onUpdate, onDelete, onUploadLogo, onToggleGuest }) => {
    const [isEditing, setIsEditing] = useState(false);
    const [editData, setEditData] = useState({ ...machine });
    const [uploading, setUploading] = useState(false);

    // Sync state if machine prop changes (e.g. after refresh)
    React.useEffect(() => {
        setEditData({ ...machine });
    }, [machine]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setEditData(prev => ({ ...prev, [name]: value }));
    };

    const handleSave = () => {
        onUpdate({ ...editData, id: machine.id, origen: type });
        setIsEditing(false);
    };

    const handleFileChange = async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        setUploading(true);
        try {
            await onUploadLogo(machine.id, type, file);
        } catch (error) {
            console.error("Upload failed", error);
            alert("Error al subir la imagen");
        } finally {
            setUploading(false);
        }
    };

    const toggleGuestAccess = (e) => {
        // Optimistic update or call API directly?
        // Let's assume parent handles it or we call specific endpoint
        // existing implementation uses /gestion-maquinas/toggle-guest-access
        // We might need to implement this in the parent or here.
        // For now, let's stick to the main edit fields.
    };

    if (!isEditing) {
        return (
            <tr>
                <td>{machine.id}</td>
                <td onClick={() => setIsEditing(true)} style={{ cursor: 'pointer' }}><strong>{machine.nombre}</strong> <small>▼</small></td>
                <td onClick={() => setIsEditing(true)} style={{ cursor: 'pointer' }}>
                    <span className={`badge ${machine.dificultad.toLowerCase().replace(' ', '-').replace('á', 'a').replace('í', 'i')}`}>
                        {machine.dificultad}
                    </span>
                </td>
                <td onClick={() => setIsEditing(true)} style={{ cursor: 'pointer' }}>{machine.autor}</td>
                <td><a href={machine.enlace_autor} target="_blank" rel="noopener noreferrer">Link</a></td>
                <td onClick={() => setIsEditing(true)} style={{ cursor: 'pointer' }}>{machine.fecha}</td>
                <td>
                    <div className="logo-upload-wrapper">
                        {machine.imagen ? (
                            <img src={`/static/${machine.imagen}`} className="logo-preview" onError={(e) => e.target.style.display = 'none'} />
                        ) : (
                            <div className="logo-preview" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc' }}>?</div>
                        )}
                        <label className="btn-upload-icon" title="Subir logo">
                            <i className={`bi ${uploading ? 'bi-hourglass-split' : 'bi-upload'}`}></i>
                            <input type="file" className="d-none" accept="image/*" onChange={handleFileChange} disabled={uploading} />
                        </label>
                    </div>
                </td>
                <td className="text-truncate" style={{ maxWidth: '150px' }} title={machine.descripcion}>{machine.descripcion}</td>
                <td className="text-truncate" style={{ maxWidth: '100px' }} title={machine.link_descarga}><a href={machine.link_descarga} target="_blank">Descarga</a></td>
                <td>{machine.categoria || '-'}</td>
                {type === 'bunker' && (
                    <td className="text-center">
                        <button
                            className="btn-action guest-toggle"
                            onClick={() => onToggleGuest(machine.id)}
                            title={machine.guest_access ? 'Acceso permitido a invitados' : 'Acceso bloqueado a invitados'}
                            style={{ background: 'none', border: 'none', padding: 0 }}
                        >
                            {machine.guest_access ?
                                <i className="bi bi-unlock-fill text-success" style={{ fontSize: '1.2rem' }}></i> :
                                <i className="bi bi-lock-fill text-danger" style={{ fontSize: '1.2rem' }}></i>
                            }
                        </button>
                    </td>
                )}
                <td>
                    <div className="d-flex gap-2">
                        <button className="btn-action save" onClick={() => setIsEditing(true)} title="Editar">
                            <i className="bi bi-pencil"></i>
                        </button>
                        <button className="btn-action delete" onClick={() => onDelete(machine.id, type)} title="Eliminar máquina">
                            <i className="bi bi-trash"></i>
                        </button>
                    </div>
                </td>
            </tr>
        );
    }

    return (
        <tr>
            <td>{machine.id}</td>
            <td><input type="text" name="nombre" value={editData.nombre || ''} onChange={handleChange} className="input-minimal" placeholder="Nombre" /></td>
            <td>
                <select name="dificultad" value={editData.dificultad} onChange={handleChange} className="select-minimal">
                    <option value="Muy Fácil">Muy Fácil</option>
                    <option value="Fácil">Fácil</option>
                    <option value="Medio">Medio</option>
                    <option value="Difícil">Difícil</option>
                </select>
            </td>
            <td><input type="text" name="autor" value={editData.autor || ''} onChange={handleChange} className="input-minimal" readOnly style={{ opacity: 0.7 }} /></td>
            <td><input type="text" name="enlace_autor" value={editData.enlace_autor || ''} onChange={handleChange} className="input-minimal" placeholder="URL Autor" /></td>
            <td><input type="text" name="fecha" value={editData.fecha || ''} onChange={handleChange} className="input-minimal" placeholder="DD/MM/YYYY" /></td>
            <td>
                {/* Image upload separate from edit state, always available */}
                <div className="logo-upload-wrapper">
                    {machine.imagen ? (
                        <img src={`/static/${machine.imagen}`} className="logo-preview" onError={(e) => e.target.style.display = 'none'} />
                    ) : (
                        <div className="logo-preview" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#ccc' }}>?</div>
                    )}
                    <label className="btn-upload-icon" title="Subir logo">
                        <i className={`bi ${uploading ? 'bi-hourglass-split' : 'bi-upload'}`}></i>
                        <input type="file" className="d-none" accept="image/*" onChange={handleFileChange} disabled={uploading} />
                    </label>
                </div>
            </td>
            <td><textarea name="descripcion" value={editData.descripcion || ''} onChange={handleChange} className="input-minimal" rows="1" style={{ resize: 'vertical', minHeight: '2.5rem' }}></textarea></td>
            <td><input type="text" name="link_descarga" value={editData.link_descarga || ''} onChange={handleChange} className="input-minimal" /></td>
            <td>
                <select name="categoria" value={editData.categoria || ''} onChange={handleChange} className="select-minimal">
                    <option value="">-</option>
                    <option value="Hacking Web">Web</option>
                    <option value="Bug Bounty">Bug Bounty</option>
                    <option value="Hacking CMS">CMS</option>
                    <option value="Hacking Infraestructura">Infra</option>
                    <option value="Pivoting">Pivoting</option>
                </select>
            </td>
            {type === 'bunker' && <td>{/* Guest toggle not editable here? */}</td>}
            <td>
                <div className="d-flex gap-2">
                    <button className="btn-action save" onClick={handleSave} title="Guardar cambios">
                        <i className="bi bi-check-lg"></i>
                    </button>
                    <button className="btn-action delete" onClick={() => setIsEditing(false)} title="Cancelar">
                        <i className="bi bi-x-lg"></i>
                    </button>
                </div>
            </td>
        </tr>
    );
};

export default MachineRow;
