import "../ui/ui.css";

interface MatchBadgeProps {
  status: string;
}

function MatchBadge({ status }: MatchBadgeProps) {
  return <span className={`ui-badge ui-badge-${status}`}>{status.replace(/_/g, " ")}</span>;
}

export default MatchBadge;
