import Card from "./Card";
import MatchBadge from "./MatchBadge";
import type { EducationMatchResult } from "../../types/match";
import type { EducationEntry } from "../../types/resume";

interface EducationAnalysisProps {
  educationMatch: EducationMatchResult;
  resumeEducation: EducationEntry[];
  jobRequirements: string[];
}

function describeEntry(entry: EducationEntry): string {
  const parts = [entry.degree, entry.institution].filter(Boolean);
  const label = parts.length > 0 ? parts.join(" — ") : entry.raw_text;
  return entry.dates ? `${label} (${entry.dates})` : label;
}

function EducationAnalysis({ educationMatch, resumeEducation, jobRequirements }: EducationAnalysisProps) {
  return (
    <Card title="Education">
      <div className="dash-semantic-row" style={{ marginBottom: "0.6rem" }}>
        <MatchBadge status={educationMatch.status} />
      </div>
      <p>{educationMatch.details}</p>

      <div className="dash-grid-2">
        <div>
          <p className="dash-subheading">Job Requirement</p>
          {jobRequirements.length === 0 ? (
            <p className="dash-empty">No education requirement specified.</p>
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
          <p className="dash-subheading">Resume Education</p>
          {resumeEducation.length === 0 ? (
            <p className="dash-empty">No education listed on the resume.</p>
          ) : (
            <ul className="dash-list">
              {resumeEducation.map((entry, index) => (
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

export default EducationAnalysis;
