import type { ParsedResume } from "../types/resume";
import { ChipList } from "./ui/Chip";

interface ParsedResumeViewProps {
  data: ParsedResume;
}

function ParsedResumeView({ data }: ParsedResumeViewProps) {
  return (
    <div>
      <h4>Contact</h4>
      <ul>
        <li>Name: {data.full_name ?? "—"}</li>
        <li>Email: {data.email ?? "—"}</li>
        <li>Phone: {data.phone ?? "—"}</li>
        <li>Location: {data.location ?? "—"}</li>
      </ul>

      <h4>Skills</h4>
      <ChipList items={data.skills} variant="neutral" emptyLabel="No skills detected." />

      <h4>Education</h4>
      {data.education.length > 0 ? (
        <ul>
          {data.education.map((entry, index) => (
            <li key={index}>
              {entry.degree ?? entry.raw_text}
              {entry.institution ? ` — ${entry.institution}` : ""}
              {entry.dates ? ` (${entry.dates})` : ""}
            </li>
          ))}
        </ul>
      ) : (
        <p className="ui-empty-inline">No education detected.</p>
      )}

      <h4>Work Experience</h4>
      {data.work_experience.length > 0 ? (
        <ul>
          {data.work_experience.map((entry, index) => (
            <li key={index}>
              {entry.title ?? entry.raw_text}
              {entry.organization ? ` — ${entry.organization}` : ""}
              {entry.dates ? ` (${entry.dates})` : ""}
            </li>
          ))}
        </ul>
      ) : (
        <p className="ui-empty-inline">No work experience detected.</p>
      )}

      <h4>Projects</h4>
      {data.projects.length > 0 ? (
        <ul>
          {data.projects.map((entry, index) => (
            <li key={index}>
              {entry.name ?? entry.raw_text}
              {entry.description ? `: ${entry.description}` : ""}
            </li>
          ))}
        </ul>
      ) : (
        <p className="ui-empty-inline">No projects detected.</p>
      )}

      <h4>Certifications</h4>
      <ChipList items={data.certifications} variant="neutral" emptyLabel="No certifications detected." />

      <h4>Languages</h4>
      <ChipList items={data.languages} variant="neutral" emptyLabel="No languages detected." />
    </div>
  );
}

export default ParsedResumeView;
