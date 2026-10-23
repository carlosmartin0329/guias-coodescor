import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Hook personalizado para manejar notificaciones en tiempo real.
 * 
 * Usa polling para consultar periódicamente nuevas guías.
 * También soporta Server-Sent Events (SSE) para actualización instantánea.
 * 
 * @param {Object} options - Opciones de configuración
 * @param {number} options.pollingInterval - Intervalo de polling en ms (default: 5000)
 * @param {string} options.userRol - Rol del usuario actual
 * @returns {Object} - Estado y funciones de notificación
 */
export function useNotificaciones(options = {}) {
  const { pollingInterval = 5000, userRol = '' } = options;
  
  const [nuevasGuias, setNuevasGuias] = useState([]);
  const [conteoEstados, setConteoEstados] = useState({});
  const [hasNew, setHasNew] = useState(false);
  const [lastPollTime, setLastPollTime] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState(null);
  const [notificationPermission, setNotificationPermission] = useState('default');
  
  const lastConsultaRef = useRef(null);
  const pollingTimeoutRef = useRef(null);
  const eventSourceRef = useRef(null);
  const notificationShownRef = useRef(false);
  
  // Solicitar permiso de notificaciones del navegador
  useEffect(() => {
    if (typeof window !== 'undefined' && 'Notification' in window) {
      if (Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
          setNotificationPermission(permission);
        });
      } else {
        setNotificationPermission(Notification.permission);
      }
    }
  }, []);

  // Sonido de notificación mejorado
  const playNotificationSound = useCallback(() => {
    try {
      if (typeof window === 'undefined') return;
      
      // Usar AudioContext para crear un beep
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      // Crear un sonido más notable: dos beeps
      oscillator.frequency.setValueAtTime(1000, audioContext.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(1500, audioContext.currentTime + 0.1);
      oscillator.type = 'sine';
      gainNode.gain.setValueAtTime(0.2, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.2);
      
      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.2);
      
      // Toque adicional más agudo
      const oscillator2 = audioContext.createOscillator();
      const gainNode2 = audioContext.createGain();
      oscillator2.connect(gainNode2);
      gainNode2.connect(audioContext.destination);
      oscillator2.frequency.value = 1500;
      oscillator2.type = 'sine';
      gainNode2.gain.value = 0.15;
      oscillator2.start(audioContext.currentTime + 0.05);
      oscillator2.stop(audioContext.currentTime + 0.25);
      
    } catch (e) {
      console.warn('Web Audio API no disponible, usando fallback:', e);
      try {
        // Fallback: crear elemento audio
        const audio = document.createElement('audio');
        audio.src = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEARKwAAIhYAQACABAAZGF0YQoGAACBhYqFbF1fdJigrD2jcTFj1UGlGDB8fv0dAjqOjQABj+ISj5n9YAGAf8err3kfQD2SgO+agICAgICAgICAgIA==';
        audio.volume = 0.5;
        audio.play().catch(() => {});
      } catch (e2) {
        console.warn('No se pudo reproducir sonido:', e2);
      }
    }
  }, []);

  // Mostrar notificación del navegador
  const showBrowserNotification = useCallback((title, body) => {
    try {
      if (typeof window === 'undefined' || !('Notification' in window)) return;
      if (Notification.permission !== 'granted') return;
      
      // Evitar mostrar múltiples notificaciones para la misma guía
      if (notificationShownRef.current) return;
      notificationShownRef.current = true;
      
      const notification = new Notification(title, {
        body: body,
        icon: '/static/icons/icon-192x192.png',
        vibrate: [200, 100, 200],
        tag: 'nueva-guia-notification'
      });
      
      notification.onclick = () => {
        window.focus();
        notification.close();
        notificationShownRef.current = false;
      };
      
      notification.onclose = () => {
        notificationShownRef.current = false;
      };
      
      // Auto-cerrar después de 5 segundos
      setTimeout(() => {
        notification.close();
        notificationShownRef.current = false;
      }, 5000);
    } catch (e) {
      console.warn('No se pudo mostrar notificación del navegador:', e);
    }
  }, []);

  // Consultar nuevas guías
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
          
          // Reproducir sonido y mostrar notificación solo si hay nuevas guías y no es el usuario de ventas
          if (userRol !== 'ventas' && nuevas.length > 0) {
            playNotificationSound();
            
            // Mostrar notificación del navegador
            const primeraGuia = nuevas[0];
            const title = `Nueva guía #${primeraGuia.consecutivo || primeraGuia.id}`;
            const body = `Cliente: ${primeraGuia.cliente || 'Desconocido'}`;
            showBrowserNotification(title, body);
            
            // Vibrar el dispositivo móvil si está soportado
            if ('vibrate' in navigator) {
              navigator.vibrate([100, 50, 100]);
            }
          }
        }
        
        return nuevas.length;
      }
      return 0;
    } catch (err) {
      setError(err.message);
      return 0;
    }
  }, [userRol, playNotificationSound]);

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
    
    // Iniciar polling periódico (más frecuente)
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
      // Cerrar conexión anterior si existe
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
  }, [userRol, playNotificationSound, fetchConteoEstados]);

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
    
    // Intentar SSE (fallback a polling si no está disponible)
    const sseStarted = startSSE();
    if (!sseStarted) {
      // SSE no disponible, usar solo polling
    }
    
    return () => {
      stopPolling();
      stopSSE();
    };
  }, [startPolling, startSSE, stopPolling, stopSSE]);

  // Marcar todas las notificaciones como leídas
  const markAllAsRead = useCallback(() => {
    setNuevasGuias([]);
    setHasNew(false);
    lastConsultaRef.current = Date.now() / 1000;
  }, []);

  // Marcar una guía específica como leída
  const markGuiaAsRead = useCallback((guiaId) => {
    setNuevasGuias(prev => prev.filter(g => g.id !== guiaId));
    if (nuevasGuias.length === 1) {
      setHasNew(false);
    }
  }, [nuevasGuias.length]);

  // Obtener conteo de guías pendientes para un rol específico
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
    
    // También contar las nuevas guías no leídas
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
