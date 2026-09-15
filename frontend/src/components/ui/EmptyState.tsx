import "./ui.css";

interface EmptyStateProps {
  title: string;
  message?: string;
}

function EmptyState({ title, message }: EmptyStateProps) {
  return (
    <div className="ui-empty-state">
      <p className="ui-empty-state-title">{title}</p>
      {message && <p style={{ margin: 0 }}>{message}</p>}
    </div>
  );
}

export default EmptyState;
