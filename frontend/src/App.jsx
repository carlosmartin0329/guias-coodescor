import { useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { GuiaProvider } from './contexts/GuiaContext';
import LoginPage from './pages/LoginPage';
import Tablero from './pages/Tablero';
import DetalleGuia from './pages/DetalleGuia';
import NuevaGuia from './pages/NuevaGuia';
import AdminDB from './pages/AdminDB';
import LoadtestAdmin from './pages/LoadtestAdmin';
import Confirmaciones from './pages/Confirmaciones';
import { NotificacionToast } from './components/Notificaciones';
import { NotificacionesProvider, useNotificaciones } from './hooks/useNotificaciones';
import './styles/global.css';

function Protegido({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="loading-block"><span className="spinner" /> Restaurando sesión…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function SoloAdmin({ children }) {
  const { user } = useAuth();
  if (user?.rol !== 'admin') return <Navigate to="/tablero" replace />;
  return children;
}

// La creación de guías está reservada al rol Ventas (el backend responde 403 a
// cualquier otro rol). Antes, entrar por URL directa a /nueva-guia mostraba el
// formulario a cualquier usuario y solo fallaba al enviar.
function SoloVentas({ children }) {
  const { user } = useAuth();
  if (user?.rol !== 'ventas') return <Navigate to="/tablero" replace />;
  return children;
}

function SoloVentasOAdministrativo({ children }) {
  const { user } = useAuth();
  if (!['ventas', 'administrativo'].includes(user?.rol)) return <Navigate to="/tablero" replace />;
  return children;
}

// Componente de layout con notificaciones
function AppLayout({ children }) {
  const { toastNotification, dismissToast } = useNotificaciones();
  const closeToast = useCallback(() => {
    // Cerrar el aviso NO marca la notificación como leída: antes el toast se
    // autodestruía a los 8 s y la guía desaparecía de la campana sin que el
    // usuario hubiera hecho nada.
    dismissToast();
  }, [dismissToast]);
  
  return (
    <>
      {children}
      
      {/* Toast notification para nuevas guías (la campana vive en AppShell) */}
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
              <Route path="/nueva-guia" element={<Protegido><SoloVentas><NuevaGuia /></SoloVentas></Protegido>} />
              <Route path="/confirmaciones" element={<Protegido><SoloVentasOAdministrativo><Confirmaciones /></SoloVentasOAdministrativo></Protegido>} />
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
