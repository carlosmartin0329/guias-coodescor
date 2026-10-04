import api from './index';

export const guiasListar = (params = {}) => api.get('/guias', { params });
export const guiasConteo = () => api.get('/guias/conteo');
export const guiasEstados = () => api.get('/guias/estados');
export const guiasDetalle = (id) => api.get(`/guias/${id}`);
export const guiasEventos = (id, params = {}) => api.get(`/guias/${id}/eventos`, { params });
export const guiasTransicion = (id, tipo) => api.get(`/guias/${id}/transicion/${tipo}`);
export const guiasCrear = (datos) => api.post('/guias', datos);
export const guiasEditar = (id, datos) => api.put(`/guias/${id}`, datos);
export const guiasEvento = (id, tipo, datos) => api.post(`/guias/${id}/evento/${tipo}`, datos);
export const exportarGuias = (params = {}) => api.get('/exportar.csv', { params, responseType: 'blob' });
export const loadtestCSV = () => api.get('/loadtest/ultimo.csv', { responseType: 'blob' });
export const loadtestXLSX = () => api.get('/loadtest/ultimo.xlsx', { responseType: 'blob' });
export const loadtestAdmin = () => api.get('/loadtest/ultimo');
