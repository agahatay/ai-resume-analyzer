interface MatchBadgeProps {
  status: string;
}

function MatchBadge({ status }: MatchBadgeProps) {
  return <span className={`dash-badge dash-badge-${status}`}>{status.replace(/_/g, " ")}</span>;
}

export default MatchBadge;
