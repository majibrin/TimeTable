import API from '../api/client';

export const checkSession = async (setUser, setLoading) => {
  const token = localStorage.getItem('token');
  if (!token) { setLoading(false); return; }
  try {
    const res = await API.get('');
    setUser({ username: res.data.username, role: res.data.role });
  } catch {
    localStorage.removeItem('token');
  } finally {
    setLoading(false);
  }
};

export const loginUser = async (username, password, setUser) => {
  try {
    const res = await API.post('auth/login/', { username, password });
    localStorage.setItem('token', res.data.access);
    setUser({ username: res.data.username, role: res.data.role });
    return { success: true, role: res.data.role };
  } catch (err) {
    return { success: false, error: err.response?.data?.error || 'Login failed' };
  }
};
