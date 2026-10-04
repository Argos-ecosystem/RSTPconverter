import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import Nav from "./components/Nav";
import { AuthProvider, useAuth } from "./context/AuthContext";
import ApiConfig from "./pages/ApiConfig";
import Cameras from "./pages/Cameras";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import "./App.css";

function ProtectedLayout({ children }) {
  const { isAuthenticated, ready } = useAuth();

  if (!ready) return null;
  if (!isAuthenticated) return <Navigate to="/login" replace />;

  return (
    <div className="app-shell">
      <Nav />
      {children}
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedLayout>
                <Dashboard />
              </ProtectedLayout>
            }
          />
          <Route
            path="/cameras"
            element={
              <ProtectedLayout>
                <Cameras />
              </ProtectedLayout>
            }
          />
          <Route
            path="/api-config"
            element={
              <ProtectedLayout>
                <ApiConfig />
              </ProtectedLayout>
            }
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Router>
    </AuthProvider>
  );
}
