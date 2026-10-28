import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import AppShell from '../components/AppShell';
import Icon from '../components/Icon';
import * as guiasApi from '../api/guias';
import { Toast, useToast } from '../components/ui';

const ESTADOS = {
  pendiente: { texto: 'Pendiente', tono: 'warning' },
  aplicada: { texto: 'Aplicada', tono: 'success' },
  duplicada: { texto: 'Duplicada', tono: 'neutral' },
  error: { texto: 'Revisar', tono: 'danger' },
};

function fecha(valor) {
  if (!valor) return '—';
  try {
    const d = new Date(valor);
    if (Number.isNaN(d.getTime())) return String(valor);
    return d.toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' });
  } catch {
    return String(valor);
  }
}

export default function Confirmaciones() {
  const [items, setItems] = useState([]);
  const [cargando, setCargando] = useState(true);
  const [sincronizando, setSincronizando] = useState(false);
  const [error, setError] = useState('');
  const { toast, showToast, closeToast } = useToast();

  const cargar = useCallback(async () => {
    setError('');
    try {
      const data = await guiasApi.confirmacionesListar({ limite: 200 });
      setItems(data.confirmaciones || []);
    } catch (err) {
      setError(err?.error || 'No se pudieron cargar las confirmaciones.');
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const sincronizar = async () => {
    setSincronizando(true);
    setError('');
    try {
      const data = await guiasApi.confirmacionesSincronizar();
      showToast(
        `Sincronización: ${data.aplicadas || 0} aplicadas, ${data.duplicadas || 0} duplicadas, ${data.errores || 0} por revisar.`,
      );
      await cargar();
    } catch (err) {
      setError(err?.error || 'No se pudo sincronizar con Google.');
    } finally {
      setSincronizando(false);
    }
  };

  const pendientes = items.filter((c) => c.estado === 'pendiente').length;
  const errores = items.filter((c) => c.estado === 'error').length;

  return (
    <AppShell
      title="Confirmaciones"
      subtitle="Recibidos confirmados desde el link gratuito de Google."
      breadcrumb="Confirmaciones"
      actions={(
        <>
          <button type="button" className="btn" onClick={cargar} disabled={sincronizando}>
            <Icon name="refresh" size={15} /> Actualizar
          </button>
          <button type="button" className="btn btn-primary" onClick={sincronizar} disabled={sincronizando}>
            <Icon name="download" size={15} /> {sincronizando ? 'Sincronizando…' : 'Sincronizar ahora'}
          </button>
        </>
      )}
    >
      {error ? <div className="inline-alert" role="alert" style={{ marginBottom: 12 }}><Icon name="alert" size={16} /> {error}</div> : null}

      <div className="kpis" style={{ marginBottom: 14 }}>
        <div className="kpi"><span className="kpi-icon blue"><Icon name="file" size={16} /></span><span className="kpi-label">Total registradas</span><b className="kpi-value num">{items.length}</b></div>
        <div className="kpi"><span className="kpi-icon amber"><Icon name="clock" size={16} /></span><span className="kpi-label">Pendientes</span><b className="kpi-value num">{pendientes}</b></div>
        <div className="kpi"><span className="kpi-icon red"><Icon name="alert" size={16} /></span><span className="kpi-label">Por revisar</span><b className="kpi-value num">{errores}</b></div>
      </div>

      <section className="panel">
        <div className="panel-head">
          <div className="panel-title">Confirmaciones de recibido</div>
          <span className="panel-sub" style={{ marginLeft: 'auto' }}>Sincronización automática cada 5 minutos</span>
        </div>
        <div className="panel-body">
          {cargando ? <div className="loading-block"><span className="spinner" /> Cargando…</div> : null}
          {!cargando && items.length === 0 ? (
            <p className="nota">Todavía no hay confirmaciones. Cuando un cliente confirme el link, aparecerá aquí.</p>
          ) : null}
          {items.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Guía</th>
                    <th>Cliente</th>
                    <th>Confirmó</th>
                    <th>Recibe</th>
                    <th>Observaciones</th>
                    <th>Estado</th>
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const meta = ESTADOS[item.estado] || ESTADOS.error;
                    return (
                      <tr key={item.id}>
                        <td className="mono">#{item.consecutivo || item.guia_id}</td>
                        <td>{item.guia_cliente || item.nombre || '—'}</td>
                        <td>{fecha(item.fecha_confirmacion)}</td>
                        <td>{item.nombre || '—'}</td>
                        <td className="muted">{item.observaciones || '—'}</td>
                        <td><span className={`tag ${meta.tono}`}>{meta.texto}</span></td>
                        <td><Link className="btn btn-sm" to={`/guia/${item.guia_id}`}>Ver guía</Link></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </section>
      <Toast toast={toast} onClose={closeToast} />
    </AppShell>
  );
}
