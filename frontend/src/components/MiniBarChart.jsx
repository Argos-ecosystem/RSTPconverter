export default function MiniBarChart({ items }) {
  if (!items.length) {
    return <div className="empty-state">Sin datos todavia</div>;
  }

  const max = Math.max(1, ...items.map((i) => i.value));

  return (
    <div className="mini-bar-chart" role="img" aria-label="Frames enviados por camara">
      {items.map((item) => (
        <div className="mini-bar-col" key={item.label} title={`${item.label}: ${item.value}`}>
          <span className="bar-value">{item.value}</span>
          <div className="bar" style={{ height: `${Math.max(2, (item.value / max) * 100)}%` }} />
          <span className="bar-label">{item.label}</span>
        </div>
      ))}
    </div>
  );
}
