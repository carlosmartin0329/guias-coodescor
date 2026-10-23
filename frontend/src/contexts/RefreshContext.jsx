import { createContext, useContext, useState, useCallback } from 'react';

/**
 * Contexto para manejar el refresh global de datos en la aplicación.
 * Esto permite que cualquier componente pueda forzar una actualización de datos.
 */
const RefreshContext = createContext();

export function RefreshProvider({ children }) {
  const [refreshKey, setRefreshKey] = useState(0);
  
  /**
   * Función para forzar un refresh global.
   * Incrementa la clave de refresh, lo que hace que todos los componentes
   * que dependan de esta clave se vuelvan a renderizar.
   */
  const forceRefresh = useCallback(() => {
    setRefreshKey(prev => prev + 1);
  }, []);
  
  /**
   * Función para forzar refresh después de un tiempo.
   */
  const scheduleRefresh = useCallback((delay = 1000) => {
    setTimeout(() => {
      setRefreshKey(prev => prev + 1);
    }, delay);
  }, []);
  
  return (
    <RefreshContext.Provider value={{ refreshKey, forceRefresh, scheduleRefresh }}>
      {children}
    </RefreshContext.Provider>
  );
}

export function useRefresh() {
  const context = useContext(RefreshContext);
  if (!context) {
    throw new Error('useRefresh debe usarse dentro de un RefreshProvider');
  }
  return context;
}
