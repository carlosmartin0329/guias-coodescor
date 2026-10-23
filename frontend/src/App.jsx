import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { GuiaProvider, useGuias } from './contexts/GuiaContext';
import LoginPage from './pages/LoginPage';
import Tablero from './pages/Tablero';
import DetalleGuia from './pages/DetalleGuia';
import NuevaGuia from './pages/NuevaGuia';
import AdminDB from './pages/AdminDB';
import LoadtestAdmin from './pages/LoadtestAdmin';
import { NotificacionToast, NavbarNotificaciones } from './components/Notificaciones';
import { useSSESync } from './hooks/useSSESync';
import { useNotificaciones } from './hooks/useNotificaciones';
import { useState, useEffect, useCallback } from 'react';
import './styles/global.css';

function Protegido({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="container">Cargando…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function SoloAdmin({ children }) {
  const { user } = useAuth();
  if (user?.rol !== 'admin') return <Navigate to="/tablero" replace />;
  return children;
}

// Componente de layout con notificaciones
function AppLayout({ children }) {
  const { user } = useAuth();
  const { guias, conteo, ultimaActualizacion, sseConnected } = useGuias();
  const [toasts, setToasts] = useState([]);
  
  // Hook de notificaciones tradicional (polling)
  const { 
    nuevasGuias, 
    markAllAsRead, 
    markGuiaAsRead,
    playNotificationSound,
    showBrowserNotification,
  } = useNotificaciones({
    userRol: user?.rol || ''
  });

  // Efecto para reproducir sonido cuando hay nuevas guías
  useEffect(() => {
    if (nuevasGuias.length > 0 && user?.rol !== 'ventas') {
      playNotificationSound();
      
      // Mostrar browser notification
      const primeraGuia = nuevasGuias[0];
      showBrowserNotification(
        `Nueva guía #${primeraGuia.consecutivo || primeraGuia.id}`,
        `Cliente: ${primeraGuia.cliente || 'Desconocido'}`
      );
    }
  }, [nuevasGuias, user?.rol, playNotificationSound, showBrowserNotification]);

  // Agregar toast cuando haya nuevas guías
  useEffect(() => {
    if (nuevasGuias.length > 0 && user?.rol !== 'ventas') {
      const nueva = nuevasGuias[0];
      const toast = {
        id: `toast-${Date.now()}`,
        message: `Nueva guía #${nueva.consecuito || nueva.id} de ${nueva.cliente}`,
        type: 'info',
        duration: 8000,
      };
      
      setToasts(prev => [...prev, toast]);
      
      // Auto-remover después de la duración
      const timer = setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== toast.id));
      }, toast.duration);
      
      return () => clearTimeout(timer);
    }
  }, [nuevasGuias, user?.rol]);

  const closeToast = useCallback((toastId) => {
    setToasts(prev => prev.filter(t => t.id !== toastId));
  }, []);

  const handleGuiaClick = (guia) => {
    markGuiaAsRead(guia.id);
    window.location.href = `/guia/${guia.id}`;
  };

  return (
    <>
      {children}
      
      {/* Navbar con campana de notificaciones */}
      {user && <NavbarNotificaciones />}
      
      {/* Toast notifications */}
      {toasts.map(toast => (
        <NotificacionToast
          key={toast.id}
          type={toast.type}
          message={toast.message}
          duration={toast.duration}
          onClose={() => closeToast(toast.id)}
        />
      ))}
      
      {/* Indicador de conexión SSE */}
      {user && (
        <div className="sse-status" title={sseConnected ? 'Conectado en tiempo real' : 'Polling activo'}>
          {sseConnected ? '●' : '○'}
        </div>
      )}
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <GuiaProvider>
          <AppLayout>
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/tablero" element={<Protegido><Tablero /></Protegido>} />
              <Route path="/guia/:id" element={<Protegido><DetalleGuia /></Protegido>} />
              <Route path="/nueva-guia" element={<Protegido><NuevaGuia /></Protegido>} />
              <Route path="/admin/db" element={<Protegido><SoloAdmin><AdminDB /></SoloAdmin></Protegido>} />
              <Route path="/admin/loadtest" element={<Protegido><SoloAdmin><LoadtestAdmin /></SoloAdmin></Protegido>} />
              <Route path="*" element={<Navigate to="/tablero" replace />} />
            </Routes>
          </AppLayout>
        </GuiaProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;