import type { ResumeMatchResponse, SemanticMatchItem } from "../types/match";

interface MatchResultProps {
  data: ResumeMatchResponse;
}

function StringList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <p>—</p>;
  }
  return (
    <ul>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function SemanticMatchCard({ item }: { item: SemanticMatchItem }) {
  return (
    <div style={{ border: "1px solid #ccc", padding: "0.5rem", marginBottom: "0.5rem" }}>
      <p>
        <strong>Category:</strong> {item.category}
      </p>
      <p>
        <strong>Required:</strong> "{item.requirement}"
      </p>
      <p>
        <strong>Matched Resume Text:</strong>{" "}
        {item.matched_resume_text ? `"${item.matched_resume_text}"` : "—"}
      </p>
      <p>
        <strong>Similarity:</strong> {item.similarity.toFixed(2)}
      </p>
      <p>{item.matched ? "✓ Semantic Match" : "✗ No Semantic Match"}</p>
    </div>
  );
}

function MatchResult({ data }: MatchResultProps) {
  return (
    <div>
      <h3>Deterministic Match: {Math.round(data.deterministic_match.score)}%</h3>
      <h3>Semantic Match: {Math.round(data.semantic_match.semantic_score)}%</h3>
      <h3>Combined Match: {Math.round(data.combined_match_score)}%</h3>
      <p>
        <em>{data.combined_score_formula}</em>
      </p>

      <h4>Matched Skills</h4>
      <StringList items={data.matched_skills} />

      <h4>Missing Required Skills</h4>
      <StringList items={data.missing_required_skills} />

      <h4>Matched Preferred Skills</h4>
      <StringList items={data.matched_preferred_skills} />

      <h4>Missing Preferred Skills</h4>
      <StringList items={data.missing_preferred_skills} />

      <h4>Education</h4>
      <p>
        {data.education_match.status.replace("_", " ")}: {data.education_match.details}
      </p>

      <h4>Experience</h4>
      <p>
        {data.experience_match.status.replace("_", " ")}: {data.experience_match.details}
      </p>

      <h4>Certifications</h4>
      <p>Matched:</p>
      <StringList items={data.certification_match.matched} />
      <p>Missing:</p>
      <StringList items={data.certification_match.missing} />

      <h4>Languages</h4>
      <p>Matched:</p>
      <StringList items={data.language_match.matched} />
      <p>Missing:</p>
      <StringList items={data.language_match.missing} />

      <h4>Semantic Matches</h4>
      <p>
        Model: {data.semantic_match.model_name} · Similarity threshold:{" "}
        {data.semantic_match.similarity_threshold}
      </p>
      {data.semantic_match.semantic_matches.length === 0 ? (
        <p>—</p>
      ) : (
        data.semantic_match.semantic_matches.map((item, index) => (
          <SemanticMatchCard key={`${item.category}-${item.requirement}-${index}`} item={item} />
        ))
      )}

      <h4>Recommendations</h4>
      <p>{data.summary}</p>
    </div>
  );
}

export default MatchResult;
