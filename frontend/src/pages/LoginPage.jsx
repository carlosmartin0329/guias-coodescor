import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import * as authApi from '../api/auth';
import { useAuth } from '../contexts/AuthContext';
import './Login.css';

export default function LoginPage() {
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [captcha, setCaptcha] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [svg, setSvg] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const [cargandoCaptcha, setCargandoCaptcha] = useState(false);
  const peticionRef = useRef(0);
  const navigate = useNavigate();
  const { login } = useAuth();

  const cargarCaptcha = async () => {
    const peticion = ++peticionRef.current;
    setCargandoCaptcha(true);
    try {
      const data = await authApi.captchaNuevo();
      // Ignora respuestas viejas: dos clics rápidos podían dejar el SVG de una
      // petición con el token de otra.
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

  useEffect(() => {
    cargarCaptcha();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setCargando(true);
    setError('');
    try {
      const data = await login({
        usuario,
        clave,
        captcha_token: captchaToken,
        captcha_respuesta: captcha,
      });
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
    <div className="login-container">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Guías Coodescor</h1>
        {error && <div className="error" role="alert">{error}</div>}
        <label htmlFor="login-usuario">
          Usuario
          <input
            id="login-usuario"
            name="usuario"
            autoComplete="username"
            value={usuario}
            onChange={(e) => setUsuario(e.target.value)}
            required
          />
        </label>
        <label htmlFor="login-clave">
          Contraseña
          <input
            id="login-clave"
            name="clave"
            type="password"
            autoComplete="current-password"
            value={clave}
            onChange={(e) => setClave(e.target.value)}
            required
          />
        </label>
        <div className="captcha">
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
            onClick={cargarCaptcha}
            title="Otro código"
            aria-label="Generar otro CAPTCHA"
            disabled={cargandoCaptcha}
          >
            ⟳
          </button>
        </div>
        <label htmlFor="login-captcha">
          Código CAPTCHA
          <input
            id="login-captcha"
            name="captcha"
            autoComplete="off"
            value={captcha}
            onChange={(e) => setCaptcha(e.target.value.toUpperCase())}
            required
            maxLength={6}
          />
        </label>
        <button type="submit" disabled={cargando || !captchaToken}>
          {cargando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
