import Card from "./Card";
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

function SemanticMatchCard({ item }: { item: SemanticMatchItem }) {
  const similarityPercent = Math.round(item.similarity * 100);
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
          Similarity: <strong>{item.similarity.toFixed(2)}</strong> ({similarityPercent}%)
        </span>
        <span className={`dash-badge ${item.matched ? "dash-badge-matched" : "dash-badge-missing"}`}>
          {item.matched ? "✓ Semantic Match" : "✗ Not Matched"}
        </span>
      </div>
      <div className="dash-similarity-bar" role="img" aria-label={`Similarity ${similarityPercent}%`}>
        <div
          className={`dash-similarity-bar-fill ${item.matched ? "" : "dash-below-threshold"}`}
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
        <p className="dash-empty">No semantic comparisons were available for this job description.</p>
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
