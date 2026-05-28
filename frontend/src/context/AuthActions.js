export const checkSession = async (setUser, setLoading) => {
  const token = localStorage.getItem('token');
  if (!token) {
    setLoading(false);
    return;
  }
  // Restore simulation session instantly on refresh
  setUser({ username: 'Admin', role: 'ADMIN' });
  setLoading(false);
};

export const loginUser = async (username, password, setUser) => {
  // Pure local operational pass-through—zero network blockers
  localStorage.setItem('token', 'simulated_timetable_token');
  setUser({ username, role: 'ADMIN' });
  return { success: true, role: 'ADMIN' };
};
