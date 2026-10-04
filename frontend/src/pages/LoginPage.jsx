import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import * as authApi from '../api/auth';
import './Login.css';

export default function LoginPage() {
  const [usuario, setUsuario] = useState('');
  const [clave, setClave] = useState('');
  const [captcha, setCaptcha] = useState('');
  const [captchaToken, setCaptchaToken] = useState('');
  const [svg, setSvg] = useState('');
  const [error, setError] = useState('');
  const [cargando, setCargando] = useState(false);
  const navigate = useNavigate();

  const cargarCaptcha = async () => {
    const data = await authApi.captchaNuevo();
    setSvg(data.svg);
    setCaptchaToken(data.token);
    setCaptcha('');
  };

  useEffect(() => {
    cargarCaptcha();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setCargando(true);
    setError('');
    try {
      const data = await authApi.login({
        usuario,
        clave,
        captcha_token: captchaToken,
        captcha_respuesta: captcha,
      });
      if (data.ok) {
        navigate('/tablero');
      } else {
        setError(data.error || 'Credenciales incorrectas');
        cargarCaptcha();
      }
    } catch (err) {
      setError(err.error || 'Error al iniciar sesión');
      cargarCaptcha();
    } finally {
      setCargando(false);
    }
  };

  return (
    <div className="login-container">
      <form className="login-card" onSubmit={handleSubmit}>
        <h1>Guías Coodescor</h1>
        {error && <div className="error">{error}</div>}
        <label>
          Usuario
          <input value={usuario} onChange={(e) => setUsuario(e.target.value)} required />
        </label>
        <label>
          Contraseña
          <input type="password" value={clave} onChange={(e) => setClave(e.target.value)} required />
        </label>
        <div className="captcha">
          <div className="captcha-img" dangerouslySetInnerHTML={{ __html: svg }} />
          <button type="button" onClick={cargarCaptcha} title="Otro código">⟳</button>
        </div>
        <label>
          Código CAPTCHA
          <input value={captcha} onChange={(e) => setCaptcha(e.target.value.toUpperCase())} required maxLength={6} />
        </label>
        <button type="submit" disabled={cargando}>
          {cargando ? 'Entrando…' : 'Entrar'}
        </button>
      </form>
    </div>
  );
}
