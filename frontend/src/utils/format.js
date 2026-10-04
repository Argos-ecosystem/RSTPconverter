export function formatDuration(seconds) {
  if (!seconds || seconds < 1) return "-";

  const s = Math.floor(seconds);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const minutes = Math.floor((s % 3600) / 60);
  const secs = s % 60;

  if (days > 0) return `${days}d ${hours}h`;
  if (hours > 0) return `${hours}h ${minutes}m`;
  if (minutes > 0) return `${minutes}m ${secs}s`;
  return `${secs}s`;
}

export function formatDateTime(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString.endsWith("Z") ? isoString : `${isoString}Z`);
  return date.toLocaleString();
}

export function formatRelative(isoString) {
  if (!isoString) return "-";
  const date = new Date(isoString.endsWith("Z") ? isoString : `${isoString}Z`);
  const diffSeconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (diffSeconds < 5) return "justo ahora";
  if (diffSeconds < 60) return `hace ${diffSeconds}s`;
  if (diffSeconds < 3600) return `hace ${Math.floor(diffSeconds / 60)}m`;
  if (diffSeconds < 86400) return `hace ${Math.floor(diffSeconds / 3600)}h`;
  return `hace ${Math.floor(diffSeconds / 86400)}d`;
}
