import type { ParsedResume } from "../types/resume";

interface ParsedResumeViewProps {
  data: ParsedResume;
}

function ParsedResumeView({ data }: ParsedResumeViewProps) {
  return (
    <div>
      <h3>Contact</h3>
      <ul>
        <li>Name: {data.full_name ?? "—"}</li>
        <li>Email: {data.email ?? "—"}</li>
        <li>Phone: {data.phone ?? "—"}</li>
        <li>Location: {data.location ?? "—"}</li>
      </ul>

      <h3>Skills</h3>
      {data.skills.length > 0 ? (
        <ul>
          {data.skills.map((skill) => (
            <li key={skill}>{skill}</li>
          ))}
        </ul>
      ) : (
        <p>—</p>
      )}

      <h3>Education</h3>
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
        <p>—</p>
      )}

      <h3>Work Experience</h3>
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
        <p>—</p>
      )}

      <h3>Projects</h3>
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
        <p>—</p>
      )}

      <h3>Certifications</h3>
      {data.certifications.length > 0 ? (
        <ul>
          {data.certifications.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>—</p>
      )}

      <h3>Languages</h3>
      {data.languages.length > 0 ? (
        <ul>
          {data.languages.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>—</p>
      )}
    </div>
  );
}

export default ParsedResumeView;
