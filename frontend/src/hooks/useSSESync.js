import { useState, useEffect, useCallback, useRef } from 'react';

/**
 * Hook para sincronizar el estado de la aplicación con eventos SSE.
 * 
 * Conecta el EventSource a los eventos del backend y actualiza el estado
 * local sin necesidad de recargar la página.
 * 
 * @param {Object} options - Opciones de configuración
 * @param {Function} options.onNuevaGuia - Callback cuando se crea una nueva guía
 * @param {Function} options.onEstadoActualizado - Callback cuando cambia el estado de una guía
 * @param {Function} options.onConteoActualizado - Callback cuando cambia el conteo por estado
 * @returns {Object} Estado de la conexión SSE
 */
export function useSSESync(options = {}) {
  const {
    onNuevaGuia,
    onEstadoActualizado,
    onConteoActualizado,
    enabled = true,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const eventSourceRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const reconnectDelay = 3000;

  // Mantener referencias estables a los callbacks
  const onNuevaGuiaRef = useRef(onNuevaGuia);
  const onEstadoActualizadoRef = useRef(onEstadoActualizado);
  const onConteoActualizadoRef = useRef(onConteoActualizado);

  useEffect(() => {
    onNuevaGuiaRef.current = onNuevaGuia;
    onEstadoActualizadoRef.current = onEstadoActualizado;
    onConteoActualizadoRef.current = onConteoActualizado;
  }, [onNuevaGuia, onEstadoActualizado, onConteoActualizado]);

  const connect = useCallback(() => {
    if (typeof window === 'undefined' || !window.EventSource) {
      return;
    }

    // Cerrar conexión anterior si existe
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const eventSource = new EventSource('/api/sse', { withCredentials: true });
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
      };

      eventSource.onerror = (err) => {
        setIsConnected(false);
        setError('Conexión SSE perdida. Reintentando...');
        eventSource.close();
        scheduleReconnect();
      };

      // Evento: nueva guía creada
      eventSource.addEventListener('nueva_guia', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onNuevaGuiaRef.current) {
            onNuevaGuiaRef.current(data);
          }
        } catch (e) {
          console.error('Error parseando evento nueva_guia:', e);
        }
      });

      // Evento: estado de guía actualizado
      eventSource.addEventListener('estado_actualizado', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onEstadoActualizadoRef.current) {
            onEstadoActualizadoRef.current(data);
          }
        } catch (e) {
          console.error('Error parseando evento estado_actualizado:', e);
        }
      });

      // Evento: conteo por estado actualizado
      eventSource.addEventListener('conteo_actualizado', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onConteoActualizadoRef.current) {
            onConteoActualizadoRef.current(data);
          }
        } catch (e) {
          console.error('Error parseando evento conteo_actualizado:', e);
        }
      });

    } catch (e) {
      setError('No se pudo conectar SSE: ' + e.message);
    }
  }, []);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      setError('No se pudo reconectar SSE después de ' + maxReconnectAttempts + ' intentos.');
      return;
    }

    reconnectAttemptsRef.current += 1;
    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, reconnectDelay);
  }, [connect]);

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Conectar al montar
  useEffect(() => {
    if (!enabled) {
      return;
    }

    connect();

    return () => {
      disconnect();
    };
  }, [enabled, connect, disconnect]);

  return {
    isConnected,
    error,
    disconnect,
    reconnect: connect,
  };
}