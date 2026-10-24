import { useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useNotificaciones } from '../hooks/useNotificaciones';
import Icon from './Icon';
import { StatusPill } from './ui';

const TEMA_KEY = 'guias.tema';

function leerTema() {
  try {
    return window.localStorage.getItem(TEMA_KEY) === 'dark' ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

function iniciales(nombre) {
  const partes = String(nombre || 'Usuario').trim().split(/\s+/).filter(Boolean);
  const letras = partes.slice(0, 2).map((p) => p[0]);
  return (letras.join('') || 'U').toUpperCase();
}

export default function AppShell({
  children, title, subtitle, actions, breadcrumb, activeNav, sinPageHead = false,
}) {
  const { user, logout } = useAuth();
  const { count, hasNew, nuevasGuias, markAllAsRead, markGuiaAsRead } = useNotificaciones();
  const navigate = useNavigate();
  const location = useLocation();
  const [tema, setTema] = useState(leerTema);
  const [busqueda, setBusqueda] = useState('');
  const [notiAbiertas, setNotiAbiertas] = useState(false);
  const notiRef = useRef(null);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', tema);
    try {
      window.localStorage.setItem(TEMA_KEY, tema);
    } catch {
      /* sin persistencia: el tema sigue funcionando en la sesión */
    }
  }, [tema]);

  useEffect(() => {
    const cerrar = (evento) => {
      if (notiRef.current && !notiRef.current.contains(evento.target)) {
        setNotiAbiertas(false);
      }
    };
    document.addEventListener('mousedown', cerrar);
    return () => document.removeEventListener('mousedown', cerrar);
  }, []);

  const rol = user?.rol || '';
  const esAdmin = rol === 'admin';
  const esVentas = rol === 'ventas';
  const params = new URLSearchParams(location.search);
  const vista = params.get('vista') || 'jornada';
  const buscandoGuias = vista === 'guias';
  const enRuta = vista === 'ruta';

  const nav = useMemo(() => {
    const items = [
      { key: 'jornada', to: '/tablero', label: 'Mi jornada', icon: 'grid', activo: vista === 'jornada' && location.pathname === '/tablero' },
      { key: 'guias', to: '/tablero?vista=guias', label: 'Guías', icon: 'box', activo: buscandoGuias, badge: count },
      { key: 'ruta', to: '/tablero?vista=ruta', label: 'En ruta', icon: 'route', activo: enRuta },
    ];
    if (esVentas) {
      items.push({ key: 'nueva', to: '/nueva-guia', label: 'Nueva guía', icon: 'plus', activo: location.pathname === '/nueva-guia' });
    }
    return items;
  }, [buscandoGuias, enRuta, location.pathname, count, esVentas, vista]);

  const adminNav = [
    { key: 'db', to: '/admin/db', label: 'Base de datos', icon: 'database' },
    { key: 'loadtest', to: '/admin/loadtest', label: 'Load test', icon: 'chart' },
  ];

  const salir = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const buscar = (evento) => {
    evento.preventDefault();
    const texto = busqueda.trim();
    navigate(texto ? `/tablero?q=${encodeURIComponent(texto)}` : '/tablero');
  };

  const irANotificacion = (noti) => {
    markGuiaAsRead(noti.id);
    setNotiAbiertas(false);
    navigate(`/guia/${noti.guia_id}`);
  };

  const tituloActual = breadcrumb || title || 'Mi jornada';
  const crumbFinal = typeof tituloActual === 'string' ? tituloActual : 'Detalle';

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Navegación principal">
        <Link to="/tablero" className="brand" aria-label="Ir al tablero">
          <span className="brand-mark">GC</span>
          <span className="brand-text">
            <h1 className="brand-name">Guías Coodescor</h1>
            <span className="brand-sub">Operación logística</span>
          </span>
        </Link>

        <nav className="nav-group">
          <span className="nav-label">Trabajo</span>
          {nav.map((item) => (
            <Link
              key={item.key}
              to={item.to}
              className={`nav-item ${item.activo && activeNav !== 'otro' ? 'active' : ''}`.trim()}
            >
              <Icon name={item.icon} size={18} />
              <span className="grow">{item.label}</span>
              {item.badge ? <span className="nav-badge">{item.badge}</span> : null}
            </Link>
          ))}
        </nav>

        {esAdmin ? (
          <nav className="nav-group">
            <span className="nav-label">Administración</span>
            {adminNav.map((item) => (
              <Link
                key={item.key}
                to={item.to}
                className={`nav-item ${activeNav === item.key ? 'active' : ''}`.trim()}
              >
                <Icon name={item.icon} size={18} />
                <span className="grow">{item.label}</span>
              </Link>
            ))}
          </nav>
        ) : null}

        <div className="sidebar-foot">
          <div className="user-card">
            <span className="avatar">{iniciales(user?.nombre || user?.usuario)}</span>
            <span className="grow user-meta">
              <span className="user-name">{user?.nombre || user?.usuario}</span>
              <span className="user-role">{rol || 'usuario'}</span>
            </span>
            <button type="button" className="icon-btn ghost" onClick={salir} title="Cerrar sesión">
              <Icon name="logout" size={17} />
              <span className="sr-only">Salir</span>
            </button>
          </div>
          <button type="button" className="btn btn-ghost salir-movil" onClick={salir}>
            <Icon name="logout" size={15} /> Salir
          </button>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <span className="brand-mark mobile-brand" aria-hidden="true">GC</span>
          <div className="crumb">
            <Icon name="home" size={14} />
            <span>{crumbFinal}</span>
          </div>

          <form className="topbar-search" onSubmit={buscar} role="search">
            <Icon name="search" size={16} />
            <input
              value={busqueda}
              onChange={(e) => setBusqueda(e.target.value)}
              placeholder="Buscar guía, cliente o documento…"
              aria-label="Buscar guía, cliente o documento"
            />
            <kbd>Enter</kbd>
          </form>

          <button
            type="button"
            className="icon-btn"
            onClick={() => setTema((actual) => (actual === 'dark' ? 'light' : 'dark'))}
            title={tema === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
            aria-label={tema === 'dark' ? 'Cambiar a tema claro' : 'Cambiar a tema oscuro'}
          >
            <Icon name={tema === 'dark' ? 'sun' : 'moon'} size={17} />
          </button>

          <div className="noti-wrap" ref={notiRef}>
            <button
              type="button"
              className="icon-btn"
              onClick={() => setNotiAbiertas((abierta) => !abierta)}
              aria-expanded={notiAbiertas}
              aria-label={`Notificaciones: ${count} pendientes`}
              title="Notificaciones"
            >
              <Icon name="bell" size={17} />
              {count > 0 ? <span className={`dot ${hasNew ? 'pulse' : ''}`.trim()} /> : null}
            </button>
            {notiAbiertas ? (
              <div className="noti-dropdown">
                <div className="noti-head">
                  <strong>Notificaciones</strong>
                  {nuevasGuias.length ? (
                    <button type="button" className="link" onClick={markAllAsRead}>
                      Marcar leídas
                    </button>
                  ) : null}
                </div>
                <div className="noti-list">
                  {nuevasGuias.length === 0 ? (
                    <p className="noti-empty">No tienes notificaciones pendientes.</p>
                  ) : (
                    nuevasGuias.slice(0, 8).map((noti) => (
                      <button
                        type="button"
                        key={noti.id}
                        className="noti-item"
                        onClick={() => irANotificacion(noti)}
                      >
                        <span className="noti-main">
                          <strong>Guía #{noti.consecutivo || noti.guia_id}</strong>
                          <span>{noti.cliente}</span>
                        </span>
                        <StatusPill estado={noti.estado} />
                      </button>
                    ))
                  )}
                </div>
              </div>
            ) : null}
          </div>

          <span className="avatar avatar-top">{iniciales(user?.nombre || user?.usuario)}</span>
        </header>

        <main className="page">
          {!sinPageHead && (title || actions) ? (
            <div className="page-head">
              <div className="page-head-text">
                <h2 className="page-title">{title}</h2>
                {subtitle ? <p className="page-sub">{subtitle}</p> : null}
              </div>
              {actions ? <div className="page-actions">{actions}</div> : null}
            </div>
          ) : null}
          {children}
        </main>
      </div>

      <nav className="bottom-nav" aria-label="Navegación móvil">
        {nav.map((item) => (
          <Link key={item.key} to={item.to} className={`bn-item ${item.activo ? 'active' : ''}`.trim()}>
            <Icon name={item.icon} size={20} />
            <span>{item.label === 'Mi jornada' ? 'Jornada' : item.label}</span>
          </Link>
        ))}
        {esAdmin ? (
          <Link to="/admin/db" className={`bn-item ${activeNav === 'db' ? 'active' : ''}`.trim()}>
            <Icon name="database" size={20} />
            <span>BD</span>
          </Link>
        ) : (
          <button type="button" className="bn-item" onClick={salir}>
            <Icon name="logout" size={20} />
            <span>Salir</span>
          </button>
        )}
      </nav>
    </div>
  );
}
