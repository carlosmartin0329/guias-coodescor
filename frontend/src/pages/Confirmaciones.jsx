import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import AppShell from '../components/AppShell';
import Icon from '../components/Icon';
import * as guiasApi from '../api/guias';
import { Toast, useToast } from '../components/ui';
import { useAuth } from '../contexts/AuthContext';

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

function estaVencido(item) {
  if (item.estado !== 'pendiente' || !item.expira_en) return false;
  const fechaFin = new Date(item.expira_en);
  return !Number.isNaN(fechaFin.getTime()) && fechaFin.getTime() < Date.now();
}

async function copiarAlPortapapeles(texto) {
  if (!texto) return false;
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(texto);
      return true;
    }
  } catch {
    /* Algunos navegadores bloquean el portapapeles; se usa el respaldo. */
  }
  try {
    const auxiliar = document.createElement('textarea');
    auxiliar.value = texto;
    auxiliar.setAttribute('readonly', '');
    auxiliar.style.position = 'fixed';
    auxiliar.style.opacity = '0';
    document.body.appendChild(auxiliar);
    auxiliar.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(auxiliar);
    return ok;
  } catch {
    return false;
  }
}

export default function Confirmaciones() {
  const { user } = useAuth();
  const rol = user?.rol;
  const esVentas = rol === 'ventas';
  const puedeSincronizar = rol === 'administrativo';
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
      setError(err?.error || 'No se pudieron cargar los tokens.');
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

  const copiarToken = async (item) => {
    const ok = await copiarAlPortapapeles(item.link);
    if (ok) {
      showToast(`Link de la guía #${item.consecutivo || item.guia_id} copiado.`);
    } else {
      setError('El navegador bloqueó el portapapeles. Abre el link y cópialo manualmente.');
    }
  };

  const pendientes = items.filter((c) => c.estado === 'pendiente' && !estaVencido(c)).length;
  const aplicadas = items.filter((c) => c.estado === 'aplicada').length;
  const vencidos = items.filter(estaVencido).length;
  const porRevisar = items.filter((c) => c.estado === 'error').length;

  return (
    <AppShell
      title={esVentas ? 'Tokens de clientes' : 'Confirmaciones y tokens'}
      subtitle="Consulta, verifica y comparte los links de confirmación de tus guías."
      breadcrumb="Tokens clientes"
      actions={(
        <>
          <button type="button" className="btn" onClick={cargar} disabled={sincronizando}>
            <Icon name="refresh" size={15} /> Actualizar
          </button>
          {puedeSincronizar ? (
            <button type="button" className="btn btn-primary" onClick={sincronizar} disabled={sincronizando}>
              <Icon name="download" size={15} /> {sincronizando ? 'Sincronizando…' : 'Sincronizar ahora'}
            </button>
          ) : null}
        </>
      )}
    >
      {error ? <div className="inline-alert" role="alert" style={{ marginBottom: 12 }}><Icon name="alert" size={16} /> {error}</div> : null}

      <div className="kpis" style={{ marginBottom: 14 }}>
        <div className="kpi"><span className="kpi-icon blue"><Icon name="file" size={16} /></span><span className="kpi-label">Tokens registrados</span><b className="kpi-value num">{items.length}</b></div>
        <div className="kpi"><span className="kpi-icon amber"><Icon name="clock" size={16} /></span><span className="kpi-label">Pendientes vigentes</span><b className="kpi-value num">{pendientes}</b></div>
        <div className="kpi"><span className="kpi-icon green"><Icon name="check" size={16} /></span><span className="kpi-label">Aplicados</span><b className="kpi-value num">{aplicadas}</b></div>
        <div className="kpi"><span className="kpi-icon red"><Icon name="alert" size={16} /></span><span className="kpi-label">Vencidos / revisar</span><b className="kpi-value num">{vencidos + porRevisar}</b></div>
      </div>

      <section className="panel">
        <div className="panel-head">
          <div className="panel-title">Tokens de confirmación</div>
          <span className="panel-sub" style={{ marginLeft: 'auto' }}>Vigencia de 7 días · un solo uso</span>
        </div>
        <div className="panel-body">
          <div className="inline-info" style={{ marginBottom: 12 }}>
            <Icon name="check" size={16} />
            <span><strong>Verificar link</strong> abre la misma página que verá el cliente. Si el cliente ya confirmó, el token aparece como <strong>Aplicado</strong>.</span>
          </div>
          {cargando ? <div className="loading-block"><span className="spinner" /> Cargando…</div> : null}
          {!cargando && items.length === 0 ? (
            <p className="nota">Todavía no hay tokens generados. Crea una guía normal y usa el botón Generar link para que aparezcan aquí.</p>
          ) : null}
          {items.length > 0 ? (
            <div className="table-wrap">
              <table className="table">
                <thead>
                  <tr>
                    <th>Guía</th>
                    <th>Cliente</th>
                    <th>Vence</th>
                    <th>Confirmó</th>
                    <th>Recibe</th>
                    <th>Estado</th>
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => {
                    const vencido = estaVencido(item);
                    const meta = vencido ? { texto: 'Vencido', tono: 'neutral' } : (ESTADOS[item.estado] || ESTADOS.error);
                    return (
                      <tr key={item.id}>
                        <td className="mono">#{item.consecutivo || item.guia_id}</td>
                        <td>{item.guia_cliente || item.nombre || '—'}</td>
                        <td className={vencido ? 'muted' : ''}>{fecha(item.expira_en)}</td>
                        <td>{fecha(item.fecha_confirmacion)}</td>
                        <td>{item.nombre || '—'}</td>
                        <td><span className={`tag ${meta.tono}`}>{meta.texto}</span></td>
                        <td>
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                            {item.link ? (
                              <>
                                <button type="button" className="btn btn-sm btn-primary" onClick={() => copiarToken(item)}>
                                  Copiar
                                </button>
                                <a className="btn btn-sm" href={item.link} target="_blank" rel="noreferrer">
                                  Verificar link
                                </a>
                              </>
                            ) : null}
                            <Link className="btn btn-sm" to={`/guia/${item.guia_id}`}>Guía</Link>
                          </div>
                        </td>
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
