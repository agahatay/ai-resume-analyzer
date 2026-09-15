import "./ui/ui.css";

interface StatusBadgeProps {
  status: string;
}

function StatusBadge({ status }: StatusBadgeProps) {
  const variant = status === "ok" ? "matched" : status === "unreachable" ? "missing" : "neutral";
  return (
    <p style={{ margin: 0 }}>
      <span className={`ui-badge ui-badge-${variant}`}>API: {status}</span>
    </p>
  );
}

export default StatusBadge;
