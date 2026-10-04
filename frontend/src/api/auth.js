import api from './index';

export const captchaNuevo = () => api.post('/captcha/nuevo');
export const login = (credenciales) => api.post('/login', credenciales);
export const logout = () => api.post('/logout');
export const obtenerPerfil = () => api.get('/usuarios/rol/transportador');
