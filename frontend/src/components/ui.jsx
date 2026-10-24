import { useCallback, useEffect, useState } from 'react';
import Icon from './Icon';

export const ESTADOS = {
  CREADA: { etiqueta: 'Creada', tono: 'creada' },
  RECIBIDA_ADMIN: { etiqueta: 'Recibida', tono: 'recibida' },
  EN_CEDIS: { etiqueta: 'En CEDIS', tono: 'cedis' },
  EN_RUTA: { etiqueta: 'En ruta', tono: 'ruta' },
  ENTREGADA: { etiqueta: 'Entregada', tono: 'entregada' },
  ANULADA: { etiqueta: 'Anulada', tono: 'anulada' },
};

export const TITULOS_EVENTO = {
  creacion: 'Guía creada',
  recepcion_admin: 'Recepción administrativa',
  control_cedis: 'Control CEDIS',
  entrega_transporte: 'Entrega a transportador',
  entrega_cliente: 'Entrega al cliente',
  anular: 'Anulación',
  editar_guia: 'Edición de datos',
  asignacion_transportador: 'Asignación de transportador',
};

export function StatusPill({ estado, className = '' }) {
  const info = ESTADOS[estado] || { etiqueta: estado || '—', tono: 'anulada' };
  return (
    <span className={`status ${info.tono} ${className}`.trim()}>
      {info.etiqueta}
    </span>
  );
}

export function KpiCard({ label, value, icon, tone = 'indigo', foot, onClick }) {
  const Tag = onClick ? 'button' : 'div';
  return (
    <Tag
      type={onClick ? 'button' : undefined}
      className={`kpi ${onClick ? 'kpi-click' : ''}`.trim()}
      onClick={onClick}
    >
      <span className="kpi-top">
        <span className="kpi-label">{label}</span>
        <span className={`kpi-icon ${tone}`}>
          <Icon name={icon} size={15} />
        </span>
      </span>
      <span className="kpi-value num">{value}</span>
      {foot ? <span className="kpi-foot">{foot}</span> : null}
    </Tag>
  );
}

export function EmptyState({ title, detail, action }) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon name="box" size={22} />
      </span>
      <strong>{title}</strong>
      {detail ? <p>{detail}</p> : null}
      {action}
    </div>
  );
}

export function PageError({ message, onRetry }) {
  return (
    <div className="page-error" role="alert">
      <Icon name="alert" size={19} />
      <div className="grow">
        <strong>No se pudo cargar la información</strong>
        <p>{message || 'Revisa la conexión e inténtalo de nuevo.'}</p>
      </div>
      {onRetry ? (
        <button type="button" className="btn btn-sm" onClick={onRetry}>
          <Icon name="refresh" size={14} /> Reintentar
        </button>
      ) : null}
    </div>
  );
}

export function Spinner({ label = 'Cargando…' }) {
  return (
    <div className="loading-block" role="status">
      <span className="spinner" aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function Toast({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return undefined;
    const timer = window.setTimeout(onClose, toast.duration || 4200);
    return () => window.clearTimeout(timer);
  }, [toast, onClose]);

  if (!toast) return null;
  return (
    <div className={`app-toast ${toast.tipo || 'success'}`} role="status">
      <span className="app-toast-icon">
        <Icon name={toast.tipo === 'error' ? 'alert' : 'check'} size={16} />
      </span>
      <span className="grow">{toast.mensaje}</span>
      <button type="button" className="app-toast-close" onClick={onClose} aria-label="Cerrar aviso">
        <Icon name="x" size={14} />
      </button>
    </div>
  );
}

export function useToast() {
  const [toast, setToast] = useState(null);
  const showToast = useCallback((mensaje, tipo = 'success', duration = 4200) => {
    setToast({ mensaje, tipo, duration, id: Date.now() });
  }, []);
  const closeToast = useCallback(() => setToast(null), []);
  return { toast, showToast, closeToast };
}

export function fechaCorta(valor) {
  if (!valor) return '—';
  const fecha = new Date(String(valor).replace(' ', 'T'));
  if (Number.isNaN(fecha.getTime())) return String(valor);
  return fecha.toLocaleDateString('es-CO', { day: '2-digit', month: 'short' });
}

export function fechaHora(valor) {
  if (!valor) return '—';
  const fecha = new Date(String(valor).replace(' ', 'T'));
  if (Number.isNaN(fecha.getTime())) return String(valor);
  return fecha.toLocaleString('es-CO', {
    day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

export function hace(valor) {
  if (!valor) return '—';
  const fecha = new Date(String(valor).replace(' ', 'T'));
  if (Number.isNaN(fecha.getTime())) return '—';
  const minutos = Math.max(0, Math.floor((Date.now() - fecha.getTime()) / 60000));
  if (minutos < 1) return 'ahora';
  if (minutos < 60) return `hace ${minutos} min`;
  const horas = Math.floor(minutos / 60);
  if (horas < 24) return `hace ${horas} h`;
  const dias = Math.floor(horas / 24);
  return dias === 1 ? 'ayer' : `hace ${dias} días`;
}

export function contarPorEstado(conteo, estado) {
  const fila = (conteo || []).find((item) => item.estado === estado);
  return Number(fila?.n ?? fila?.total ?? 0) || 0;
}

export function totalGuias(conteo) {
  return (conteo || []).reduce(
    (total, item) => total + (Number(item?.n ?? item?.total ?? 0) || 0),
    0,
  );
}
