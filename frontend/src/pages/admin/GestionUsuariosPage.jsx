import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import './GestionUsuariosPage.css';

// Helper to get CSRF token
const getCsrfToken = () => {
  return document.cookie.split('; ')
    .find(row => row.startsWith('csrf_token='))
    ?.split('=')[1];
};

const GestionUsuariosPage = () => {
  const { user, loading: authLoading } = useAuth();
  const [usuarios, setUsuarios] = useState([]);
  const [loadingUsers, setLoadingUsers] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [showEmails, setShowEmails] = useState(false);
  const [showUsers, setShowUsers] = useState(false);

  const navigate = useNavigate();

  // Redirect if not authenticated or not authorized
  useEffect(() => {
    if (!authLoading) {
      if (!user?.is_authenticated) {
        navigate('/login');
      } else if (user?.user?.role !== 'admin' && user?.user?.role !== 'moderador') {
        navigate('/403'); // Or dashboard with error
      } else {
        fetchUsers();
      }
    }
  }, [user, authLoading, navigate]);

  const currentUserRole = user?.user?.role || '';

  const fetchUsers = () => {
    setLoadingUsers(true);
    fetch('/api/usuarios', { credentials: 'include' })
      .then(res => {
        if (res.status === 401 || res.status === 403) {
          // controlled by useEffect above, but safe guard
          throw new Error("Unauthorized");
        }
        return res.json();
      })
      .then(data => {
        setUsuarios(data.usuarios || []);
        setLoadingUsers(false);
      })
      .catch(err => {
        console.error("Error fetching users:", err);
        setLoadingUsers(false);
      });
  };

  const handleRoleChange = async (userId, newRole) => {
    if (!window.confirm(`¿Estás seguro de cambiar el rol a ${newRole}?`)) return;

    try {
      const response = await fetch('/api/update_user_role', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ user_id: userId, role: newRole }),
        credentials: 'include'
      });

      if (response.ok) {
        // Update local state to reflect change without full reload
        setUsuarios(prev => prev.map(u =>
          u.id === userId ? { ...u, role: newRole } : u
        ));
      } else {
        const err = await response.json();
        alert("Error: " + (err.error || "No se pudo actualizar el rol"));
      }
    } catch (error) {
      console.error("Error updating role:", error);
      alert("Error de conexión");
    }
  };

  const handleDeleteUser = async (userId) => {
    if (!window.confirm("¿Seguro que quieres eliminar este usuario? Esta acción no se puede deshacer.")) return;

    try {
      const response = await fetch('/api/delete_user', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ user_id: userId }),
        credentials: 'include'
      });

      if (response.ok) {
        setUsuarios(prev => prev.filter(u => u.id !== userId));
      } else {
        const err = await response.json();
        alert("Error: " + (err.error || "No se pudo eliminar el usuario"));
      }
    } catch (error) {
      console.error("Error deleting user:", error);
      alert("Error de conexión");
    }
  };

  const filteredUsers = usuarios.filter(user =>
    user.username.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (user.email && user.email.toLowerCase().includes(searchTerm.toLowerCase())) ||
    user.role.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (authLoading || loadingUsers) return <div className="gestion-usuarios-container"><div className="loading-spinner">Cargando usuarios...</div></div>;

  return (
    <div className="gestion-usuarios-container">
      <div className="gestion-usuarios-header">
        <h2><i className="bi bi-people-fill"></i> Gestión de Usuarios</h2>
      </div>

      <div className="search-bar-container">
        <div className="input-group">
          <span className="input-group-text"><i className="bi bi-search"></i></span>
          <input
            type="text"
            className="form-control bg-dark text-light border-secondary"
            placeholder="Buscar por usuario, email o rol..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="table-responsive">
        <table className="table" id="gestionUsuariosTable">
          <thead>
            <tr>
              <th>ID</th>
              <th>
                Usuario
                <button className="header-btn-toggle" onClick={() => setShowUsers(!showUsers)} title="Mostrar/Ocultar usuarios">
                  <i className={`bi ${showUsers ? 'bi-eye-slash-fill' : 'bi-eye-fill'}`}></i>
                </button>
              </th>
              {currentUserRole === 'admin' && (
                <>
                  <th>
                    Email
                    <button className="header-btn-toggle" onClick={() => setShowEmails(!showEmails)} title="Mostrar/Ocultar emails">
                      <i className={`bi ${showEmails ? 'bi-eye-slash-fill' : 'bi-eye-fill'}`}></i>
                    </button>
                  </th>
                  <th>PIN</th>
                </>
              )}
              <th>Rol</th>
              <th>Creado</th>
              {currentUserRole === 'admin' && <th className="text-center">Acciones</th>}
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length > 0 ? (
              filteredUsers.map(user => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td className="user-cell">
                    {showUsers ? (
                      <span className="user-real text-info fw-bold">{user.username}</span>
                    ) : (
                      <span className="user-censored">***************</span>
                    )}
                  </td>
                  {currentUserRole === 'admin' && (
                    <>
                      <td className="email-cell">
                        {showEmails ? (
                          <span className="email-real text-warning">{user.email}</span>
                        ) : (
                          <span className="email-censored">***************</span>
                        )}
                      </td>
                      <td>
                        {user.recovery_pin_plain ? (
                          <span className="badge bg-info">{user.recovery_pin_plain}</span>
                        ) : (
                          <span className="text-muted small">N/A</span>
                        )}
                      </td>
                    </>
                  )}
                  <td>
                    {currentUserRole === 'admin' ? (
                      <select
                        className="form-select form-select-sm"
                        value={user.role}
                        onChange={(e) => handleRoleChange(user.id, e.target.value)}
                      >
                        <option value="jugador">Jugador</option>
                        <option value="moderador">Moderador</option>
                        <option value="admin">Admin</option>
                      </select>
                    ) : (
                      <span className="badge bg-secondary" style={{ textTransform: 'capitalize' }}>{user.role}</span>
                    )}
                  </td>
                  <td>{new Date(user.created_at).toLocaleDateString()}</td>
                  {currentUserRole === 'admin' && (
                    <td className="text-center">
                      <button
                        className="btn btn-sm btn-danger"
                        onClick={() => handleDeleteUser(user.id)}
                      >
                        <i className="bi bi-trash-fill"></i> Eliminar
                      </button>
                    </td>
                  )}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={currentUserRole === 'admin' ? 7 : 4} className="text-center py-4 text-muted">
                  No se encontraron usuarios
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default GestionUsuariosPage;
