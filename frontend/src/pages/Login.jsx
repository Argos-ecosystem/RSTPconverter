import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [checkingSetup, setCheckingSetup] = useState(true);
  const [setupRequired, setSetupRequired] = useState(false);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    api.auth
      .status()
      .then((res) => setSetupRequired(res.setup_required))
      .catch(() => setError("No se pudo contactar al servicio. Verifica que el backend este corriendo."))
      .finally(() => setCheckingSetup(false));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");

    if (setupRequired && password !== confirmPassword) {
      setError("Las contrasenas no coinciden");
      return;
    }

    setSubmitting(true);
    try {
      const res = setupRequired
        ? await api.auth.setup(username, password)
        : await api.auth.login(username, password);
      login(res.access_token);
      navigate("/");
    } catch (err) {
      setError(err.message || "No se pudo iniciar sesion");
    } finally {
      setSubmitting(false);
    }
  }

  if (checkingSetup) {
    return (
      <div className="login-shell">
        <div className="login-card">Cargando...</div>
      </div>
    );
  }

  return (
    <div className="login-shell">
      <div className="login-card">
        <h1>{setupRequired ? "Crear usuario admin" : "Iniciar sesion"}</h1>
        <p className="subtitle">
          {setupRequired
            ? "Este equipo local todavia no tiene un administrador. Crea las credenciales de acceso."
            : "RSTP Converter - panel de administracion local"}
        </p>

        {error ? <div className="banner error">{error}</div> : null}

        <form onSubmit={handleSubmit}>
          <div className="field">
            <label htmlFor="username">Usuario</label>
            <input
              id="username"
              type="text"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="password">Contrasena</label>
            <input
              id="password"
              type="password"
              autoComplete={setupRequired ? "new-password" : "current-password"}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              minLength={setupRequired ? 8 : undefined}
              required
            />
          </div>
          {setupRequired ? (
            <div className="field">
              <label htmlFor="confirmPassword">Confirmar contrasena</label>
              <input
                id="confirmPassword"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                minLength={8}
                required
              />
            </div>
          ) : null}

          <button className="btn btn-primary" type="submit" disabled={submitting}>
            {submitting ? "Enviando..." : setupRequired ? "Crear administrador" : "Entrar"}
          </button>
        </form>
      </div>
    </div>
  );
}
