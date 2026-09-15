import Card from "./Card";
import type { ResumeMatchResponse } from "../../types/match";

/**
 * Pure, deterministic recommendations derived only from the existing
 * backend match result — no LLM involved. Every recommendation traces back
 * to a specific field already present in `data`.
 */
function buildRecommendations(data: ResumeMatchResponse): string[] {
  const recommendations: string[] = [];

  if (data.missing_required_skills.length > 0) {
    recommendations.push(
      `Add or gain experience in these required skills: ${data.missing_required_skills.join(", ")}.`,
    );
  }

  if (data.missing_preferred_skills.length > 0) {
    recommendations.push(
      `Consider these preferred skills to strengthen the application: ${data.missing_preferred_skills.join(", ")}.`,
    );
  }

  if (data.education_match.status === "not_matched" || data.education_match.status === "partial") {
    recommendations.push(`Education gap: ${data.education_match.details}`);
  }

  if (
    data.experience_match.status === "not_matched" ||
    data.experience_match.status === "partial" ||
    data.experience_match.status === "unknown"
  ) {
    recommendations.push(`Experience gap: ${data.experience_match.details}`);
  }

  if (data.certification_match.missing.length > 0) {
    recommendations.push(`Missing certifications: ${data.certification_match.missing.join(", ")}.`);
  }

  if (data.language_match.missing.length > 0) {
    recommendations.push(`Missing languages: ${data.language_match.missing.join(", ")}.`);
  }

  // Call out cases where the deterministic matcher missed a required or
  // preferred skill that the semantic layer found evidence for elsewhere in
  // the resume — this is exactly the kind of gap semantic matching exists
  // to surface.
  const missingSkills = new Set([...data.missing_required_skills, ...data.missing_preferred_skills]);
  for (const item of data.semantic_match.semantic_matches) {
    if (item.matched && item.matched_resume_text && missingSkills.has(item.requirement)) {
      recommendations.push(
        `"${item.requirement}" wasn't an exact keyword match, but the resume semantically demonstrates it via: "${item.matched_resume_text}" (similarity ${item.similarity.toFixed(2)}).`,
      );
    }
  }

  if (recommendations.length === 0) {
    recommendations.push("Strong match — no major gaps identified based on the available data.");
  }

  return recommendations;
}

interface RecommendationsProps {
  data: ResumeMatchResponse;
}

function Recommendations({ data }: RecommendationsProps) {
  const recommendations = buildRecommendations(data);

  return (
    <Card title="Recommendations">
      <ul className="dash-recommendation-list">
        {recommendations.map((text, index) => (
          <li key={index}>{text}</li>
        ))}
      </ul>
    </Card>
  );
}

export default Recommendations;
