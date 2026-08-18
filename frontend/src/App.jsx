import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { checkSession } from './context/AuthActions';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import OfficerDashboard from './pages/OfficerDashboard';
import SuperAdminDashboard from './pages/SuperAdminDashboard';
import DepartmentDashboard from './pages/DepartmentDashboard';
import StudentDashboard from './pages/StudentDashboard';

const RoleRouter = () => {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (user.role === 'SUPER_ADMIN') return <Navigate to="/superadmin" replace />;
  if (user.role === 'TIMETABLE_OFFICER') return <Navigate to="/officer" replace />;
  if (user.role === 'DEPARTMENT') return <Navigate to="/department" replace />;
  if (user.role === 'STUDENT') return <Navigate to="/student" replace />;
  return <Navigate to="/login" replace />;
};

const AppRoutes = () => {
  const { setUser, setLoading } = useAuth();
  useEffect(() => { checkSession(setUser, setLoading); }, []);

  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<ProtectedRoute><RoleRouter /></ProtectedRoute>} />
      <Route path="/superadmin" element={<ProtectedRoute allowedRoles={['SUPER_ADMIN']}><SuperAdminDashboard /></ProtectedRoute>} />
      <Route path="/officer" element={<ProtectedRoute allowedRoles={['TIMETABLE_OFFICER','SUPER_ADMIN']}><OfficerDashboard /></ProtectedRoute>} />
      <Route path="/department" element={<ProtectedRoute allowedRoles={['DEPARTMENT']}><DepartmentDashboard /></ProtectedRoute>} />
      <Route path="/student" element={<ProtectedRoute allowedRoles={['STUDENT']}><StudentDashboard /></ProtectedRoute>} />
      <Route path="*" element={<ProtectedRoute><RoleRouter /></ProtectedRoute>} />
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
