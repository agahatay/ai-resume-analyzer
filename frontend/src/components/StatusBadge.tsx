interface StatusBadgeProps {
  status: string;
}

function StatusBadge({ status }: StatusBadgeProps) {
  return <span>API status: {status}</span>;
}

export default StatusBadge;
