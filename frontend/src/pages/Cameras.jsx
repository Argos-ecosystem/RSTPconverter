import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import CameraSnapshot from "../components/CameraSnapshot";
import StatusBadge from "../components/StatusBadge";
import { api } from "../api/client";
import { formatDateTime, formatRelative } from "../utils/format";

const EMPTY_FORM = {
  name: "",
  rtsp_url: "",
  external_camera_id: "",
  api_key: "",
  enabled: true,
};

function SecretInput({ label, value, onChange, configured, onClear, placeholder }) {
  return (
    <div className="field">
      <label>{label}</label>
      <div className="secret-row">
        <input
          type="password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
        />
        <span className={`configured-badge ${configured ? "yes" : "no"}`}>
          {configured ? "configurada" : "no configurada"}
        </span>
      </div>
      {configured ? (
        <button type="button" className="clear-link" onClick={onClear}>
          Borrar valor guardado
        </button>
      ) : null}
    </div>
  );
}

function CameraFormModal({ camera, onClose, onSaved }) {
  const isEdit = !!camera;
  const [form, setForm] = useState(
    camera
      ? {
          name: camera.name,
          rtsp_url: camera.rtsp_url,
          external_camera_id: camera.external_camera_id || "",
          api_key: "",
          enabled: camera.enabled,
        }
      : EMPTY_FORM
  );
  const [clearApiKey, setClearApiKey] = useState(false);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError("");
    setSaving(true);
    try {
      if (isEdit) {
        await api.cameras.update(camera.id, {
          name: form.name,
          rtsp_url: form.rtsp_url,
          external_camera_id: form.external_camera_id,
          api_key: form.api_key ? form.api_key : null,
          clear_api_key: clearApiKey,
          enabled: form.enabled,
        });
      } else {
        await api.cameras.create({
          name: form.name,
          rtsp_url: form.rtsp_url,
          external_camera_id: form.external_camera_id || null,
          api_key: form.api_key || null,
          enabled: form.enabled,
        });
      }
      onSaved();
    } catch (err) {
      setError(err.message || "No se pudo guardar la camara");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h2>{isEdit ? "Editar camara" : "Agregar camara"}</h2>
        {error ? <div className="banner error">{error}</div> : null}
        <form onSubmit={handleSubmit}>
          <div className="field">
            <label>Nombre</label>
            <input
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="Ej: Entrada principal"
              required
            />
          </div>
          <div className="field">
            <label>URL RTSP</label>
            <input
              type="text"
              value={form.rtsp_url}
              onChange={(e) => setForm({ ...form, rtsp_url: e.target.value })}
              placeholder="rtsp://usuario:clave@192.168.1.50:554/stream1"
              required
            />
            <span className="hint">
              La URL completa con usuario y contrasena incluidos (si la camara los pide), igual que
              en Iris. Ej: rtsp://admin:clave@192.168.1.50:554/stream1
            </span>
          </div>
          <div className="field">
            <label>Camera ID en la API destino</label>
            <input
              type="text"
              value={form.external_camera_id}
              onChange={(e) => setForm({ ...form, external_camera_id: e.target.value })}
              placeholder="Ej: CAM1"
            />
            <span className="hint">
              Debe coincidir EXACTO (mayusculas incluidas) con el camera_id configurado en Iris
              para esta camara. Ej: "CAM1" y "cam1" no son lo mismo para la API.
            </span>
          </div>
          <SecretInput
            label="API Key de esta camara"
            value={form.api_key}
            onChange={(v) => {
              setForm({ ...form, api_key: v });
              if (v) setClearApiKey(false);
            }}
            configured={isEdit && camera.has_api_key && !clearApiKey}
            onClear={() => {
              setClearApiKey(true);
              setForm({ ...form, api_key: "" });
            }}
            placeholder={isEdit && camera.has_api_key ? "sin cambios" : "Clave que identifica a esta camara ante la API"}
          />
          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(e) => setForm({ ...form, enabled: e.target.checked })}
            />
            Habilitada (captura y envia frames)
          </label>

          <div className="modal-actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>
              Cancelar
            </button>
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? "Guardando..." : "Guardar"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function SnapshotModal({ camera, onClose }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()} style={{ maxWidth: 640 }}>
        <h2>{camera.name}</h2>
        <CameraSnapshot key={camera.id} cameraId={camera.id} />
        <div className="modal-actions">
          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

function SendLogsModal({ camera, onClose, message }) {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    async function refresh() {
      try {
        const data = await api.stats.logs({ camera_id: camera.id, limit: 20 });
        if (active) { setLogs(data); setError(""); }
      } catch (err) {
        if (active) setError(err.message);
      } finally {
        if (active) setLoading(false);
      }
    }
    refresh();
    const timer = setInterval(refresh, 3000);
    return () => { active = false; clearInterval(timer); };
  }, [camera.id]);
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" aria-label={`Envios de ${camera.name}`} onClick={(e) => e.stopPropagation()} style={{ maxWidth: 760 }}>
        <h2>Log de envíos · {camera.name}</h2>
        {message && <p role="status">{message}</p>}
        <p className="muted">Últimos 20 envíos. Se actualiza cada 3 segundos.</p>
        {error && <div className="banner error">{error}</div>}
        {loading ? <p>Cargando...</p> : !logs.length ? <p>Todavía no hay envíos registrados.</p> : logs.map((log) => (
          <details key={log.id} open={log.trigger_reason === "manual"} className="send-log">
            <summary>{formatDateTime(log.sent_at)} · {log.success ? "Enviado" : "Falló"} · {log.trigger_reason === "manual" ? "Manual" : log.trigger_reason} · {log.http_status ? `HTTP ${log.http_status}` : "Sin respuesta HTTP"}</summary>
            <p>{log.latency_ms ?? "—"} ms · {log.frame_bytes ?? 0} bytes</p>
            {log.error_message && <p className="banner error">{log.error_message}</p>}
            <strong>Respuesta de la API</strong>
            <pre className="send-response">{log.response_body ?? "Sin cuerpo de respuesta registrado."}</pre>
          </details>
        ))}
        <div className="modal-actions"><button className="btn btn-secondary" onClick={onClose}>Cerrar</button></div>
      </div>
    </div>
  );
}

