import "./ui.css";

interface SpinnerProps {
  label?: string;
}

function Spinner({ label }: SpinnerProps) {
  return (
    <span role="status" aria-live="polite" style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
      <span className="ui-spinner" aria-hidden="true" />
      {label && <span>{label}</span>}
    </span>
  );
}

export default Spinner;
