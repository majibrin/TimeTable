import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import API from '../api/client';

export default function Signup() {
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({ username: '', password: '', department: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    API.get('departments/').then(res => setDepartments(res.data)).catch(() => setError('Failed to load departments'));
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSubmitting(true);
    try {
      await API.post('register/', form);
      navigate('/login', { state: { message: 'Account created. Please sign in.' } });
    } catch (err) {
      const details = err.response?.data || {};
      setError(details.username?.[0] || details.password?.[0] || details.department?.[0] || 'Registration failed');
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 p-4">
      <form onSubmit={handleSubmit} className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-8 shadow-md">
        <h1 className="mb-6 text-center text-2xl font-bold tracking-wider text-slate-800">STUDENT SIGNUP</h1>
        {error && <div className="mb-4 rounded border-l-4 border-red-600 bg-red-50 p-3 text-sm text-red-700">{error}</div>}
        <div className="space-y-4">
          <input value={form.username} onChange={e => setForm({...form, username: e.target.value})} required minLength={3}
            className="w-full rounded border border-slate-300 bg-slate-50 px-3 py-2 text-sm" placeholder="Username" />
          <input type="password" value={form.password} onChange={e => setForm({...form, password: e.target.value})} required minLength={8}
            className="w-full rounded border border-slate-300 bg-slate-50 px-3 py-2 text-sm" placeholder="Password (8 characters minimum)" />
          <select value={form.department} onChange={e => setForm({...form, department: e.target.value})} required
            className="w-full rounded border border-slate-300 bg-slate-50 px-3 py-2 text-sm">
            <option value="">Select department</option>
            {departments.map(department => <option key={department.id} value={department.id}>{department.name}</option>)}
          </select>
          <button type="submit" disabled={submitting} className="w-full rounded bg-blue-600 py-3 text-sm font-bold tracking-widest text-white disabled:opacity-50">
            {submitting ? 'CREATING ACCOUNT...' : 'CREATE ACCOUNT'}
          </button>
        </div>
        <p className="mt-5 text-center text-xs text-slate-500"><Link to="/login" className="font-bold text-blue-600">BACK TO LOGIN</Link></p>
      </form>
    </div>
  );
}
