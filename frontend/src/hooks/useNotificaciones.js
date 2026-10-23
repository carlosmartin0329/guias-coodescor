import { useState, useEffect, useRef, useCallback } from 'react';

/**
 * Hook para notificaciones en tiempo real con sonido y notificaciones del navegador
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

  // Sonido de notificacion
  const playNotificationSound = useCallback(() => {
    try {
      if (typeof window !== 'undefined') {
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const osc1 = audioContext.createOscillator();
        const gain1 = audioContext.createGain();
        osc1.connect(gain1);
        gain1.connect(audioContext.destination);
        osc1.frequency.value = 1000;
        osc1.type = 'sine';
        gain1.gain.value = 0.2;
        osc1.start();
        osc1.stop(audioContext.currentTime + 0.3);
        
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
      console.warn('Sonido no disponible:', e);
    }
  }, []);

  // Notificacion del navegador
  const showBrowserNotification = useCallback((title, body) => {
    try {
      if (typeof window === 'undefined' || !('Notification' in window)) return;
      if (Notification.permission === 'default') {
        Notification.requestPermission();
        return;
      }
      if (Notification.permission !== 'granted') return;
      
      new Notification(title, {
        body: body,
        icon: '/static/icons/icon-192x192.png',
        vibrate: [200, 100, 200],
        tag: 'nueva-guia'
      });
      
      if ('vibrate' in navigator) {
        navigator.vibrate([100, 50, 100]);
      }
    } catch (e) {
      console.warn('Notificaciones del navegador no disponibles:', e);
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
      
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      
      const data = await response.json();
      
      if (data.ok) {
        const nuevas = data.nuevas || [];
        lastConsultaRef.current = data.timestamp || Date.now() / 1000;
        setLastPollTime(new Date());
        
        if (nuevas.length > 0) {
          setNuevasGuias(prev => {
            const nuevaIds = new Set(nuevas.map(g => g.id));
            return [...nuevas, ...prev.filter(g => !nuevaIds.has(g.id))];
          });
          setHasNew(true);
          
          if (userRol !== 'ventas' && nuevas.length > 0) {
            playNotificationSound();
            const g = nuevas[0];
            showBrowserNotification(
              `Nueva guia #${g.consecutivo || g.id}`,
              `Cliente: ${g.cliente || 'Desconocido'}`
            );
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
      const response = await fetch('/api/notificaciones/conteo', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        if (data.ok) setConteoEstados(data.estados || {});
      }
    } catch (err) {
      setError(err.message);
    }
  }, []);

  // Iniciar polling
  const startPolling = useCallback(() => {
    stopPolling();
    fetchNuevasGuias();
    fetchConteoEstados();
    const poll = () => {
      fetchNuevasGuias();
      fetchConteoEstados();
      pollingTimeoutRef.current = setTimeout(poll, pollingInterval);
    };
    pollingTimeoutRef.current = setTimeout(poll, pollingInterval);
    setIsConnected(true);
  }, [fetchNuevasGuias, fetchConteoEstados, pollingInterval]);

  const stopPolling = useCallback(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Iniciar SSE
  const startSSE = useCallback(() => {
    if (typeof window === 'undefined' || !window.EventSource) return false;
    try {
      if (eventSourceRef.current) eventSourceRef.current.close();
      const eventSource = new EventSource('/api/sse', { withCredentials: true });
      eventSourceRef.current = eventSource;
      eventSource.onopen = () => setIsConnected(true);
      eventSource.onerror = () => { setIsConnected(false); eventSource.close(); };
      eventSource.addEventListener('nueva_guia', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (!nuevasGuias.some(g => g.id === data.guia_id)) {
            setNuevasGuias(prev => [{ id: data.guia_id, ...data }, ...prev]);
            setHasNew(true);
          }
          if (userRol !== 'ventas') {
            playNotificationSound();
            showBrowserNotification(
              `Nueva guia #${data.consecutivo || data.guia_id}`,
              `Cliente: ${data.cliente || 'Desconocido'}`
            );
          }
        } catch (e) { console.error('Error SSE:', e); }
      });
      eventSource.addEventListener('estado_actualizado', () => fetchConteoEstados());
      return true;
    } catch (e) { console.error('SSE error:', e); return false; }
  }, [userRol, playNotificationSound, showBrowserNotification, fetchConteoEstados, nuevasGuias]);

  const stopSSE = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsConnected(false);
  }, []);

  // Iniciar al montar
  useEffect(() => {
    startPolling();
    startSSE();
    return () => { stopPolling(); stopSSE(); };
  }, [startPolling, startSSE, stopPolling, stopSSE]);

  const markAllAsRead = useCallback(() => {
    setNuevasGuias([]);
    setHasNew(false);
    lastConsultaRef.current = Date.now() / 1000;
  }, []);

  const markGuiaAsRead = useCallback((guiaId) => {
    setNuevasGuias(prev => prev.filter(g => g.id !== guiaId));
    if (nuevasGuias.length === 1) setHasNew(false);
  }, [nuevasGuias.length]);

  const getPendientesCount = useCallback((rol) => {
    const pendingStates = {
      'administrativo': ['CREADA'],
      'cedis': ['RECIBIDA_ADMIN', 'EN_CEDIS'],
      'transportador': ['EN_RUTA'],
    };
    const states = pendingStates[rol] || [];
    let count = states.reduce((sum, state) => sum + (conteoEstados[state] || 0), 0);
    if (hasNew) {
      count += nuevasGuias.filter(g => states.includes(g.estado || '')).length;
    }
    return count;
  }, [conteoEstados, hasNew, nuevasGuias]);

  return {
    nuevasGuias, conteoEstados, hasNew, lastPollTime, isConnected, error,
    startPolling, stopPolling, startSSE, stopSSE, markAllAsRead, markGuiaAsRead,
    getPendientesCount, playNotificationSound, showBrowserNotification,
    fetchNuevasGuias, fetchConteoEstados,
  };
}

export function useNotificacionesBadge(rol) {
  const { hasNew, getPendientesCount } = useNotificaciones({ userRol: rol });
  return { hasNew, count: getPendientesCount(rol) };
}
