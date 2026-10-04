import { useEffect, useState } from "react";
import MiniBarChart from "../components/MiniBarChart";
import StatTile from "../components/StatTile";
import StatusBadge from "../components/StatusBadge";
import { api } from "../api/client";
import { formatDateTime, formatDuration, formatRelative } from "../utils/format";

const REFRESH_MS = 10000;

export default function Dashboard() {
  const [summary, setSummary] = useState(null);
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;

    async function load() {
      try {
        const [summaryData, logsData] = await Promise.all([api.stats.summary(), api.stats.logs({ limit: 15 })]);
        if (!cancelled) {
          setSummary(summaryData);
          setLogs(logsData);
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError(err.message || "No se pudieron cargar las estadisticas");
      }
    }

    load();
    const id = setInterval(load, REFRESH_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  if (error && !summary) {
    return (
      <div className="page">
        <h1>Resumen</h1>
        <div className="banner error">{error}</div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="page">
        <h1>Resumen</h1>
        <p>Cargando estadisticas...</p>
      </div>
    );
  }

  const chartItems = summary.cameras.map((c) => ({ label: c.camera_name, value: c.frames_sent_total }));

  return (
    <div className="page">
      <div className="page-header">
        <h1>Resumen</h1>
      </div>

      <div className="stat-grid">
        <StatTile label="Frames enviados (total)" value={summary.frames_sent_total} />
        <StatTile label="Frames enviados hoy" value={summary.frames_sent_today} />
        <StatTile
          label="Tasa de exito"
          value={`${summary.success_rate.toFixed(1)}%`}
          sub={`${summary.frames_failed_total} fallidos`}
        />
        <StatTile
          label="Camaras activas"
          value={`${summary.active_cameras}/${summary.total_cameras}`}
        />
        <StatTile
          label="Latencia promedio"
          value={summary.avg_latency_ms != null ? `${Math.round(summary.avg_latency_ms)} ms` : "-"}
        />
        <StatTile
          label="Mayor tiempo activo seguido"
          value={formatDuration(summary.longest_uptime_seconds)}
          sub="racha de envios sin interrupcion"
        />
        <StatTile
          label="Mayor caida detectada"
          value={formatDuration(summary.longest_gap_seconds)}
          sub="mayor intervalo sin enviar"
        />
      </div>

      <div className="card" style={{ marginBottom: 24 }}>
        <div className="label" style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
          Frames enviados por camara
        </div>
        <MiniBarChart items={chartItems} />
      </div>

      <div className="card">
        <div className="label" style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
          Detalle por camara
        </div>
        {summary.cameras.length === 0 ? (
          <div className="empty-state">Aun no hay camaras configuradas.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Camara</th>
                <th>Estado</th>
                <th className="num">Enviados</th>
                <th className="num">Hoy</th>
                <th className="num">Exito</th>
                <th>Ultimo envio</th>
                <th className="num">Uptime max</th>
                <th className="num">Caida max</th>
              </tr>
            </thead>
            <tbody>
              {summary.cameras.map((c) => (
                <tr key={c.camera_id}>
                  <td>{c.camera_name}</td>
                  <td>
                    <StatusBadge status={c.status} />
                  </td>
                  <td className="num">{c.frames_sent_total}</td>
                  <td className="num">{c.frames_sent_today}</td>
                  <td className="num">{c.success_rate.toFixed(1)}%</td>
                  <td className="muted">{formatRelative(c.last_sent_at)}</td>
                  <td className="num">{formatDuration(c.longest_uptime_seconds)}</td>
                  <td className="num">{formatDuration(c.longest_gap_seconds)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="card" style={{ marginTop: 24 }}>
        <div className="label" style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 8 }}>
          Actividad reciente
        </div>
        {logs.length === 0 ? (
          <div className="empty-state">Todavia no hubo intentos de envio.</div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Hora</th>
                <th>Camara</th>
                <th>Resultado</th>
                <th>Motivo</th>
                <th>Detalle</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log) => (
                <tr key={log.id}>
                  <td className="muted">{formatDateTime(log.sent_at)}</td>
                  <td>{log.camera_name}</td>
                  <td>
                    <span className={`status-badge ${log.success ? "status-good" : "status-critical"}`}>
                      <span className="dot" />
                      {log.success ? "Enviado" : "Fallo"}
                    </span>
                  </td>
                  <td className="muted">{log.trigger_reason || "-"}</td>
                  <td className="muted">{log.success ? `HTTP ${log.http_status}` : log.error_message}
                    {log.response_body && <details><summary>Ver respuesta</summary><pre className="send-response">{log.response_body}</pre></details>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
