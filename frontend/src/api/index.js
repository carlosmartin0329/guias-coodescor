import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const data = error.response?.data || { error: 'Error de conexión' };
    return Promise.reject(data);
  }
);

export default api;
