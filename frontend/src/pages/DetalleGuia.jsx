import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import * as guiasApi from '../api/guias';
import api from '../api';
import { useAuth } from '../contexts/AuthContext';
import './DetalleGuia.css';

export default function DetalleGuia() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [guia, setGuia] = useState(null);
  const [eventos, setEventos] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelado = false;
    const cargar = async () => {
      setCargando(true);
      setError(null);
      try {
        const [detalle, evs] = await Promise.all([
          guiasApi.guiasDetalle(id),
          guiasApi.guiasEventos(id),
        ]);
        if (!cancelado) {
          setGuia(detalle.guia);
          setEventos(evs.eventos || []);
        }
      } catch (err) {
        if (!cancelado) setError(err.error || 'Error al cargar la guía');
      } finally {
        if (!cancelado) setCargando(false);
      }
    };
    cargar();
    return () => { cancelado = true; };
  }, [id]);

  const ejecutarEvento = async (tipo) => {
    try {
      await guiasApi.guiasEvento(id, tipo, {});
      const [detalle, evs] = await Promise.all([
        guiasApi.guiasDetalle(id),
        guiasApi.guiasEventos(id),
      ]);
      setGuia(detalle.guia);
      setEventos(evs.eventos || []);
    } catch (err) {
      alert(err.error || 'No se pudo ejecutar el paso');
    }
  };

  if (cargando) return <div className="container">Cargando…</div>;
  if (error) return <div className="container error">{error}</div>;
  if (!guia) return <div className="container">Guía no encontrada</div>;

  return (
    <div className="detalle">
      <header className="detalle-header">
        <div>
          <Link to="/tablero" className="btn-mini">← Volver</Link>
          <h1>Guía #{guia.id} · {guia.estado}</h1>
        </div>
        <div className="detalle-usuario">
          <span>{user?.nombre || user?.usuario}</span>
          <button onClick={logout} className="btn-mini">Salir</button>
        </div>
      </header>

      <section className="card">
        <h2>Datos de la guía</h2>
        <div className="grid">
          <div><strong>Cliente:</strong> {guia.cliente}</div>
          <div><strong>Ciudad:</strong> {guia.ciudad}</div>
          <div><strong>Dirección:</strong> {guia.direccion}</div>
          <div><strong>Documentos:</strong> {guia.documentos}</div>
          <div><strong>Creada por:</strong> {guia.creada_por}</div>
          <div><strong>Creada en:</strong> {guia.creada_en}</div>
          {guia.anulada_motivo && <div><strong>Anulada:</strong> {guia.anulada_motivo}</div>}
        </div>
      </section>

      <section className="card">
        <h2>Acciones</h2>
        <div className="acciones">
          {user?.rol === 'ventas' && guia.estado === 'CREADA' && (
            <button onClick={() => ejecutarEvento('edicion_guia')}>Editar guía</button>
          )}
          {user?.rol === 'administrativo' && guia.estado === 'CREADA' && (
            <button onClick={() => ejecutarEvento('recepcion_admin')}>Recibir en admin</button>
          )}
          {user?.rol === 'cedis' && (guia.estado === 'CREADA' || guia.estado === 'RECIBIDA_ADMIN' || guia.estado === 'EN_CEDIS') && (
            <button onClick={() => ejecutarEvento('control_cedis')}>Control CEDIS</button>
          )}
          {user?.rol === 'cedis' && (guia.estado === 'EN_CEDIS' || guia.estado === 'EN_RUTA') && (
            <button onClick={() => ejecutarEvento('entrega_transporte')}>Entrega a transporte</button>
          )}
          {user?.rol === 'cedis' && guia.estado === 'EN_RUTA' && (
            <button onClick={() => ejecutarEvento('entrega_cliente')}>Entrega a cliente</button>
          )}
          {user?.rol === 'admin' && guia.estado !== 'ENTREGADA' && guia.estado !== 'ANULADA' && (
            <button onClick={() => ejecutarEvento('anular')} className="peligro">Anular guía</button>
          )}
        </div>
      </section>
    </div>
  );
}
