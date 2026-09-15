import Card from "../ui/Card";
import type { SemanticMatchItem } from "../../types/match";

interface SemanticMatchesProps {
  matches: SemanticMatchItem[];
  modelName: string;
  similarityThreshold: number;
}

const CATEGORY_LABELS: Record<SemanticMatchItem["category"], string> = {
  skills: "Skills",
  experience: "Experience",
  projects: "Projects",
  education: "Education",
  certifications: "Certifications",
};

function similarityBand(similarity: number): "high" | "medium" | "low" {
  if (similarity >= 0.5) return "high";
  if (similarity >= 0.3) return "medium";
  return "low";
}

function SemanticMatchCard({ item }: { item: SemanticMatchItem }) {
  const similarityPercent = Math.round(item.similarity * 100);
  const band = similarityBand(item.similarity);

  return (
    <div className="dash-semantic-item">
      <span className="dash-semantic-label">Job Requirement</span>
      <p className="dash-semantic-text">"{item.requirement}"</p>

      <span className="dash-semantic-label">Best Matching Resume Text</span>
      <p className="dash-semantic-text">
        {item.matched_resume_text ? `"${item.matched_resume_text}"` : "No comparable resume text found."}
      </p>

      <div className="dash-semantic-row">
        <span>
          Similarity: <strong>{similarityPercent}%</strong> ({item.similarity.toFixed(2)})
        </span>
        <span className={`ui-badge ${item.matched ? "ui-badge-matched" : "ui-badge-missing"}`}>
          {item.matched ? "✓ Semantic Match" : "✗ Not Matched"}
        </span>
      </div>
      <div className="dash-similarity-bar" role="img" aria-label={`Similarity ${similarityPercent}%`}>
        <div
          className={`dash-similarity-bar-fill dash-similarity-${band}`}
          style={{ width: `${similarityPercent}%` }}
        />
      </div>
    </div>
  );
}

function SemanticMatches({ matches, modelName, similarityThreshold }: SemanticMatchesProps) {
  const categories = Array.from(new Set(matches.map((item) => item.category)));

  return (
    <Card title="Semantic Matches">
      <p className="dash-subheading">
        Model: {modelName} · Similarity threshold: {similarityThreshold}
      </p>
      {matches.length === 0 ? (
        <p className="ui-empty-inline">No semantic comparisons were available for this job description.</p>
      ) : (
        categories.map((category) => (
          <div key={category}>
            <p className="dash-semantic-category">{CATEGORY_LABELS[category]}</p>
            {matches
              .filter((item) => item.category === category)
              .map((item, index) => (
                <SemanticMatchCard key={`${category}-${item.requirement}-${index}`} item={item} />
              ))}
          </div>
        ))
      )}
    </Card>
  );
}

export default SemanticMatches;
