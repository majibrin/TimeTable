import axios from 'axios';

const PUBLIC_ENDPOINTS = ['auth/login/', 'register/'];

const API = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000/',
  headers: { 'Content-Type': 'application/json' },
});

API.interceptors.request.use((config) => {
  const url = config.url || '';
  const isPublicEndpoint = PUBLIC_ENDPOINTS.some(endpoint => url.includes(endpoint));
  const token = localStorage.getItem('token');

  if (config.headers) {
    delete config.headers.Authorization;
  }

  if (token && !isPublicEndpoint) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

export default API;
