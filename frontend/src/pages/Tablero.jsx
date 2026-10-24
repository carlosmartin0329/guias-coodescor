import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useGuias } from '../contexts/GuiaContext';
import { useAuth } from '../contexts/AuthContext';
import * as guiasApi from '../api/guias';
import AppShell from '../components/AppShell';
import Icon from '../components/Icon';
import {
  EmptyState, KpiCard, PageError, StatusPill, Toast, contarPorEstado,
  fechaCorta, hace, useToast, totalGuias,
} from '../components/ui';

const PESTANAS = [
  { clave: '', etiqueta: 'Todas' },
  { clave: 'CREADA', etiqueta: 'Creadas' },
  { clave: 'RECIBIDA_ADMIN', etiqueta: 'Recibidas' },
  { clave: 'EN_CEDIS', etiqueta: 'En CEDIS' },
  { clave: 'EN_RUTA', etiqueta: 'En ruta' },
  { clave: 'ENTREGADA', etiqueta: 'Entregadas' },
  { clave: 'ANULADA', etiqueta: 'Anuladas' },
];

function saludo() {
  const hora = new Date().getHours();
  if (hora < 12) return 'Buenos días';
  if (hora < 19) return 'Buenas tardes';
  return 'Buenas noches';
}

function nombreCorto(usuario) {
  return String(usuario?.nombre || usuario?.usuario || '').split(/\s+/)[0] || '';
}

