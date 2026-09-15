import type { ResumeMatchResponse } from "../types/match";

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

function MatchResult({ data }: MatchResultProps) {
  return (
    <div>
      <h3>Match Score: {Math.round(data.overall_match_score)}%</h3>

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

      <h4>Recommendations</h4>
      <p>{data.summary}</p>
    </div>
  );
}

export default MatchResult;
