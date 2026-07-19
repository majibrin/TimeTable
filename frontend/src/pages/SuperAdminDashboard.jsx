import React, { useState, useEffect } from 'react';
import API from '../api/client';

const ROLES = ['SUPER_ADMIN', 'TIMETABLE_OFFICER', 'LECTURER', 'STUDENT'];

export default function SuperAdminDashboard() {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState({ username: '', email: '', first_name: '', last_name: '', role: 'STUDENT', password: '' });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const fetchUsers = async () => {
    try {
      const res = await API.get('users/');
      setUsers(res.data);
    } catch (e) {
      setError('Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    setError(''); setSuccess('');
    try {
      await API.post('users/', form);
      setSuccess('User created successfully');
      setForm({ username: '', email: '', first_name: '', last_name: '', role: 'STUDENT', password: '' });
      fetchUsers();
    } catch (e) {
      setError(e.response?.data?.username?.[0] || e.response?.data?.email?.[0] || 'Failed to create user');
    }
  };

  const handleDeactivate = async (id, is_active) => {
    try {
      await API.patch(`users/${id}/`, { is_active: !is_active });
      fetchUsers();
    } catch (e) {
      setError('Failed to update user');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  };

  return (
    <div className="min-h-screen bg-slate-50 font-mono p-4">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center bg-white border border-slate-200 rounded-lg p-4 mb-6 shadow-sm">
          <div>
            <h1 className="text-sm font-bold text-slate-900 tracking-tight">SUPER ADMIN</h1>
            <p className="text-xs text-slate-400">User Management</p>
          </div>
          <button onClick={handleLogout} className="px-3 py-1.5 border border-red-200 text-red-600 rounded text-xs font-bold">LOGOUT</button>
        </div>

        {error && <div className="bg-red-50 text-red-700 text-xs p-3 rounded mb-4 border border-red-200">{error}</div>}
        {success && <div className="bg-green-50 text-green-700 text-xs p-3 rounded mb-4 border border-green-200">{success}</div>}

        <div className="bg-white border border-slate-200 rounded-lg p-4 mb-6 shadow-sm">
          <h2 className="text-xs font-bold text-slate-700 mb-3 uppercase tracking-wider">Create User</h2>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
            {[['username','Username'],['email','Email'],['first_name','First Name'],['last_name','Last Name'],['password','Password']].map(([field, label]) => (
              <div key={field}>
                <label className="block text-[10px] text-slate-500 mb-1 uppercase">{label}</label>
                <input
                  type={field === 'password' ? 'password' : 'text'}
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
                onChange={e => setForm({...form, role: e.target.value})}
                className="w-full px-2 py-1.5 text-xs border border-slate-200 rounded focus:outline-none focus:ring-1 focus:ring-slate-400"
              >
                {ROLES.map(r => <option key={r} value={r}>{r.replace('_',' ')}</option>)}
              </select>
            </div>
            <div className="col-span-2">
              <button type="submit" className="w-full py-2 bg-slate-900 text-white text-xs font-bold rounded hover:bg-slate-700">
                CREATE USER
              </button>
            </div>
          </form>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg shadow-sm">
          <div className="p-4 border-b border-slate-100">
            <h2 className="text-xs font-bold text-slate-700 uppercase tracking-wider">All Users ({users.length})</h2>
          </div>
          {loading ? (
            <div className="p-8 text-center text-xs text-slate-400">Loading...</div>
          ) : (
            <div className="divide-y divide-slate-100">
              {users.map(u => (
                <div key={u.id} className="flex items-center justify-between p-3">
                  <div>
                    <div className="text-xs font-bold text-slate-800">{u.username}</div>
                    <div className="text-[10px] text-slate-400">{u.first_name} {u.last_name} · {u.email}</div>
                    <div className="text-[10px] text-blue-600 font-bold">{u.role.replace('_',' ')}</div>
                  </div>
                  <button
                    onClick={() => handleDeactivate(u.id, u.is_active)}
                    className={`px-2 py-1 text-[10px] font-bold rounded ${u.is_active ? 'bg-red-50 text-red-600 border border-red-200' : 'bg-green-50 text-green-600 border border-green-200'}`}
                  >
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