export default function Tablero() {
  const { user } = useAuth();
  const { guias, conteo, cargando, error, listarGuias, cargarConteo } = useGuias();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { toast, showToast, closeToast } = useToast();

  const [q, setQ] = useState(searchParams.get('q') || '');
  const [estado, setEstado] = useState(searchParams.get('estado') || '');
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refrescando, setRefrescando] = useState(false);
  const [ultimaCarga, setUltimaCarga] = useState(null);
  const [busquedaAplicada, setBusquedaAplicada] = useState(searchParams.get('q') || '');
  const filtrosRef = useRef({ q: '', estado: '' });
  const refrescandoRef = useRef(false);
  const primeraCargaRef = useRef(false);

  useEffect(() => {
    filtrosRef.current = { q: busquedaAplicada, estado };
  }, [busquedaAplicada, estado]);

  // La barra lateral enlaza a /tablero?ver=guias o ?estado=EN_RUTA: mantenemos
  // el estado del filtro sincronizado cuando cambia la URL.
  useEffect(() => {
    const estadoUrl = searchParams.get('estado') || '';
    const qUrl = searchParams.get('q') || '';
    if (estadoUrl !== estado) setEstado(estadoUrl);
    if (qUrl !== q) {
      setQ(qUrl);
      setBusquedaAplicada(qUrl);
    }
    // Solo dependemos de los parámetros: el estado local se actualiza aquí.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const refreshData = useCallback(async (filtros) => {
    if (refrescandoRef.current) return;
    refrescandoRef.current = true;
    setRefrescando(true);
    try {
      const activos = filtros || filtrosRef.current;
      await Promise.all([
        cargarConteo(),
        listarGuias({ q: activos.q, estado: activos.estado }),
      ]);
      setUltimaCarga(new Date());
    } catch (err) {
      console.error('Error al refrescar el tablero:', err);
    } finally {
      refrescandoRef.current = false;
      setRefrescando(false);
      primeraCargaRef.current = true;
    }
  }, [cargarConteo, listarGuias]);

  useEffect(() => {
    refreshData({ q: busquedaAplicada, estado });
    // Solo al montar: los cambios de filtro se piden explícitamente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!autoRefresh) return undefined;
    const intervalo = window.setInterval(() => {
      if (!document.hidden) refreshData();
    }, 4000);
    const alVolver = () => { if (!document.hidden) refreshData(); };
    document.addEventListener('visibilitychange', alVolver);
    return () => {
      window.clearInterval(intervalo);
      document.removeEventListener('visibilitychange', alVolver);
    };
  }, [autoRefresh, refreshData]);

  const aplicarFiltroEstado = (nuevoEstado) => {
    setEstado(nuevoEstado);
    const params = new URLSearchParams(searchParams);
    if (nuevoEstado) params.set('estado', nuevoEstado);
    else params.delete('estado');
    params.delete('ver');
    setSearchParams(params, { replace: true });
    refreshData({ q: busquedaAplicada, estado: nuevoEstado });
  };

  const buscar = (evento) => {
    evento.preventDefault();
    const texto = q.trim();
    setBusquedaAplicada(texto);
    const params = new URLSearchParams(searchParams);
    if (texto) params.set('q', texto);
    else params.delete('q');
    params.delete('ver');
    setSearchParams(params, { replace: true });
    refreshData({ q: texto, estado });
  };

  const exportarCSV = async () => {
    try {
      const blob = await guiasApi.exportarGuias({ q: busquedaAplicada, estado });
      const url = window.URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `guias-${new Date().toISOString().slice(0, 10)}.csv`;
      enlace.click();
      window.URL.revokeObjectURL(url);
      showToast('Exportación completada.');
    } catch (err) {
      showToast(err.error || 'No se pudo exportar el CSV.', 'error');
    }
  };

  const descargarLoadtest = async () => {
    try {
      const blob = await guiasApi.loadtestCSV();
      const url = window.URL.createObjectURL(blob);
      const enlace = document.createElement('a');
      enlace.href = url;
      enlace.download = `loadtest-${new Date().toISOString().slice(0, 10)}.csv`;
      enlace.click();
      window.URL.revokeObjectURL(url);
      showToast('Reporte de load test descargado.');
    } catch (err) {
      showToast(err.error || 'No se pudo descargar el load test.', 'error');
    }
  };

  const abrirGuia = (id) => navigate(`/guia/${id}`);

  const pendientes = contarPorEstado(conteo, 'CREADA') + contarPorEstado(conteo, 'RECIBIDA_ADMIN');
  const enCedis = contarPorEstado(conteo, 'EN_CEDIS');
  const enRuta = contarPorEstado(conteo, 'EN_RUTA');
  const entregadas = contarPorEstado(conteo, 'ENTREGADA');
  const total = totalGuias(conteo);
  const rol = user?.rol || '';

  const tareas = useMemo(() => {
    const lista = [];
    const creadas = contarPorEstado(conteo, 'CREADA');
    const recibidas = contarPorEstado(conteo, 'RECIBIDA_ADMIN');

    if (rol === 'administrativo' || rol === 'admin') {
      if (creadas > 0) lista.push({
        icono: 'clock', tono: 'amber', titulo: `${creadas} guía${creadas === 1 ? '' : 's'} por recibir en bodega`,
        meta: 'Recepción administrativa pendiente', accion: 'Recepcionar', estado: 'CREADA',
      });
      if (recibidas > 0) lista.push({
        icono: 'box', tono: 'indigo', titulo: `${recibidas} guía${recibidas === 1 ? '' : 's'} listas para CEDIS`,
        meta: 'Ya fueron recibidas en bodega', accion: 'Ver recibidas', estado: 'RECIBIDA_ADMIN',
      });
      if (enCedis > 0) lista.push({
        icono: 'truck', tono: 'sky', titulo: `${enCedis} guía${enCedis === 1 ? '' : 's'} en CEDIS`,
        meta: 'Control y despacho pendientes', accion: 'Ver CEDIS', estado: 'EN_CEDIS',
      });
    } else if (rol === 'cedis') {
      if (recibidas > 0) lista.push({
        icono: 'box', tono: 'indigo', titulo: `${recibidas} control${recibidas === 1 ? '' : 'es'} CEDIS pendiente${recibidas === 1 ? '' : 's'}`,
        meta: 'Confirma bultos y firmas', accion: 'Controlar', estado: 'RECIBIDA_ADMIN',
      });
      if (enCedis > 0) lista.push({
        icono: 'truck', tono: 'amber', titulo: `${enCedis} guía${enCedis === 1 ? '' : 's'} lista${enCedis === 1 ? '' : 's'} para despacho`,
        meta: 'Entrega a transportador o cliente', accion: 'Despachar', estado: 'EN_CEDIS',
      });
    } else if (rol === 'transportador') {
      if (enRuta > 0) lista.push({
        icono: 'route', tono: 'indigo', titulo: `${enRuta} entrega${enRuta === 1 ? '' : 's'} en ruta`,
        meta: 'Confirma la entrega con firma del cliente', accion: 'Ver ruta', estado: 'EN_RUTA',
      });
    } else {
      if (pendientes > 0) lista.push({
        icono: 'clock', tono: 'amber', titulo: `${pendientes} guía${pendientes === 1 ? '' : 's'} en proceso`,
        meta: 'Creadas o pendientes de recepción', accion: 'Ver pendientes', estado: '',
      });
      if (enRuta > 0) lista.push({
        icono: 'truck', tono: 'indigo', titulo: `${enRuta} guía${enRuta === 1 ? '' : 's'} en ruta`,
        meta: 'Seguimiento de entregas activas', accion: 'Ver ruta', estado: 'EN_RUTA',
      });
    }
    if (entregadas > 0) lista.push({
      icono: 'check', tono: 'green', titulo: `${entregadas} entrega${entregadas === 1 ? '' : 's'} confirmada${entregadas === 1 ? '' : 's'}`,
      meta: 'Guías cerradas con acta digital', accion: 'Ver entregadas', estado: 'ENTREGADA',
    });
    return lista.slice(0, 3);
  }, [conteo, enCedis, enRuta, entregadas, pendientes, rol]);

  const actividad = useMemo(() => (
    [...guias]
      .sort((a, b) => String(b.creada_en || '').localeCompare(String(a.creada_en || '')))
      .slice(0, 4)
  ), [guias]);

  const puedeExportar = ['admin', 'administrativo'].includes(rol);

  return (
    <AppShell
      title={`${saludo()}, ${nombreCorto(user)}`}
      subtitle={`${new Date().toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })} · ${pendientes + enCedis} tareas requieren atención`}
      actions={(
        <>
          {puedeExportar ? (
            <button type="button" className="btn" onClick={exportarCSV}>
              <Icon name="download" size={15} /> Exportar
            </button>
          ) : null}
          {rol === 'admin' ? (
            <button type="button" className="btn" onClick={descargarLoadtest}>
              <Icon name="chart" size={15} /> Load test
            </button>
          ) : null}
          {rol === 'ventas' ? (
            <button type="button" className="btn btn-primary" onClick={() => navigate('/nueva-guia')}>
              <Icon name="plus" size={15} /> Nueva guía
            </button>
          ) : null}
        </>
      )}
    >
      <div className="tablero">
        {error ? <PageError message={error} onRetry={() => refreshData()} /> : null}

        <div className="kpis" aria-label="Resumen de guías">
          <KpiCard
            label="Por atender"
            value={pendientes}
            icon="clock"
            tone="amber"
            foot={<>Incluye creadas y recibidas</>}
            onClick={() => aplicarFiltroEstado('CREADA')}
          />
          <KpiCard
            label="En CEDIS"
            value={enCedis}
            icon="box"
            tone="indigo"
            foot={<>Control y despacho</>}
            onClick={() => aplicarFiltroEstado('EN_CEDIS')}
          />
          <KpiCard
            label="En ruta"
            value={enRuta}
            icon="truck"
            tone="sky"
            foot={<>Entregas activas</>}
            onClick={() => aplicarFiltroEstado('EN_RUTA')}
          />
          <KpiCard
            label="Entregadas"
            value={entregadas}
            icon="check"
            tone="green"
            foot={<>Total histórico</>}
            onClick={() => aplicarFiltroEstado('ENTREGADA')}
          />
        </div>

        <div className="dashboard">
          <div className="dashboard-main">
            <section className="panel" aria-label="Mi trabajo de hoy">
              <div className="panel-head">
                <div>
                  <div className="panel-title">Mi trabajo de hoy</div>
                  <div className="panel-sub">Priorizado por estado y pendientes de tu rol</div>
                </div>
                <button type="button" className="link" style={{ marginLeft: 'auto' }} onClick={() => aplicarFiltroEstado('')}>
                  Ver todas
                </button>
              </div>
              <div className="panel-body">
                {tareas.length === 0 ? (
                  <EmptyState title="Todo al día" detail="No tienes tareas pendientes por ahora." />
                ) : (
                  <div className="tasks">
                    {tareas.map((tarea) => (
                      <div className="task" key={`${tarea.titulo}-${tarea.estado}`}>
                        <span className={`task-ico ${tarea.tono}`}>
                          <Icon name={tarea.icono} size={18} />
                        </span>
                        <div className="task-main grow">
                          <div className="task-title">{tarea.titulo}</div>
                          <div className="task-meta">{tarea.meta}</div>
                        </div>
                        <div className="task-action">
                          <button type="button" className="btn btn-sm btn-primary" onClick={() => aplicarFiltroEstado(tarea.estado)}>
                            {tarea.accion}
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="panel" aria-label="Listado de guías">
              <div className="toolbar">
                <div className="seg" role="tablist" aria-label="Filtrar por estado">
                  {PESTANAS.map((pestana) => {
                    const cantidad = pestana.clave ? contarPorEstado(conteo, pestana.clave) : total;
                    return (
                      <button
                        key={pestana.clave || 'todas'}
                        type="button"
                        role="tab"
                        aria-selected={estado === pestana.clave}
                        className={estado === pestana.clave ? 'active' : ''}
                        onClick={() => aplicarFiltroEstado(pestana.clave)}
                      >
                        {pestana.etiqueta}
                        <span className="pill-count">{cantidad}</span>
                      </button>
                    );
                  })}
                </div>
                <div className="toolbar-right">
                  <form className="field" onSubmit={buscar} role="search">
                    <Icon name="search" size={15} />
                    <input
                      value={q}
                      onChange={(e) => setQ(e.target.value)}
                      placeholder="Buscar por cliente, ciudad o documento…"
                      aria-label="Buscar guías"
                    />
                  </form>
                  <button type="submit" className="btn btn-sm" onClick={buscar}>Buscar</button>
                  <button
                    type="button"
                    className={`auto-toggle ${autoRefresh ? 'on' : ''}`.trim()}
                    onClick={() => setAutoRefresh((valor) => !valor)}
                    title={autoRefresh ? 'Actualización automática activa' : 'Actualización manual'}
                  >
                    <Icon name="refresh" size={13} />
                    {autoRefresh ? 'Auto' : 'Manual'}
                  </button>
                  {refrescando ? <span className="updated-at">Actualizando…</span> : null}
                  {ultimaCarga && !refrescando ? (
                    <span className="updated-at">
                      {ultimaCarga.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  ) : null}
                </div>
              </div>

              {!primeraCargaRef.current && cargando ? (
                <div className="loading-block"><span className="spinner" /> Cargando guías…</div>
              ) : guias.length === 0 ? (
                <EmptyState
                  title="No hay guías con este filtro"
                  detail="Prueba con otro estado o limpia la búsqueda."
                  action={(
                    <button type="button" className="btn btn-sm" onClick={() => aplicarFiltroEstado('')}>
                      Ver todas
                    </button>
                  )}
                />
              ) : (
                <>
                  <div className="table-wrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Guía</th>
                          <th>Cliente</th>
                          <th>Ciudad</th>
                          <th>Estado</th>
                          <th>Creada</th>
                          <th aria-label="Acciones" />
                        </tr>
                      </thead>
                      <tbody>
                        {guias.map((guia) => (
                          <tr
                            key={guia.id}
                            className="clickable"
                            tabIndex={0}
                            onClick={() => abrirGuia(guia.id)}
                            onKeyDown={(evento) => {
                              if (evento.key === 'Enter' || evento.key === ' ') {
                                evento.preventDefault();
                                abrirGuia(guia.id);
                              }
                            }}
                            aria-label={`Abrir guía ${guia.consecutivo || guia.id}`}
                          >
                            <td>
                              <span className="guia-id">#{guia.consecutivo || guia.id}</span>
                            </td>
                            <td className="guia-cliente">{guia.cliente}</td>
                            <td className="guia-ciudad">{guia.ciudad || '—'}</td>
                            <td><StatusPill estado={guia.estado} /></td>
                            <td><span className="age">{fechaCorta(guia.creada_en)}</span></td>
                            <td>
                              <div className="row-action">
                                <button
                                  type="button"
                                  className="btn btn-sm"
                                  onClick={(evento) => { evento.stopPropagation(); abrirGuia(guia.id); }}
                                >
                                  Abrir <Icon name="chevronRight" size={13} />
                                </button>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="cards-movil">
                    {guias.map((guia) => (
                      <article className="guia-card" key={`card-${guia.id}`}>
                        <div className="guia-card-top">
                          <span className="mono">#{guia.consecutivo || guia.id}</span>
                          <StatusPill estado={guia.estado} />
                        </div>
                        <div className="guia-card-title">{guia.cliente}</div>
                        <div className="guia-card-meta">
                          <Icon name="mapPin" size={13} /> {guia.ciudad || '—'}
                          <span aria-hidden="true">·</span>
                          <Icon name="clock" size={13} /> {fechaCorta(guia.creada_en)}
                        </div>
                        <div className="guia-card-actions">
                          <button type="button" className="btn btn-sm btn-primary grow" onClick={() => abrirGuia(guia.id)}>
                            Abrir guía
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                </>
              )}
            </section>
          </div>

          <aside className="dashboard-rail">
            <section className="panel">
              <div className="panel-head">
                <div className="panel-title">Actividad reciente</div>
                <button type="button" className="link" style={{ marginLeft: 'auto' }} onClick={() => aplicarFiltroEstado('')}>
                  Ver todo
                </button>
              </div>
              <div className="panel-body">
                {actividad.length === 0 ? (
                  <p className="nota">Aún no hay actividad registrada.</p>
                ) : (
                  <div className="timeline">
                    {actividad.map((guia) => (
                      <button
                        type="button"
                        key={`act-${guia.id}`}
                        className="tl-item"
                        style={{ border: 0, background: 'transparent', textAlign: 'left', width: '100%', cursor: 'pointer' }}
                        onClick={() => abrirGuia(guia.id)}
                      >
                        <span className={`tl-dot ${guia.estado === 'ENTREGADA' ? 'ok' : guia.estado === 'EN_RUTA' ? 'run' : ''}`.trim()}>
                          <Icon name={guia.estado === 'ENTREGADA' ? 'check' : guia.estado === 'EN_RUTA' ? 'truck' : 'box'} size={13} />
                        </span>
                        <span className="tl-body">
                          <span className="tl-title">Guía #{guia.consecutivo || guia.id}</span>
                          <span className="tl-meta">{guia.cliente}</span>
                        </span>
                        <span className="tl-time">{hace(guia.creada_en)}</span>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </section>

            <section className="panel">
              <div className="panel-head"><div className="panel-title">Resumen del día</div></div>
              <div className="panel-body">
                <div className="summary-row"><span>Guías registradas</span><b className="num">{total}</b></div>
                <div className="summary-row"><span>Por atender</span><b className="num">{pendientes}</b></div>
                <div className="summary-row"><span>En CEDIS</span><b className="num">{enCedis}</b></div>
                <div className="summary-row"><span>En ruta</span><b className="num">{enRuta}</b></div>
                <div className="summary-row"><span>Entregadas</span><b className="num">{entregadas}</b></div>
                <div className="summary-row"><span>Anuladas</span><b className="num">{contarPorEstado(conteo, 'ANULADA')}</b></div>
              </div>
            </section>

            <section className="panel">
              <div className="panel-body suggestion">
                <div className="hstack" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="kpi-icon indigo"><Icon name="sparkles" size={15} /></span>
                  <div>
                    <div className="panel-title">Siguiente paso</div>
                    <div className="panel-sub">Según el estado de tu operación</div>
                  </div>
                </div>
                <p>
                  {enCedis > 0
                    ? `Hay ${enCedis} guía${enCedis === 1 ? '' : 's'} en CEDIS. Prioriza el control para no retrasar la ruta.`
                    : 'No hay guías en CEDIS. Revisa las pendientes de recepción o crea una guía nueva.'}
                </p>
                <button type="button" className="btn btn-sm btn-primary btn-block" onClick={() => aplicarFiltroEstado(enCedis > 0 ? 'EN_CEDIS' : 'CREADA')}>
                  {enCedis > 0 ? 'Ver guías en CEDIS' : 'Ver pendientes'}
                </button>
              </div>
            </section>
          </aside>
        </div>
      </div>
      <Toast toast={toast} onClose={closeToast} />
    </AppShell>
  );
}
