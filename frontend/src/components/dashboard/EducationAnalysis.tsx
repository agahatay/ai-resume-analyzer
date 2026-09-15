import Card from "../ui/Card";
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
            <p className="ui-empty-inline">No education requirement specified.</p>
          ) : (
            <ul className="dash-plain-list">
              {jobRequirements.map((req) => (
                <li key={req}>{req}</li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <p className="dash-subheading">Resume Education</p>
          {resumeEducation.length === 0 ? (
            <p className="ui-empty-inline">No education listed on the resume.</p>
          ) : (
            <ul className="dash-plain-list">
              {resumeEducation.map((entry, index) => (
                <li key={index}>{describeEntry(entry)}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </Card>
  );
}

export default EducationAnalysis;
