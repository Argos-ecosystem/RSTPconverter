import { createContext, useContext, useEffect, useState } from "react";
import { setAuthToken, setUnauthorizedHandler } from "../api/client";

const AuthContext = createContext(null);
const STORAGE_KEY = "rstpconverter_token";

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY));
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setAuthToken(token);
    setReady(true);
  }, [token]);

  function login(newToken) {
    localStorage.setItem(STORAGE_KEY, newToken);
    setAuthToken(newToken);
    setToken(newToken);
  }

  function logout() {
    localStorage.removeItem(STORAGE_KEY);
    setAuthToken(null);
    setToken(null);
  }

  // A 401 from any request (token expired, or stale after the backend's
  // data/secret was reset) logs the user out instead of leaving pages stuck.
  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, []);

  return (
    <AuthContext.Provider value={{ token, isAuthenticated: !!token, login, logout, ready }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
