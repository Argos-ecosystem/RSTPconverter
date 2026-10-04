import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function Nav() {
  const { logout } = useAuth();

  return (
    <nav className="topnav">
      <span className="brand">RSTP Converter</span>
      <NavLink to="/" end>
        Resumen
      </NavLink>
      <NavLink to="/cameras">Camaras</NavLink>
      <NavLink to="/api-config">API y transformacion</NavLink>
      <div className="spacer" />
      <button className="logout-btn" onClick={logout}>
        Cerrar sesion
      </button>
    </nav>
  );
}
