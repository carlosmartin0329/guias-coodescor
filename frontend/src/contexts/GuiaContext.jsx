import { createContext, useContext, useState, useCallback } from 'react';
import * as guiasApi from '../api/guias';

const GuiaContext = createContext(null);

export function GuiaProvider({ children }) {
  const [guias, setGuias] = useState([]);
  const [conteo, setConteo] = useState([]);
  const [estados, setEstados] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);

  const cargarConteo = useCallback(async () => {
    setCargando(true);
    setError(null);
    try {
      const data = await guiasApi.guiasConteo();
      setConteo(data.conteo || []);
    } catch (err) {
      setError(err.error);
    } finally {
      setCargando(false);
    }
  }, []);

  const cargarEstados = useCallback(async () => {
    try {
      const data = await guiasApi.guiasEstados();
      setEstados(data.estados || []);
    } catch (err) {
      setError(err.error);
    }
  }, []);

  const listarGuias = useCallback(async (params = {}) => {
    setCargando(true);
    setError(null);
    try {
      const data = await guiasApi.guiasListar(params);
      setGuias(data.guias || []);
      return data;
    } catch (err) {
      setError(err.error);
      return { guias: [], total: 0, conteo_por_estado: [] };
    } finally {
      setCargando(false);
    }
  }, []);

  return (
    <GuiaContext.Provider value={{ guias, conteo, estados, cargando, error, listarGuias, cargarConteo, cargarEstados }}>
      {children}
    </GuiaContext.Provider>
  );
}

export function useGuias() {
  const context = useContext(GuiaContext);
  if (!context) throw new Error('useGuias debe usarse dentro de GuiaProvider');
  return context;
}
