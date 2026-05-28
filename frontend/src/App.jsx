import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { checkSession } from './context/AuthActions';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';

const AdminView = () => <div className="p-5 font-mono"><h3>Admin Optimization Console</h3></div>;

const AppRoutes = () => {
  const { setUser, setLoading } = useAuth();

  useEffect(() => {
    checkSession(setUser, setLoading);
  }, [setUser, setLoading]);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
      <Route path="/admin/generate" element={<ProtectedRoute allowedRoles={['ADMIN']}><AdminView /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
};

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
