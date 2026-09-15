import Card from "./Card";

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
      {/* Values are rendered exactly as returned by the backend (Math.round is
          display-only rounding, not a recalculation of any formula). */}
      <div className="dash-score-value">{Math.round(value)}%</div>
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
