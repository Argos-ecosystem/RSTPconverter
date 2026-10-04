const STATUS_MAP = {
  connected: { cls: "status-good", label: "Conectada" },
  connecting: { cls: "status-warning", label: "Conectando" },
  error: { cls: "status-critical", label: "Error" },
  stopped: { cls: "status-muted", label: "Detenida" },
};

export default function StatusBadge({ status }) {
  const info = STATUS_MAP[status] || STATUS_MAP.stopped;
  return (
    <span className={`status-badge ${info.cls}`}>
      <span className="dot" />
      {info.label}
    </span>
  );
}
