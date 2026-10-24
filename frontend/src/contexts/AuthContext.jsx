import { createContext, useContext, useState, useEffect } from 'react';
import * as authApi from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // Arranca en true: hasta comprobar la cookie de sesión no se puede decidir si
  // redirigir a /login. Antes era false y cada recarga/deep-link expulsaba al
  // usuario aunque su sesión siguiera válida.
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let vivo = true;
    (async () => {
      try {
        const data = await authApi.session();
        if (vivo) setUser(data?.usuario || null);
      } catch {
        if (vivo) setUser(null);
      } finally {
        if (vivo) setLoading(false);
      }
    })();
    return () => { vivo = false; };
  }, []);

  const login = async (credenciales) => {
    const data = await authApi.login(credenciales);
    let usuario = data?.usuario || null;
    if (!usuario && data?.ok) {
      // Compatibilidad con un backend anterior que no devolvía el usuario.
      try {
        const sesion = await authApi.session();
        usuario = sesion?.usuario || null;
      } catch {
        usuario = null;
      }
    }
    setUser(usuario);
    return data;
  };

  const logout = async () => {
    try {
      await authApi.logout();
    } finally {
      // Aunque el servidor falle, el estado local debe quedar cerrado.
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth debe usarse dentro de AuthProvider');
  return context;
}
