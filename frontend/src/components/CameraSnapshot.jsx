import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

const REFRESH_MS = 500;

export default function CameraSnapshot({ cameraId }) {
  const [src, setSrc] = useState(null);
  const [connected, setConnected] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const urlRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    let timer;

    async function tick() {
      try {
        const blob = await api.cameras.snapshot(cameraId);
        if (cancelled) return;
        const url = URL.createObjectURL(blob);
        if (urlRef.current) URL.revokeObjectURL(urlRef.current);
        urlRef.current = url;
        setSrc(url);
        setConnected(true);
        setError("");
      } catch (err) {
        if (!cancelled) {
          setConnected(false);
          setError(err.message || "No se pudo cargar la vista previa");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
          timer = setTimeout(tick, REFRESH_MS);
        }
      }
    }

    tick();
    return () => {
      cancelled = true;
      clearTimeout(timer);
      if (urlRef.current) URL.revokeObjectURL(urlRef.current);
    };
  }, [cameraId]);

  if (loading) {
    return <div className="snapshot-placeholder">Cargando...</div>;
  }

  if (!src) {
    return (
      <div className="snapshot-placeholder">
        {connected ? "Cargando..." : error}
      </div>
    );
  }

  return (
    <div className="snapshot-wrap">
      <img className="snapshot-img" src={src} alt="vista en vivo de la camara" />
      {!connected ? (
        <div className="snapshot-overlay">{error}. Mostrando la ultima imagen.</div>
      ) : null}
    </div>
  );
}
