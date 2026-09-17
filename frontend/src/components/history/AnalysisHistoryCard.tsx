import type { AnalysisListItem } from "../../types/analysisHistory";
import Card from "../ui/Card";
import "./history.css";

interface AnalysisHistoryCardProps {
  item: AnalysisListItem;
  onViewDetails: (analysisId: string) => void;
}

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

function AnalysisHistoryCard({ item, onViewDetails }: AnalysisHistoryCardProps) {
  return (
    <Card className="history-card">
      <div className="history-card-scores">
        <div className="history-card-score">
          <span className="history-card-score-value">{Math.round(item.combined_score)}%</span>
          <span className="history-card-score-label">Combined</span>
        </div>
        <div className="history-card-score">
          <span className="history-card-score-value">{Math.round(item.deterministic_score)}%</span>
          <span className="history-card-score-label">Deterministic</span>
        </div>
        <div className="history-card-score">
          <span className="history-card-score-value">{Math.round(item.semantic_score)}%</span>
          <span className="history-card-score-label">Semantic</span>
        </div>
      </div>

      <div className="history-card-footer">
        <span className="ui-field-hint">{formatDate(item.created_at)}</span>
        <button
          type="button"
          className="ui-button ui-button-primary"
          onClick={() => onViewDetails(item.analysis_id)}
        >
          View Details
        </button>
      </div>
    </Card>
  );
}

export default AnalysisHistoryCard;