export default function Cameras() {
  const [cameras, setCameras] = useState([]);
  const [logCamera, setLogCamera] = useState(null);
  const [sending, setSending] = useState({});
  const [sendMessages, setSendMessages] = useState({});

  async function sendNow(camera) {
    setSending((prev) => ({ ...prev, [camera.id]: true }));
    setSendMessages((prev) => ({ ...prev, [camera.id]: "Tomando una imagen y enviando..." }));
    setLogCamera(camera);
    try {
      const log = await api.cameras.sendNow(camera.id);
      setSendMessages((prev) => ({ ...prev, [camera.id]: log.success
        ? `Enviado · HTTP ${log.http_status} · ${log.latency_ms} ms`
        : `Falló: ${log.error_message || "Consulta el log"}` }));
      load();
    } catch (err) {
      setSendMessages((prev) => ({ ...prev, [camera.id]: err.message || "No se pudo enviar" }));
    } finally {
      setSending((prev) => ({ ...prev, [camera.id]: false }));
    }
  }
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [modalCamera, setModalCamera] = useState(undefined); // undefined = closed, null = new, object = edit
  const [previewCamera, setPreviewCamera] = useState(null);
  const [endpointUrl, setEndpointUrl] = useState(undefined); // undefined = loading, null = not set

  async function load() {
    try {
      const data = await api.cameras.list();
      setCameras(data);
      setError("");
    } catch (err) {
      setError(err.message || "No se pudieron cargar las camaras");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    api.apiConfig
      .get()
      .then((cfg) => setEndpointUrl(cfg.endpoint_url || null))
      .catch(() => setEndpointUrl(null));
  }, []);

  async function toggleEnabled(camera) {
    await api.cameras.update(camera.id, { enabled: !camera.enabled });
    load();
  }

  async function handleDelete(camera) {
    if (!confirm(`Eliminar la camara "${camera.name}"? Esto tambien borra su historial.`)) return;
    await api.cameras.remove(camera.id);
    load();
  }

  return (
    <div className="page">
      <div className="page-header">
        <h1>Camaras (fuentes RTSP)</h1>
        <button className="btn btn-primary" onClick={() => setModalCamera(null)}>
          + Agregar camara
        </button>
      </div>

      {error ? <div className="banner error">{error}</div> : null}

      {endpointUrl !== undefined ? (
        <div className="banner" style={{ background: "var(--gridline)", color: "var(--text-secondary)" }}>
          {endpointUrl ? (
            <>
              Enviando imagenes a: <strong style={{ color: "var(--text-primary)" }}>{endpointUrl}</strong>
            </>
          ) : (
            <>Todavia no configuraste el destino en la nube.</>
          )}{" "}
          <Link to="/api-config">Editar en API y transformacion</Link>
        </div>
      ) : null}

      <div className="card">
        {loading ? (
          <p>Cargando...</p>
        ) : cameras.length === 0 ? (
          <div className="empty-state">
            No hay camaras todavia. Agrega la misma URL RTSP que usas en Iris para empezar a enviar frames.
          </div>
        ) : (
          <div className="camera-grid">
            {cameras.map((camera) => (
              <article className="camera-tile" key={camera.id}>
                <div className="camera-tile-heading">
                  <h2>{camera.name}</h2>
                  <StatusBadge status={camera.enabled ? camera.last_status : "stopped"} />
                </div>
                <button
                  className="camera-tile-preview"
                  onClick={() => setPreviewCamera(camera)}
                  disabled={!camera.enabled}
                  aria-label={`Ampliar vista de ${camera.name}`}
                >
                  {camera.enabled ? (
                    <CameraSnapshot key={camera.id} cameraId={camera.id} />
                  ) : (
                    <div className="snapshot-placeholder">Camara deshabilitada</div>
                  )}
                </button>
                <div className="camera-tile-details">
                  <span>ID API: {camera.external_camera_id || "sin configurar"}</span>
                  <span>{camera.has_api_key ? "API Key configurada" : "Sin API Key para envios"}</span>
                  <span>Ultimo envio: {formatRelative(camera.last_sent_at)}</span>
                </div>
                {sendMessages[camera.id] && <p role="status">{sendMessages[camera.id]}</p>}
                <div className="toolbar">
                  <button className="btn btn-primary btn-sm" onClick={() => sendNow(camera)} disabled={!camera.enabled || sending[camera.id]}>{sending[camera.id] ? "Enviando..." : "Enviar ahora"}</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => setLogCamera(camera)}>Ver log</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => setPreviewCamera(camera)} disabled={!camera.enabled}>Ampliar</button>
                  <button className="btn btn-secondary btn-sm" onClick={() => toggleEnabled(camera)}>
                    {camera.enabled ? "Deshabilitar" : "Habilitar"}
                  </button>
                  <button className="btn btn-secondary btn-sm" onClick={() => setModalCamera(camera)}>Editar</button>
                  <button className="btn btn-danger btn-sm" onClick={() => handleDelete(camera)}>Eliminar</button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      {modalCamera !== undefined ? (
        <CameraFormModal
          camera={modalCamera}
          onClose={() => setModalCamera(undefined)}
          onSaved={() => {
            setModalCamera(undefined);
            load();
          }}
        />
      ) : null}

      {logCamera && <SendLogsModal key={logCamera.id} camera={logCamera} message={sendMessages[logCamera.id]} onClose={() => setLogCamera(null)} />}
      {previewCamera ? <SnapshotModal camera={previewCamera} onClose={() => setPreviewCamera(null)} /> : null}
    </div>
  );
}
