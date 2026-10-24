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
    // Sesión expirada: volver al login. Antes el interceptor solo rechazaba y
    // la UI mostraba "Error interno" sin regresar a la pantalla de acceso.
    const url = String(error.config?.url || '');
    // Si ya estamos en /login (o la petición ES el login), redirigir otra vez
    // produce un bucle de recargas: la consulta de sesión sin cookie responde
    // 401 y el navegador vuelve a cargar /login indefinidamente.
    const yaEnLogin = window.location.pathname.startsWith('/login');
    if (error.response?.status === 401 && !url.includes('/login') && !yaEnLogin) {
      window.location.assign('/login');
    }
    return Promise.reject(data);
  }
);

export default api;
