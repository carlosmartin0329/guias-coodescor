import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Hook personalizado para manejar notificaciones en tiempo real.
 * 
 * Usa polling para consultar periodicamente nuevas guias (cada 5 segundos).
 * Tambien soporta Server-Sent Events (SSE) para actualizacion instantanea.
 * 
 * @param {Object} options - Opciones de configuracion
 * @param {number} options.pollingInterval - Intervalo de polling en ms (default: 5000)
 * @param {string} options.userRol - Rol del usuario actual
 * @returns {Object} - Estado y funciones de notificacion
 */
export function useNotificaciones(options = {}) {
  const { pollingInterval = 5000, userRol = '' } = options;
  
  const [nuevasGuias, setNuevasGuias] = useState([]);
  const [conteoEstados, setConteoEstados] = useState({});
  const [hasNew, setHasNew] = useState(false);
  const [lastPollTime, setLastPollTime] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  
  const lastConsultaRef = useRef(null);
  const pollingTimeoutRef = useRef(null);
  const eventSourceRef = useRef(null);

  // Solicitar permiso de notificaciones del navegador
  useEffect(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission === 'default') {
        Notification.requestPermission();
      }
    }
  }, []);

  // Sonido de notificacion mejorado
  const playNotificationSound = useCallback(() => {
    try {
      if (typeof window !== 'undefined') {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Primer beep
        const osc1 = audioContext.createOscillator();
        const gain1 = audioContext.createGain();
        osc1.connect(gain1);
        gain1.connect(audioContext.destination);
        osc1.frequency.value = 1000;
        osc1.type = 'sine';
        gain1.gain.value = 0.2;
        osc1.start();
        osc1.stop(audioContext.currentTime + 0.3);
        
        // Segundo beep (mas agudo)
        const osc2 = audioContext.createOscillator();
        const gain2 = audioContext.createGain();
        osc2.connect(gain2);
        gain2.connect(audioContext.destination);
        osc2.frequency.value = 1500;
        osc2.type = 'sine';
        gain2.gain.value = 0.15;
        osc2.start(audioContext.currentTime + 0.1);
        osc2.stop(audioContext.currentTime + 0.4);
      }
    } catch (e) {
      console.warn('Web Audio API no disponible:', e);
    }
  }, []);

  // Mostrar notificacion del navegador
  const showBrowserNotification = useCallback((title, body) => {
    try {
      if (typeof window === 'undefined' || !('Notification' in window)) return;
      if (Notification.permission !== 'granted') return;
      
      new Notification(title, {
        body: body,
        icon: '/static/icons/icon-192x192.png',
        vibrate: [200, 100, 200],
        tag: 'nueva-guia-notification'
      });
      
      // Vibrar en dispositivos mobiles
      if ('vibrate' in navigator) {
        navigator.vibrate([100, 50, 100]);
      }
    } catch (e) {
      console.warn('No se pudo mostrar notificacion del navegador:', e);
    }
  }, []);

  // Consultar nuevas guias
  const fetchNuevasGuias = useCallback(async () => {
    try {
      const timestamp = lastConsultaRef.current || 0;
      const response = await fetch(
        `/api/notificaciones/nuevas_guias?ultima_consulta=${timestamp}`,
        { credentials: 'include' }
      );
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.ok) {
        const nuevas = data.nuevas || [];
        lastConsultaRef.current = data.timestamp || Date.now() / 1000;
        setLastPollTime(new Date());
        
        if (nuevas.length > 0) {
          setNuevasGuias(prev => {
            // Evitar duplicados
            const nuevaIds = new Set(nuevas.map(g => g.id));
            const filtered = prev.filter(g => !nuevaIds.has(g.id));
            return [...nuevas, ...filtered];
          });
          setHasNew(true);
          
          // Reproducir sonido y mostrar notificacion solo si no es ventas
          if (userRol !== 'ventas' && nuevas.length > 0) {
            playNotificationSound();
            
            // Mostrar notificacion del navegador
            const primeraGuia = nuevas[0];
            const title = `Nueva guia #${primeraGuia.consecutivo || primeraGuia.id}`;
            const body = `Cliente: ${primeraGuia.cliente || 'Desconocido'}`;
            showBrowserNotification(title, body);
          }
        }
        
        return nuevas.length;
      }
      return 0;
    } catch (err) {
      setError(err.message);
      return 0;
    }
  }, [userRol, playNotificationSound, showBrowserNotification]);

  // Consultar conteo por estado
  const fetchConteoEstados = useCallback(async () => {
    try {
      const response = await fetch(
        `/api/notificaciones/conteo`,
        { credentials: 'include' }
      );
      
      if (response.ok) {
        const data = await response.json();
        if (data.ok) {
          setConteoEstados(data.estados || {});
        }
      }
    } catch (err) {
      setError(err.message);
    }
  }, []);

  // Iniciar polling
  const startPolling = useCallback(() => {
    stopPolling();
    
    // Consulta inicial
    fetchNuevasGuias();
    fetchConteoEstados();
    
    // Iniciar polling periodico cada 5 segundos
    const poll = () => {
      fetchNuevasGuias();
      fetchConteoEstados();
      pollingTimeoutRef.current = setTimeout(poll, pollingInterval);
    };
    
    pollingTimeoutRef.current = setTimeout(poll, pollingInterval);
    setIsConnected(true);
  }, [fetchNuevasGuias, fetchConteoEstados, pollingInterval]);

  // Detener polling
  const stopPolling = useCallback(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Iniciar SSE (opcional, para navegadores modernos)
  const startSSE = useCallback(() => {
    if (typeof window === 'undefined' || !window.EventSource) {
      return false;
    }
    
    try {
      // Cerrar conexion anterior si existe
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
      
      const eventSource = new EventSource('/api/sse', { withCredentials: true });
      eventSourceRef.current = eventSource;
      
      eventSource.onopen = () => {
        setIsConnected(true);
      };
      
      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource.close();
      };
      
      eventSource.addEventListener('nueva_guia', (event) => {
        try {
          const data = JSON.parse(event.data);
          setNuevasGuias(prev => {
            // Evitar duplicados
            if (prev.some(g => g.id === data.guia_id)) {
              return prev;
            }
            return [{ id: data.guia_id, ...data }, ...prev];
          });
          setHasNew(true);
          
          if (userRol !== 'ventas') {
            playNotificationSound();
            showBrowserNotification(
              `Nueva guia #${data.consecutivo || data.guia_id}`,
              `Cliente: ${data.cliente || 'Desconocido'}`
            );
          }
        } catch (e) {
          console.error('Error parsing SSE event:', e);
        }
      });
      
      eventSource.addEventListener('estado_actualizado', (event) => {
        try {
          const data = JSON.parse(event.data);
          // Actualizar conteo de estados
          fetchConteoEstados();
        } catch (e) {
          console.error('Error parsing SSE event:', e);
        }
      });
      
      return true;
    } catch (e) {
      console.error('SSE not supported:', e);
      return false;
    }
  }, [userRol, playNotificationSound, showBrowserNotification, fetchConteoEstados]);

  // Detener SSE
  const stopSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Limpiar al desmontar
  useEffect(() => {
    startPolling();
    
    // Intentar SSE (fallback a polling si no esta disponible)
    const sseStarted = startSSE();
    if (!sseStarted) {
      // SSE no disponible, usar solo polling
    }
    
    return () => {
      stopPolling();
      stopSSE();
    };
  }, [startPolling, startSSE, stopPolling, stopSSE]);

  // Marcar todas las notificaciones como leidas
  const markAllAsRead = useCallback(() => {
    setNuevasGuias([]);
    setHasNew(false);
    lastConsultaRef.current = Date.now() / 1000;
  }, []);

  // Marcar una guia especifica como leida
  const markGuiaAsRead = useCallback((guiaId) => {
    setNuevasGuias(prev => prev.filter(g => g.id !== guiaId));
    if (nuevasGuias.length === 1) {
      setHasNew(false);
    }
  }, [nuevasGuias.length]);

  // Obtener conteo de guias pendientes para un rol especifico
  const getPendientesCount = useCallback((rol) => {
    const pendingStates = {
      'administrativo': ['CREADA'],
      'cedis': ['RECIBIDA_ADMIN', 'EN_CEDIS'],
      'transportador': ['EN_RUTA'],
    };
    
    const states = pendingStates[rol] || [];
    let count = 0;
    
    for (const state of states) {
      count += conteoEstados[state] || 0;
    }
    
    // Tambien contar las nuevas guias no leidas
    if (hasNew) {
      count += nuevasGuias.filter(g => {
        const state = g.estado || '';
        return states.includes(state);
      }).length;
    }
    
    return count;
  }, [conteoEstados, hasNew, nuevasGuias]);

  return {
    // Estado
    nuevasGuias,
    conteoEstados,
    hasNew,
    lastPollTime,
    isConnected,
    error,
    
    // Funciones
    startPolling,
    stopPolling,
    startSSE,
    stopSSE,
    markAllAsRead,
    markGuiaAsRead,
    getPendientesCount,
    playNotificationSound,
    showBrowserNotification,
    fetchNuevasGuias,
    fetchConteoEstados,
  };
}

/**
 * Hook simplificado para mostrar badge de notificaciones
 */
export function useNotificacionesBadge(rol) {
  const { hasNew, getPendientesCount } = useNotificaciones({ userRol: rol });
  const count = getPendientesCount(rol);
  
  return { hasNew, count };
}
