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
<<<<<<< HEAD
    userRol: user?.rol || '',
    pollingInterval: 5000
=======
<<<<<<< HEAD
    userRol: user?.rol || '',
    pollingInterval: 5000
=======
<<<<<<< HEAD
    userRol: user?.rol || '',
    pollingInterval: 5000 // 5 segundos para polling
=======
    userRol: user?.rol || ''
>>>>>>> b704871078b6406ee0e8136d9b6ba91116b7c4dc
>>>>>>> 2692ee69256663c5d5c557b499b2d492361eff7b
>>>>>>> 210ae8543490bde42f42f380aabbcb9a5be4c426
  });
  const unreadGuia = nuevasGuias[0];
  
  return (
    <>
      {children}
      {user && <NavbarNotificaciones />}
      {unreadGuia && user?.rol !== 'ventas' && (
        <NotificacionToast
          type="info"
<<<<<<< HEAD
          message={`Nueva guia #${unreadGuia.consecutivo} de ${unreadGuia.cliente} - Haz clic para ver`}
          duration={15000}
=======
<<<<<<< HEAD
          message={`Nueva guia #${unreadGuia.consecutivo} de ${unreadGuia.cliente} - Haz clic para ver`}
          duration={15000}
=======
<<<<<<< HEAD
          message={`📬 Nueva guía #${unreadGuia.consecutivo} de ${unreadGuia.cliente} - Haz clic para ver`}
          duration={15000}
          persistent={true}
=======
          message={`Nueva guía #${unreadGuia.consecutivo} de ${unreadGuia.cliente}`}
          duration={8000}
>>>>>>> b704871078b6406ee0e8136d9b6ba91116b7c4dc
>>>>>>> 2692ee69256663c5d5c557b499b2d492361eff7b
>>>>>>> 210ae8543490bde42f42f380aabbcb9a5be4c426
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
