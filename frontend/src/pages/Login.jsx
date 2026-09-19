import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { loginUser } from '../context/AuthActions';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSubmitting(true);

    const result = await loginUser(username, password, setUser);

    if (result.success) {
      navigate('/');
    } else {
      setError(result.error);
      setSubmitting(false);
    }
  };

  return (
    <div className="flex justify-center items-center min-h-screen bg-slate-50 font-sans p-4">
      <div className="bg-white p-8 rounded-lg shadow-md w-full max-w-md border border-slate-200">
        <h2 className="text-center text-2xl font-bold text-slate-800 tracking-wider mb-6">SYSTEM GATEWAY</h2>
        
        {error && (
          <div className="bg-red-50 text-red-700 text-sm p-3 rounded-md mb-4 border-l-4 border-red-600">
            {error}
          </div>
        )}
        {location.state?.message && <div className="mb-4 rounded border-l-4 border-green-600 bg-green-50 p-3 text-sm text-green-700">{location.state.message}</div>}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Username</label>
            <input 
              type="text" 
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-slate-800 focus:bg-white transition-all"
            />
          </div>

          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">Password</label>
            <input 
              type="password" 
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-3 py-2 bg-slate-50 border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-slate-800 focus:bg-white transition-all"
            />
          </div>

          <button 
            type="submit" 
            disabled={submitting}
            className="w-full py-3 bg-blue-600 hover:bg-blue-700 text-white rounded font-bold tracking-widest text-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {submitting ? 'AUTHENTICATING...' : 'ENTER SYSTEM'}
          </button>
        </form>
        <p className="mt-5 text-center text-xs text-slate-500">New student? <Link to="/signup" className="font-bold text-blue-600">CREATE AN ACCOUNT</Link></p>
      </div>
    </div>
  );
}