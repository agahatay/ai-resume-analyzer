import "./ui.css";

interface ChipProps {
  children: string;
  variant: "matched" | "missing" | "neutral";
}

function Chip({ children, variant }: ChipProps) {
  return (
    <li className={`ui-chip ui-chip-${variant}`}>
      <span aria-hidden="true">{variant === "matched" ? "✓" : variant === "missing" ? "✗" : "•"}</span>
      {children}
    </li>
  );
}

interface ChipListProps {
  items: string[];
  variant: "matched" | "missing" | "neutral";
  emptyLabel: string;
}

export function ChipList({ items, variant, emptyLabel }: ChipListProps) {
  if (items.length === 0) {
    return <p className="ui-empty-inline">{emptyLabel}</p>;
  }
  return (
    <ul className="ui-chip-list">
      {items.map((item) => (
        <Chip key={item} variant={variant}>
          {item}
        </Chip>
      ))}
    </ul>
  );
}

export default Chip;
