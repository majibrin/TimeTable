import React, { useState, useEffect } from 'react';
import API from '../api/client';

const ROLES = ['SUPER_ADMIN', 'TIMETABLE_OFFICER', 'LECTURER', 'STUDENT'];

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

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  const filteredUsers = filterRole
    ? users.filter(u => u.role === filterRole)
    : users;

  return (
    <div className="min-h-screen bg-slate-50 font-mono">
      <div className="bg-white border-b border-slate-200 px-4 py-3 flex justify-between items-center">
        <div>
          <h1 className="text-sm font-bold text-slate-900">SUPER ADMIN</h1>
          <p className="text-[10px] text-slate-400">User Management — GSU Timetable System</p>
        </div>
        <button onClick={handleLogout}
          className="px-3 py-1.5 border border-red-200 text-red-600 rounded text-xs font-bold">
          LOGOUT
        </button>
      </div>

      <div className="p-4 max-w-3xl mx-auto">
        {error && <div className="bg-red-50 text-red-700 text-xs p-3 rounded mb-4 border border-red-200">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 text-xs p-3 rounded mb-4 border border-green-200">{success}</div>}

        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6 shadow-sm">
          <h2 className="text-xs font-bold text-slate-700 mb-3 uppercase tracking-wider">Create User</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
            {[
              ['username', 'Username', 'text'],
              ['email', 'Email', 'email'],
              ['first_name', 'First Name', 'text'],
              ['last_name', 'Last Name', 'text'],
              ['password', 'Password', 'password'],
            ].map(([field, label, type]) => (
              <div key={field}>
                <label className="block text-[10px] text-slate-500 mb-1 uppercase">{label}</label>
                <input
                  type={type}
                  value={form[field]}
                  onChange={e => setForm({...form, [field]: e.target.value})}
                  required
                  className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
                />
              </div>
            ))}

            <div>
              <label className="block text-[10px] text-slate-500 mb-1 uppercase">Role</label>
              <select
                value={form.role}
                onChange={e => setForm({...form, role: e.target.value, department: ''})}
                className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
              >
                {ROLES.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
              </select>
            </div>

            {(form.role === 'LECTURER' || form.role === 'STUDENT') && (
              <div className="col-span-2">
                <label className="block text-[10px] text-slate-500 mb-1 uppercase">
                  Department {form.role === 'LECTURER' ? '(required for lecturer)' : '(optional)'}
                </label>
                <select
                  value={form.department}
                  onChange={e => setForm({...form, department: e.target.value})}
                  className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
                >
                  <option value="">-- Select Department --</option>
                  {departments.map(d => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
            )}

            <div className="col-span-2">
              <button type="submit"
                className="w-full py-2 bg-slate-900 text-white text-xs font-bold rounded hover:bg-slate-700">
                CREATE USER
              </button>
            </div>
          </form>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
          <div className="p-3 border-b border-slate-100 flex justify-between items-center">
            <h2 className="text-xs font-bold text-slate-700 uppercase">Users ({filteredUsers.length})</h2>
            <select
              value={filterRole}
              onChange={e => setFilterRole(e.target.value)}
              className="px-2 py-1 text-[10px] border border-slate-200 rounded focus:outline-none">
              <option value="">All Roles</option>
              {ROLES.map(r => <option key={r} value={r}>{r.replace('_', ' ')}</option>)}
            </select>
          </div>

          {loading ? (
            <div className="p-8 text-center text-xs text-slate-400">Loading...</div>
          ) : (
            <div className="divide-y divide-slate-100">
              {filteredUsers.map(u => (
                <div key={u.id} className="flex items-center justify-between p-3">
                  <div>
                    <div className="text-xs font-bold text-slate-800">{u.username}</div>
                    <div className="text-[10px] text-slate-400">
                      {u.first_name} {u.last_name}
                      {u.email ? ` · ${u.email}` : ''}
                    </div>
                    <div className="flex gap-2 mt-0.5">
                      <span className="text-[10px] text-blue-600 font-bold">{u.role.replace('_', ' ')}</span>
                      {u.department_name && (
                        <span className="text-[10px] text-slate-400">· {u.department_name}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => handleToggleActive(u.id, u.is_active)}
                    className={`px-2 py-1 text-[10px] font-bold rounded ${
                      u.is_active
                        ? 'bg-red-50 text-red-600 border border-red-200'
                        : 'bg-green-50 text-green-600 border border-green-200'
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
  );
}
