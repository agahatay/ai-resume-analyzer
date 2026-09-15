import type { ParsedJobDescription } from "../types/jobDescription";

interface ParsedJobDescriptionViewProps {
  data: ParsedJobDescription;
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

function ParsedJobDescriptionView({ data }: ParsedJobDescriptionViewProps) {
  return (
    <div>
      <h3>Job Title</h3>
      <p>{data.job_title ?? "—"}</p>

      <h3>Required Skills</h3>
      <StringList items={data.required_skills} />

      <h3>Preferred Skills</h3>
      <StringList items={data.preferred_skills} />

      <h3>Education Requirements</h3>
      <StringList items={data.education_requirements} />

      <h3>Experience Requirements</h3>
      <StringList items={data.experience_requirements} />

      <h3>Certifications</h3>
      <StringList items={data.certifications} />

      <h3>Languages</h3>
      <StringList items={data.languages} />
    </div>
  );
}

export default ParsedJobDescriptionView;
