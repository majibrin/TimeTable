import React, { useState, useEffect } from 'react';
import API from '../api/client';

const ROLES = ['SUPER_ADMIN', 'TIMETABLE_OFFICER', 'DEPARTMENT', 'STUDENT'];

export default function SuperAdminDashboard() {
  const [users, setUsers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({
    username: '', email: '', first_name: '', last_name: '',
    role: 'STUDENT', password: '', department: ''
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [filterRole, setFilterRole] = useState('');
  const [editingUser, setEditingUser] = useState(null);

  const fetchAll = async () => {
    try {
      const [usersRes, deptsRes] = await Promise.all([
        API.get('users/'),
        API.get('departments/'),
      ]);
      setUsers(usersRes.data);
      setDepartments(deptsRes.data);
    } catch (e) {
      setError('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchAll(); }, []);

  const msg = (ok, text) => {
    if (ok) setSuccess(text); else setError(text);
    setTimeout(() => { setSuccess(''); setError(''); }, 4000);
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');

    if (form.role === 'DEPARTMENT' && !form.department) {
      msg(false, 'Department is required for a Department-role account');
      return;
    }

    try {
      const payload = {
        username: form.username,
        email: form.email,
        first_name: form.first_name,
        last_name: form.last_name,
        role: form.role,
        password: form.password,
      };
      if (form.department) payload.department = parseInt(form.department);
      await API.post('users/', payload);
      msg(true, 'User created successfully');
      setForm({ username: '', email: '', first_name: '', last_name: '', role: 'STUDENT', password: '', department: '' });
      fetchAll();
    } catch (e) {
      msg(false, e.response?.data?.username?.[0] || e.response?.data?.email?.[0] || 'Failed to create user');
    }
  };

  const handleToggleActive = async (id, is_active) => {
    try {
      await API.patch(`users/${id}/`, { is_active: !is_active });
      fetchAll();
    } catch (e) {
      msg(false, 'Failed to update user');
    }
  };

  const handleEdit = async (e) => {
    e.preventDefault();
    try {
      await API.patch(`users/${editingUser.id}/`, {
        username: editingUser.username,
        role: editingUser.role,
        department: editingUser.department || null,
      });
      msg(true, 'User updated successfully');
      setEditingUser(null);
      fetchAll();
    } catch (e) {
      msg(false, e.response?.data?.username?.[0] || 'Failed to update user');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  const filteredUsers = filterRole
    ? users.filter(u => u.role === filterRole)
    : users;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-white border-b border-slate-200/60 px-4 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
          <div>
            <h1 className="text-sm font-bold text-slate-900">SUPER ADMIN</h1>
            <p className="text-[10px] sm:text-xs text-slate-400">User Management — GSU Timetable System</p>
          </div>
          <button onClick={handleLogout}
            className="px-3 py-1.5 text-[10px] sm:text-xs font-bold border border-red-300 hover:bg-red-50 text-red-600 rounded transition-colors">
            LOGOUT
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4 md:py-6">
        {error && <div className="bg-red-50 text-red-700 text-xs p-3 rounded mb-4 border border-red-200">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 text-xs p-3 rounded mb-4 border border-green-200">{success}</div>}

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* Form Column - Left */}
          <div className="lg:col-span-2">
            <div className="bg-white border border-slate-200/60 rounded-lg p-5 shadow-sm sticky top-[200px]">
              <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-4">Create User</h2>
              <form onSubmit={handleCreate} className="space-y-3">
                {[
                  ['username', 'Username', 'text'],
                  ['email', 'Email', 'email'],
                  ['first_name', 'First Name', 'text'],
                  ['last_name', 'Last Name', 'text'],
                  ['password', 'Password', 'password'],
                ].map(([field, label, type]) => (
                  <div key={field}>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">{label}</label>
                    <input
                      type={type}
                      value={form[field]}
                      onChange={e => setForm({...form, [field]: e.target.value})}
                      required
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 transition-all font-medium"
                    />
                  </div>
                ))}

                <div>
                  <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">Role</label>
                  <select
                    value={form.role}
                    onChange={e => setForm({...form, role: e.target.value, department: ''})}
                    className="w-full px-3 py-2 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 transition-all font-bold"
                  >
                    {ROLES.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                  </select>
                </div>

                {(form.role === 'STUDENT' || form.role === 'DEPARTMENT') && (
                  <div>
                    <label className="block text-[10px] font-bold text-slate-600 uppercase tracking-wider mb-1">
                      Department {form.role === 'DEPARTMENT' ? '(required)' : '(optional)'}
                    </label>
                    <select
                      value={form.department}
                      onChange={e => setForm({...form, department: e.target.value})}
                      required={form.role === 'DEPARTMENT'}
                      className="w-full px-3 py-2 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 transition-all font-bold"
                    >
                      <option value="">-- Select Department --</option>
                      {departments.map(d => (
                        <option key={d.id} value={d.id}>{d.name}</option>
                      ))}
                    </select>
                  </div>
                )}

                <button type="submit"
                  className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-black rounded transition-colors shadow-sm">
                  CREATE USER
                </button>
              </form>
            </div>
          </div>

          {/* List Column - Right */}
          <div className="lg:col-span-3">
            <div className="bg-white border border-slate-200/60 rounded-lg shadow-sm">
              <div className="p-4 border-b border-slate-100 flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">Users ({filteredUsers.length})</h2>
                <select
                  value={filterRole}
                  onChange={e => setFilterRole(e.target.value)}
                  className="px-3 py-1.5 text-[10px] font-bold border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-blue-600/20 focus:border-blue-600 bg-slate-50/50 transition-all">
                  <option value="">All Roles</option>
                  {ROLES.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
                </select>
              </div>

              {loading ? (
                <div className="p-8 text-center text-xs text-slate-400">Loading...</div>
              ) : filteredUsers.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">No users found</div>
              ) : (
                <div className="divide-y divide-slate-100 max-h-[600px] overflow-y-auto">
                  {filteredUsers.map(u => (
                    <div key={u.id} className="flex flex-wrap items-center justify-between gap-2 p-4 hover:bg-slate-50/50 transition-colors">
                      <div>
                        <div className="text-xs font-bold text-slate-800">{u.username}</div>
                        <div className="text-[10px] text-slate-500">
                          {u.first_name} {u.last_name}
                          {u.email ? ` · ${u.email}` : ''}
                        </div>
                        <div className="flex flex-wrap gap-2 mt-0.5">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            u.role === 'SUPER_ADMIN' ? 'bg-purple-50 text-purple-600' :
                            u.role === 'TIMETABLE_OFFICER' ? 'bg-blue-50 text-blue-600' :
                            u.role === 'DEPARTMENT' ? 'bg-amber-50 text-amber-600' :
                            'bg-green-50 text-green-600'
                          }`}>
                            {u.role.replace('_', ' ')}
                          </span>
                          {u.department_name && (
                            <span className="text-[10px] text-slate-400">· {u.department_name}</span>
                          )}
                        </div>
                      </div>
                      <button
                        onClick={() => setEditingUser({ id: u.id, username: u.username, role: u.role, department: u.department || '' })}
                        className="px-3 py-1.5 text-[10px] font-bold rounded border border-blue-200 bg-blue-50 text-blue-600 hover:bg-blue-100 transition-colors">
                        EDIT
                      </button>
                      <button
                        onClick={() => handleToggleActive(u.id, u.is_active)}
                        className={`px-3 py-1.5 text-[10px] font-bold rounded transition-colors ${
                          u.is_active
                            ? 'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100'
                            : 'bg-green-50 text-green-600 border border-green-200 hover:bg-green-100'
                        }`}>
                        {u.is_active ? 'DEACTIVATE' : 'ACTIVATE'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
      {editingUser && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-950/60 p-4">
          <form onSubmit={handleEdit} className="w-full max-w-md rounded-lg bg-white p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-sm font-bold text-slate-800">Edit User</h2>
              <button type="button" onClick={() => setEditingUser(null)} className="text-slate-500">CLOSE</button>
            </div>
            <div className="space-y-3">
              <input value={editingUser.username} onChange={e => setEditingUser({...editingUser, username: e.target.value})} required
                className="w-full rounded border border-slate-200 px-3 py-2 text-xs" placeholder="Username" />
              <select value={editingUser.role} onChange={e => setEditingUser({...editingUser, role: e.target.value})}
                className="w-full rounded border border-slate-200 px-3 py-2 text-xs">
                {ROLES.map(role => <option key={role} value={role}>{role.replace('_', ' ')}</option>)}
              </select>
              <select value={editingUser.department || ''} onChange={e => setEditingUser({...editingUser, department: e.target.value})}
                className="w-full rounded border border-slate-200 px-3 py-2 text-xs">
                <option value="">No department</option>
                {departments.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}
              </select>
            </div>
            <div className="mt-5 flex justify-end gap-2">
              <button type="button" onClick={() => setEditingUser(null)} className="rounded border border-slate-200 px-3 py-2 text-[10px] font-bold">CANCEL</button>
              <button type="submit" className="rounded bg-blue-600 px-3 py-2 text-[10px] font-bold text-white">SAVE CHANGES</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}