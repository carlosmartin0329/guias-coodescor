import api from './index';

export const captchaNuevo = () => api.post('/captcha/nuevo');
export const login = (credenciales) => api.post('/login', credenciales);
export const logout = () => api.post('/logout');
// Sesión actual: permite restaurar el usuario tras recargar o entrar por enlace
// directo. Antes apuntaba a /usuarios/rol/transportador, que no es un perfil.
export const session = () => api.get('/session');
