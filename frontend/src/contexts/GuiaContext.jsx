import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import * as guiasApi from '../api/guias';
import { useSSESync } from '../hooks/useSSESync';

const GuiaContext = createContext(null);

export function GuiaProvider({ children }) {
  const [guias, setGuias] = useState([]);
  const [conteo, setConteo] = useState([]);
  const [estados, setEstados] = useState([]);
  const [cargando, setCargando] = useState(false);
  const [error, setError] = useState(null);
  const [ultimaActualizacion, setUltimaActualizacion] = useState(null);

  // --- Acciones para actualizar el estado local ---

  const updateGuia = useCallback((guiaId, updates) => {
    setGuias(prev => prev.map(g => 
      g.id === guiaId ? { ...g, ...updates } : g
    ));
  }, []);

  const addGuia = useCallback((guia) => {
    setGuias(prev => {
      // Evitar duplicados
      if (prev.some(g => g.id === guia.id)) {
        return prev;
      }
      return [guia, ...prev];
    });
  }, []);

  const updateConteo = useCallback((nuevoConteo) => {
    setConteo(nuevoConteo);
  }, []);

  // --- Manejadores de eventos SSE ---

  const handleNuevaGuia = useCallback((data) => {
    // Agregar la nueva guía a la lista
    addGuia({
      id: data.guia_id,
      consecutivo: data.consecutivo,
      cliente: data.cliente,
      estado: data.estado,
      creacion: data.creada_en,
      creacion_por: data.creada_por,
    });
    // Actualizar conteo si viene en el evento
    if (data.conteo_actualizado) {
      updateConteo(data.conteo_actualizado);
    }
    setUltimaActualizacion(new Date());
  }, [addGuia, updateConteo]);

  const handleEstadoActualizado = useCallback((data) => {
    // Actualizar el estado de la guía específica
    updateGuia(data.guia_id, {
      estado: data.nuevo_estado,
    });
    setUltimaActualizacion(new Date());
  }, [updateGuia]);

  const handleConteoActualizado = useCallback((data) => {
    updateConteo(data.conteo);
    setUltimaActualizacion(new Date());
  }, [updateConteo]);

  // --- Conexión SSE ---

  const { isConnected: sseConnected, error: sseError } = useSSESync({
    onNuevaGuia: handleNuevaGuia,
    onEstadoActualizado: handleEstadoActualizado,
    onConteoActualizado: handleConteoActualizado,
    enabled: true,
  });

  // --- Carga de datos ---

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

  // Cargar datos iniciales
  useEffect(() => {
    cargarConteo();
    cargarEstados();
  }, [cargarConteo, cargarEstados]);

  return (
    <GuiaContext.Provider value={{
      guias,
      conteo,
      estados,
      cargando,
      error,
      ultimaActualizacion,
      sseConnected,
      sseError,
      listarGuias,
      cargarConteo,
      cargarEstados,
      updateGuia,
      addGuia,
      updateConteo,
    }}>
      {children}
    </GuiaContext.Provider>
  );
}

export function useGuias() {
  const context = useContext(GuiaContext);
  if (!context) throw new Error('useGuias debe usarse dentro de GuiaProvider');
  return context;
}