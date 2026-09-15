import Card from "../ui/Card";
import ProgressRing from "../ui/ProgressRing";

interface ScoreOverviewProps {
  deterministicScore: number;
  semanticScore: number;
  combinedScore: number;
  formula: string;
}

function ScoreTile({
  label,
  value,
  primary,
}: {
  label: string;
  value: number;
  primary?: boolean;
}) {
  return (
    <div className={`dash-score-tile ${primary ? "dash-score-tile-primary" : ""}`.trim()}>
      {/* The ring and percentage both render the backend value as-is
          (Math.round is display-only rounding, never a recalculation). */}
      <ProgressRing
        value={value}
        size={primary ? 108 : 84}
        strokeWidth={primary ? 10 : 7}
        color={primary ? "var(--color-primary)" : "var(--color-success)"}
        label={`${label}: ${Math.round(value)} percent`}
      />
      <div className="dash-score-label">{label}</div>
    </div>
  );
}

function ScoreOverview({ deterministicScore, semanticScore, combinedScore, formula }: ScoreOverviewProps) {
  return (
    <Card title="Match Scores">
      <div className="dash-score-row">
        <ScoreTile label="Deterministic Match" value={deterministicScore} />
        <ScoreTile label="Semantic Match" value={semanticScore} />
        <ScoreTile label="Combined Match" value={combinedScore} primary />
      </div>
      <p className="dash-formula">{formula}</p>
    </Card>
  );
}

export default ScoreOverview;
