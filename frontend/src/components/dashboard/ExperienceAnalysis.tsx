import Card from "../ui/Card";
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
            <p className="ui-empty-inline">No experience requirement specified.</p>
          ) : (
            <ul className="dash-plain-list">
              {jobRequirements.map((req) => (
                <li key={req}>{req}</li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <p className="dash-subheading">Detected Resume Experience</p>
          {resumeExperience.length === 0 ? (
            <p className="ui-empty-inline">No work experience listed on the resume.</p>
          ) : (
            <ul className="dash-plain-list">
              {resumeExperience.map((entry, index) => (
                <li key={index}>{describeEntry(entry)}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Card>
  );
}

export default ExperienceAnalysis;
