import { useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { GuiaProvider } from './contexts/GuiaContext';
import LoginPage from './pages/LoginPage';
import Tablero from './pages/Tablero';
import DetalleGuia from './pages/DetalleGuia';
import NuevaGuia from './pages/NuevaGuia';
import AdminDB from './pages/AdminDB';
import LoadtestAdmin from './pages/LoadtestAdmin';
import { NotificacionToast, NavbarNotificaciones } from './components/Notificaciones';
import { NotificacionesProvider, useNotificaciones } from './hooks/useNotificaciones';
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
  const location = useLocation();
  const { toastNotification, markGuiaAsRead } = useNotificaciones();
  const closeToast = useCallback(() => {
    if (toastNotification) markGuiaAsRead(toastNotification.id);
  }, [toastNotification, markGuiaAsRead]);
  
  return (
    <>
      {children}
      
      {/* Navbar con campana de notificaciones */}
      {user && location.pathname !== '/tablero' && <NavbarNotificaciones />}
      
      {/* Toast notification para nuevas guías */}
      {toastNotification && (
        <NotificacionToast
          type="info"
          message={`Guía #${toastNotification.consecutivo || toastNotification.guia_id} · ${toastNotification.estado} · ${toastNotification.cliente}`}
          duration={8000}
          onClose={closeToast}
        />
      )}
    </>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <GuiaProvider>
          <NotificacionesProvider>
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
          </NotificacionesProvider>
        </GuiaProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
