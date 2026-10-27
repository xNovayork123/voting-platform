import React, { useState, useEffect, useRef } from 'react';
import './ProfilePage.css';
import { useToast } from './Toast';
import Sidebar from './Sidebar';

const API_URL = '/api';

// Componente único que cubre las dos pantallas de "user management" que son
// mi parte: editar mi propio perfil (todos los usuarios) y administrar
// miembros (solo admins). Login/registro/logout NO viven aquí.
function ProfilePage({ user, setUser, onLogout, onNavigate }) {
  const toast = useToast();
  const [profile, setProfile] = useState(null);   // datos crudos de MI perfil (referencia/solo lectura)
  const [allUsers, setAllUsers] = useState([]);    // lista completa de usuarios, solo se llena si soy admin
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Edit own profile form
  // Formulario CONTROLADO de "My Profile": cada input está atado a este estado.
  const [form, setForm] = useState({ display_name: '', email: '', password: '', status: 'offline', profile_picture: '' });

  // Admin: which user is being edited
  // editingUser = null  ->  modal de edición cerrado.
  // editingUser = {...} ->  el objeto completo de la fila que se está editando.
  const [editingUser, setEditingUser] = useState(null);
  const [adminForm, setAdminForm] = useState({ display_name: '', email: '', password: '', is_admin: false, is_active: true });

  // Referencia al <input type="file"> oculto, para poder "clickearlo" desde
  // el botón bonito "Change Photo" sin mostrar el input feo del navegador.
  const fileInputRef = useRef();

  // Al montar la página: SIEMPRE pido mi propio perfil. Si además soy admin,
  // disparo una segunda petición para traer a todos los usuarios -> por eso
  // la tabla de Member Management ni siquiera pide ese dato si no soy admin.
  // Dependencia [user.is_admin]: si el rol cambiara en la misma sesión, este
  // efecto se vuelve a ejecutar.
  useEffect(() => {
    fetch(`${API_URL}/profile/`, { credentials: 'include' })
      .then(r => r.json())
      .then(data => {
        setProfile(data);
        setForm({
          display_name: data.display_name || '',
          email: data.email || '',
          password: '',                              // nunca se precarga la password actual
          status: data.status || 'offline',
          profile_picture: data.profile_picture || '',
        });
        setLoading(false);
      })
      .catch(() => setLoading(false));

    if (user.is_admin) {
      fetch(`${API_URL}/admin/users/`, { credentials: 'include' })
        .then(r => r.json())
        .then(setAllUsers)
        .catch(() => {});
    }
  }, [user.is_admin]);

  const handlePictureChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    // Límite manual de 2MB: como la foto se guarda como base64 en la base de
    // datos (no como archivo aparte), una imagen grande infla cada fila de
    // /admin/users/ para todos. Esta validación es la única defensa que hay.
    if (file.size > 2 * 1024 * 1024) {
      toast.error('Image must be under 2MB.');
      return;
    }
    // FileReader = API del navegador que convierte el archivo a base64 EN EL
    // CLIENTE. El preview aparece al instante; nada se sube al backend todavía,
    // eso pasa recién al hacer click en "Save Changes".
    const reader = new FileReader();
    reader.onload = (ev) => setForm(f => ({ ...f, profile_picture: ev.target.result }));
    reader.readAsDataURL(file);
  };

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const res = await fetch(`${API_URL}/profile/`, {
        method: 'PATCH',
        credentials: 'include',
        // X-CSRFToken: requerido por Django para cualquier request que no sea GET.
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({
          display_name: form.display_name,
          email: form.email,
          status: form.status,
          profile_picture: form.profile_picture,
          // Solo se manda "password" si el usuario escribió algo en ese campo;
          // así el backend nunca confunde "no cambiar" con "vaciar la password".
          ...(form.password ? { password: form.password } : {}),
        }),
      });
      const data = await res.json();
      if (!res.ok) { toast.error(data.error || 'Failed to save.'); return; }
      setProfile(data);
      // setUser "levanta" el cambio hasta App.js: así el Sidebar (otro
      // componente) refleja el nuevo nombre/foto sin recargar la página.
      setUser(u => ({ ...u, email: data.email, username: data.username, display_name: data.display_name, profile_picture: data.profile_picture }));
      setForm(f => ({ ...f, password: '' }));  // limpia el campo, nunca se vuelve a mostrar el valor guardado
      toast.success('Profile updated!');
    } finally {
      setSaving(false);
    }
  };

  // Abre el modal precargando el form con los datos ACTUALES de esa fila.
  const openAdminEdit = (u) => {
    setEditingUser(u);
    setAdminForm({ display_name: u.display_name, email: u.email, password: '', is_admin: u.is_admin, is_active: u.is_active });
  };

  const handleAdminSave = async () => {
    setSaving(true);
    try {
      // Mismo patrón que handleSaveProfile, pero apuntando al id del usuario
      // que se está editando (editingUser.id), no a "mí mismo".
      const res = await fetch(`${API_URL}/admin/users/${editingUser.id}/`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrf() },
        body: JSON.stringify({
          display_name: adminForm.display_name,
          email: adminForm.email,
          is_admin: adminForm.is_admin,    // solo este formulario (admin sobre otro) manda este campo
          is_active: adminForm.is_active,
          ...(adminForm.password ? { password: adminForm.password } : {}),
        }),
      });
      const data = await res.json();
      if (!res.ok) { toast.error(data.error || 'Failed to save.'); return; }
      // Actualización optimista local: en vez de volver a pedir TODA la lista
      // de usuarios al backend, se reemplaza solo la fila editada (comparando
      // por id) dentro del array que ya estaba en memoria. Evita un refetch
      // completo y el parpadeo de toda la tabla.
      setAllUsers(users => users.map(u => u.id === data.id ? data : u));
      setEditingUser(null);   // cierra el modal
      toast.success('User updated!');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="profile-loading">Loading profile...</div>;

  const avatarSrc = form.profile_picture;
  const initials = (form.display_name || form.email || 'U')[0].toUpperCase();

  return (
    <div className="dashboard">
      <Sidebar user={user} active="profile" onLogout={onLogout} onNavigate={onNavigate} />

      <main className="main-content">
        <header className="main-header">
          <div>
            <h1>Profile</h1>
            <p className="header-sub">Manage your account details</p>
          </div>
        </header>

        {/* ── Own profile card ── */}
        {/* Siempre visible (a diferencia de Member Management, que es solo-admin). */}
        <section className="profile-section">
          <h2 className="section-title">My Profile</h2>
          <div className="profile-card">

            {/* Avatar: botón "Change Photo" dispara el click del <input type="file">
                oculto vía fileInputRef; ver handlePictureChange más arriba. */}
            <div className="avatar-area">
              {avatarSrc
                ? <img src={avatarSrc} alt="profile" className="profile-avatar-img" />
                : <div className="profile-avatar-placeholder">{initials}</div>
              }
              <button className="change-pic-btn" onClick={() => fileInputRef.current.click()}>
                Change Photo
              </button>
              <input ref={fileInputRef} type="file" accept="image/*" style={{ display: 'none' }} onChange={handlePictureChange} />
            </div>

            {/* Fields */}
            <div className="profile-fields">
              {profile && (
                <div className="profile-field readonly">
                  <label>User ID</label>
                  <span className="field-value muted">#{profile.id}</span>
                </div>
              )}

              <div className="profile-field">
                <label>Display Name</label>
                <input
                  type="text"
                  value={form.display_name}
                  onChange={e => setForm(f => ({ ...f, display_name: e.target.value }))}
                  placeholder="Your display name"
                />
              </div>

              <div className="profile-field">
                <label>Email</label>
                <input
                  type="email"
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  placeholder="your@email.com"
                />
              </div>

              <div className="profile-field">
                <label>New Password</label>
                <input
                  type="password"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  placeholder="Leave blank to keep current"
                />
              </div>

              <div className="profile-field">
                <label>Status</label>
                <div className="status-toggle">
                  <button
                    className={`status-btn ${form.status === 'online' ? 'active-online' : ''}`}
                    onClick={() => setForm(f => ({ ...f, status: 'online' }))}
                  >
                    <span className="status-dot online" /> Online
                  </button>
                  <button
                    className={`status-btn ${form.status === 'offline' ? 'active-offline' : ''}`}
                    onClick={() => setForm(f => ({ ...f, status: 'offline' }))}
                  >
                    <span className="status-dot offline" /> Offline
                  </button>
                </div>
              </div>

              <button className="save-btn" onClick={handleSaveProfile} disabled={saving}>
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </section>

        {/* ── Admin: all users ── */}
        {/* Toda la sección desaparece del DOM (no es solo CSS) si no soy admin.
            allUsers llega del segundo fetch del useEffect, condicionado igual. */}
        {user.is_admin && (
          <section className="profile-section">
            <h2 className="section-title">Member Management</h2>
            <div className="users-table-wrap">
              <table className="users-table">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Avatar</th>
                    <th>Name</th>
                    <th>Email</th>
                    <th>Role</th>
                    <th>Status</th>
                    <th>Active</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {allUsers.map(u => (
                    <tr key={u.id}>
                      <td className="muted">#{u.id}</td>
                      <td>
                        {u.profile_picture
                          ? <img src={u.profile_picture} alt="" className="table-avatar-img" />
                          : <div className="table-avatar">{(u.display_name || u.email)[0].toUpperCase()}</div>
                        }
                      </td>
                      <td>{u.display_name || u.username}</td>
                      <td>{u.email}</td>
                      <td>
                        <span className={`role-badge ${u.is_admin ? 'admin' : 'member'}`}>
                          {u.is_admin ? 'Admin' : 'Member'}
                        </span>
                      </td>
                      <td>
                        <span className={`status-indicator ${u.status}`}>
                          <span className={`status-dot ${u.status}`} /> {u.status}
                        </span>
                      </td>
                      <td>
                        <span className={`active-badge ${u.is_active ? 'yes' : 'no'}`}>
                          {u.is_active ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td>
                        <button className="edit-user-btn" onClick={() => openAdminEdit(u)}>Edit</button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        {/* ── Admin edit modal ── */}
        {/* Solo se monta si editingUser !== null (ver openAdminEdit). Click en el
            overlay cierra el modal; stopPropagation en modal-box evita que un
            click DENTRO de la caja se propague al overlay y lo cierre solo. */}
        {editingUser && (
          <div className="modal-overlay" onClick={() => setEditingUser(null)}>
            <div className="modal-box" onClick={e => e.stopPropagation()}>
              <h3>Edit User — #{editingUser.id}</h3>

              <div className="modal-field">
                <label>Display Name</label>
                <input
                  type="text"
                  value={adminForm.display_name}
                  onChange={e => setAdminForm(f => ({ ...f, display_name: e.target.value }))}
                />
              </div>

              <div className="modal-field">
                <label>Email</label>
                <input
                  type="email"
                  value={adminForm.email}
                  onChange={e => setAdminForm(f => ({ ...f, email: e.target.value }))}
                />
              </div>

              <div className="modal-field">
                <label>New Password</label>
                <input
                  type="password"
                  value={adminForm.password}
                  onChange={e => setAdminForm(f => ({ ...f, password: e.target.value }))}
                  placeholder="Leave blank to keep current"
                />
              </div>

              {/* Estos 2 checkboxes son los únicos campos que NO existen en "My
                  Profile": is_admin (togglea is_staff+is_superuser juntos en
                  el backend) e is_active (soft-delete: desactiva sin borrar). */}
              <div className="modal-field checkboxes">
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={adminForm.is_admin}
                    onChange={e => setAdminForm(f => ({ ...f, is_admin: e.target.checked }))}
                  />
                  Admin role
                </label>
                <label className="checkbox-label">
                  <input
                    type="checkbox"
                    checked={adminForm.is_active}
                    onChange={e => setAdminForm(f => ({ ...f, is_active: e.target.checked }))}
                  />
                  Account active
                </label>
              </div>

              <div className="modal-actions">
                <button className="cancel-btn" onClick={() => setEditingUser(null)}>Cancel</button>
                <button className="save-btn" onClick={handleAdminSave} disabled={saving}>
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// Lee el valor de la cookie "csrftoken" que Django deja en el navegador.
// Hace falta mandarlo a mano en el header X-CSRFToken porque estos PATCH no
// se envían como un <form> HTML tradicional, sino vía fetch + JSON.
function getCsrf() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? match[1] : '';
}

export default ProfilePage;
