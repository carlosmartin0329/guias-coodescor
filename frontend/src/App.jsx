import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { GuiaProvider } from './contexts/GuiaContext';
import LoginPage from './pages/LoginPage';
import Tablero from './pages/Tablero';
import DetalleGuia from './pages/DetalleGuia';
import NuevaGuia from './pages/NuevaGuia';
import AdminDB from './pages/AdminDB';
import LoadtestAdmin from './pages/LoadtestAdmin';
import { NotificacionToast, NavbarNotificaciones } from './components/Notificaciones';
import { useNotificaciones } from './hooks/useNotificaciones';
import './styles/global.css';

function Protegido({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="container">Cargando...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function SoloAdmin({ children }) {
  const { user } = useAuth();
  if (user?.rol !== 'admin') return <Navigate to="/tablero" replace />;
  return children;
}

function AppLayout({ children }) {
  const { user } = useAuth();
  const { hasNew, nuevasGuias, markAllAsRead, markGuiaAsRead } = useNotificaciones({
    userRol: user?.rol || '',
    pollingInterval: 5000
  });
  const unreadGuia = nuevasGuias[0];
  
  return (
    <>
      {children}
      {user && <NavbarNotificaciones />}
      {unreadGuia && user?.rol !== 'ventas' && (
        <NotificacionToast
          type="info"
          message={`Nueva guia #${unreadGuia.consecutivo} de ${unreadGuia.cliente} - Haz clic para ver`}
          duration={15000}
          onClose={() => markGuiaAsRead(unreadGuia.id)}
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
