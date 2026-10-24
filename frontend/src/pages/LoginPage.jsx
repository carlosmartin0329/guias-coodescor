import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import * as authApi from '../api/auth';
import { useAuth } from '../contexts/AuthContext';
import Icon from '../components/Icon';

export default function LoginPage() {
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [captcha, setCaptcha] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [svg, setSvg] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const [cargandoCaptcha, setCargandoCaptcha] = useState(false);
  const [verClave, setVerClave] = useState(false);
  const peticionRef = useRef(0);
  const navigate = useNavigate();
  const { login } = useAuth();

  const cargarCaptcha = async () => {
    const peticion = ++peticionRef.current;
    setCargandoCaptcha(true);
    try {
      const data = await authApi.captchaNuevo();
      if (peticion !== peticionRef.current) return;
      setSvg(data?.svg || '');
      setCaptchaToken(data?.token || '');
      setCaptcha('');
      setError((prev) => (prev && prev.includes('CAPTCHA') ? '' : prev));
    } catch (err) {
      if (peticion === peticionRef.current) {
        setError(err?.error || 'No se pudo cargar el CAPTCHA. Revisa la conexión.');
      }
    } finally {
      if (peticion === peticionRef.current) setCargandoCaptcha(false);
    }
  };

  useEffect(() => { cargarCaptcha(); }, []);

  const handleSubmit = async (evento) => {
    evento.preventDefault();
    setCargando(true);
    setError('');
    try {
      const data = await login({ usuario, clave, captcha_token: captchaToken, captcha_respuesta: captcha });
      if (data?.ok) {
        navigate('/tablero', { replace: true });
      } else {
        setError(data?.error || 'Credenciales incorrectas');
        cargarCaptcha();
      }
    } catch (err) {
      setError(err?.error || 'Error al iniciar sesión');
      cargarCaptcha();
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="login-wrap">
      <section className="login-brand" aria-label="Guías Coodescor">
        <div className="login-brand-inner">
          <div className="login-logo">
            <span className="brand-mark">GC</span>
            <h1>Guías Coodescor</h1>
          </div>
          <p className="login-h">La operación de tus guías, clara y bajo control.</p>
          <p className="login-p">
            Crea, controla y entrega guías desde el computador o el celular.
            Firmas digitales, trazabilidad completa y confirmación del cliente sin instalar nada.
          </p>
          <div className="login-stats">
            <div className="login-stat"><b>100 %</b><span>Trazabilidad por evento</span></div>
            <div className="login-stat"><b>&lt; 30 s</b><span>Confirmación del cliente</span></div>
            <div className="login-stat"><b>Local</b><span>Sistema sin nube</span></div>
          </div>
        </div>
      </section>

      <section className="login-form-side">
        <form className="login-card2" onSubmit={handleSubmit}>
          <div className="login-mobile-brand">
            <span className="brand-mark">GC</span>
            <span>Guías Coodescor</span>
          </div>
          <h2>Inicia sesión</h2>
          <p className="sub">Ingresa con las credenciales asignadas por el administrador.</p>

          {error ? <div className="error login-error" role="alert">{error}</div> : null}

          <div className="login-field">
            <label className="lbl" htmlFor="login-usuario">Usuario</label>
            <input
              id="login-usuario"
              className="input"
              name="usuario"
              autoComplete="username"
              value={usuario}
              onChange={(e) => setUsuario(e.target.value)}
              required
            />
          </div>

          <div className="login-field">
            <label className="lbl" htmlFor="login-clave">Contraseña</label>
            <div style={{ position: 'relative' }}>
              <input
                id="login-clave"
                className="input"
                name="clave"
                type={verClave ? 'text' : 'password'}
                autoComplete="current-password"
                value={clave}
                onChange={(e) => setClave(e.target.value)}
                required
                style={{ paddingRight: 42 }}
              />
              <button
                type="button"
                className="icon-btn ghost"
                style={{ position: 'absolute', right: 4, top: 4, width: 30, height: 30, minHeight: 30 }}
                onClick={() => setVerClave((valor) => !valor)}
                aria-label={verClave ? 'Ocultar contraseña' : 'Mostrar contraseña'}
              >
                <Icon name="eye" size={16} />
              </button>
            </div>
          </div>

          <div className="login-field">
            <label className="lbl" htmlFor="login-captcha">Código CAPTCHA</label>
            <div className="captcha-row">
              {svg ? (
                <div
                  className="captcha-img"
                  aria-label="Imagen CAPTCHA"
                  dangerouslySetInnerHTML={{ __html: svg }}
                />
              ) : (
                <div className="captcha-img captcha-vacio">
                  {cargandoCaptcha ? 'Cargando CAPTCHA…' : 'CAPTCHA no disponible'}
                </div>
              )}
              <button
                type="button"
                className="btn captcha-refresh"
                onClick={cargarCaptcha}
                title="Otro código"
                aria-label="Generar otro CAPTCHA"
                disabled={cargandoCaptcha}
              >
                <Icon name="refresh" size={16} />
              </button>
            </div>
            <input
              id="login-captcha"
              className="input mt-2"
              name="captcha"
              autoComplete="off"
              value={captcha}
              onChange={(e) => setCaptcha(e.target.value.toUpperCase())}
              required
              maxLength={6}
              placeholder="Escribe el código"
            />
            <span className="hint">Escribe las 6 letras o números tal como aparecen en la imagen.</span>
          </div>

          <button type="submit" className="btn btn-primary btn-block" style={{ minHeight: 44, marginTop: 8 }} disabled={cargando || !captchaToken}>
            {cargando ? 'Entrando…' : 'Entrar'}
          </button>

          <div className="login-foot">
            <Icon name="shield" size={14} /> Conexión local segura · Sesión de 8 horas
          </div>
        </form>
      </section>
    </div>
  );
}
