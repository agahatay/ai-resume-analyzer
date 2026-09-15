import Card from "./Card";
import MatchBadge from "./MatchBadge";
import type { ExperienceMatchResult } from "../../types/match";
import type { ExperienceEntry } from "../../types/resume";

interface ExperienceAnalysisProps {
  experienceMatch: ExperienceMatchResult;
  resumeExperience: ExperienceEntry[];
  jobRequirements: string[];
}

function describeEntry(entry: ExperienceEntry): string {
  const parts = [entry.title, entry.organization].filter(Boolean);
  const label = parts.length > 0 ? parts.join(" — ") : entry.raw_text;
  return entry.dates ? `${label} (${entry.dates})` : label;
}

function ExperienceAnalysis({ experienceMatch, resumeExperience, jobRequirements }: ExperienceAnalysisProps) {
  return (
    <Card title="Experience">
      <div className="dash-semantic-row" style={{ marginBottom: "0.6rem" }}>
        <MatchBadge status={experienceMatch.status} />
        {experienceMatch.required_years !== null && (
          <span className="dash-subheading">Required: {experienceMatch.required_years}+ years</span>
        )}
        {experienceMatch.resume_years !== null && (
          <span className="dash-subheading">Detected: {experienceMatch.resume_years} years</span>
        )}
      </div>
      <p>{experienceMatch.details}</p>

      <div className="dash-grid-2">
        <div>
          <p className="dash-subheading">Required Experience</p>
          {jobRequirements.length === 0 ? (
            <p className="dash-empty">No experience requirement specified.</p>
          ) : (
            <ul className="dash-list">
              {jobRequirements.map((req) => (
                <li key={req} className="dash-list-item">
                  {req}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <p className="dash-subheading">Detected Resume Experience</p>
          {resumeExperience.length === 0 ? (
            <p className="dash-empty">No work experience listed on the resume.</p>
          ) : (
            <ul className="dash-list">
              {resumeExperience.map((entry, index) => (
                <li key={index} className="dash-list-item">
                  {describeEntry(entry)}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Card>
  );
}

export default ExperienceAnalysis;
