import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";

export default function ApiConfig() {
  const [form, setForm] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    api.apiConfig
      .get()
      .then((data) => {
        setForm({
          endpoint_url: data.endpoint_url || "",
          resolution_width: data.resolution_width ?? "",
          resolution_height: data.resolution_height ?? "",
          jpeg_quality: data.jpeg_quality,
          check_interval_seconds: data.check_interval_seconds,
          change_threshold_percent: data.change_threshold_percent,
          max_interval_seconds: data.max_interval_seconds,
          request_timeout_seconds: data.request_timeout_seconds,
        });
      })
      .catch((err) => setError(err.message || "No se pudo cargar la configuracion"));
  }, []);

  if (!form) {
    return (
      <div className="page">
        <h1>API y transformacion</h1>
        {error ? <div className="banner error">{error}</div> : <p>Cargando...</p>}
      </div>
    );
  }

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setSaving(true);

    const payload = {
      endpoint_url: form.endpoint_url,
      resolution_width: form.resolution_width === "" ? null : Number(form.resolution_width),
      resolution_height: form.resolution_height === "" ? null : Number(form.resolution_height),
      jpeg_quality: Number(form.jpeg_quality),
      check_interval_seconds: Number(form.check_interval_seconds),
      change_threshold_percent: Number(form.change_threshold_percent),
      max_interval_seconds: Number(form.max_interval_seconds),
      request_timeout_seconds: Number(form.request_timeout_seconds),
    };

    try {
      await api.apiConfig.update(payload);
      setSuccess("Configuracion guardada.");
    } catch (err) {
      setError(err.message || "No se pudo guardar la configuracion");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>API y transformacion</h1>
      </div>

      {error ? <div className="banner error">{error}</div> : null}
      {success ? <div className="banner success">{success}</div> : null}

      <form onSubmit={handleSubmit}>
        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, marginTop: 0 }}>Destino en la nube</h2>
          <div className="field">
            <label>Dominio / URL de destino</label>
            <input
              type="text"
              value={form.endpoint_url}
              onChange={(e) => set("endpoint_url", e.target.value)}
              placeholder="https://parcela.alabs.cl/api/ingest/image"
            />
            <span className="hint">
              El endpoint al que se sube cada frame (POST JSON con camera_id + image_base64).
            </span>
          </div>
          <div className="banner" style={{ background: "var(--gridline)", color: "var(--text-secondary)" }}>
            Autenticacion: cada camara manda su propia API Key (header X-API-Key). Se configura en{" "}
            <Link to="/cameras">Camaras</Link>, no aca.
          </div>
        </div>

        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, marginTop: 0 }}>Transformacion del frame</h2>
          <div className="form-grid">
            <div className="field">
              <label>Ancho (px)</label>
              <input
                type="number"
                min="0"
                value={form.resolution_width}
                onChange={(e) => set("resolution_width", e.target.value)}
                placeholder="original"
              />
            </div>
            <div className="field">
              <label>Alto (px)</label>
              <input
                type="number"
                min="0"
                value={form.resolution_height}
                onChange={(e) => set("resolution_height", e.target.value)}
                placeholder="original"
              />
              <span className="hint">Vacio = se mantiene la resolucion original del stream, sin redimensionar.</span>
            </div>
            <div className="field">
              <label>Calidad JPEG (1-100)</label>
              <input
                type="number"
                min="1"
                max="100"
                value={form.jpeg_quality}
                onChange={(e) => set("jpeg_quality", e.target.value)}
              />
            </div>
          </div>
        </div>

        <div className="card" style={{ marginBottom: 20 }}>
          <h2 style={{ fontSize: 15, marginTop: 0 }}>Cuando enviar un frame</h2>
          <p className="hint" style={{ marginTop: -8, marginBottom: 16 }}>
            Se revisa la camara cada "intervalo de chequeo". Si el cambio detectado supera el
            porcentaje configurado, se envia de inmediato. Si pasa el "intervalo maximo" sin que
            haya cambios suficientes, igual se envia un frame de referencia (heartbeat).
          </p>
          <div className="form-grid">
            <div className="field">
              <label>Intervalo de chequeo (segundos)</label>
              <input
                type="number"
                min="0.1"
                step="0.1"
                value={form.check_interval_seconds}
                onChange={(e) => set("check_interval_seconds", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Umbral de cambio (%)</label>
              <input
                type="number"
                min="0"
                max="100"
                step="0.5"
                value={form.change_threshold_percent}
                onChange={(e) => set("change_threshold_percent", e.target.value)}
              />
              <span className="hint">% de la imagen que debe cambiar para disparar un envio.</span>
            </div>
            <div className="field">
              <label>Intervalo maximo / heartbeat (segundos)</label>
              <input
                type="number"
                min="1"
                value={form.max_interval_seconds}
                onChange={(e) => set("max_interval_seconds", e.target.value)}
              />
            </div>
            <div className="field">
              <label>Timeout de envio a la API (segundos)</label>
              <input
                type="number"
                min="1"
                value={form.request_timeout_seconds}
                onChange={(e) => set("request_timeout_seconds", e.target.value)}
              />
            </div>
          </div>
        </div>

        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Guardando..." : "Guardar configuracion"}
        </button>
      </form>
    </div>
  );
}
