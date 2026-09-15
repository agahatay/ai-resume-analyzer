interface MatchListProps {
  items: string[];
  variant: "matched" | "missing";
  emptyLabel?: string;
}

function MatchList({ items, variant, emptyLabel = "None" }: MatchListProps) {
  if (items.length === 0) {
    return <p className="dash-empty">{emptyLabel}</p>;
  }
  return (
    <ul className="dash-list">
      {items.map((item) => (
        <li key={item} className={`dash-list-item dash-list-item-${variant}`}>
          {variant === "matched" ? "✓ " : "✗ "}
          {item}
        </li>
      ))}
    </ul>
  );
}

export default MatchList;
