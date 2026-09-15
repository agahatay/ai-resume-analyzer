import type { ParsedJobDescription } from "../types/jobDescription";
import { ChipList } from "./ui/Chip";

interface ParsedJobDescriptionViewProps {
  data: ParsedJobDescription;
}

function ParsedJobDescriptionView({ data }: ParsedJobDescriptionViewProps) {
  return (
    <div>
      <h4>Job Title</h4>
      <p>{data.job_title ?? "—"}</p>

      <h4>Required Skills</h4>
      <ChipList items={data.required_skills} variant="neutral" emptyLabel="No required skills detected." />

      <h4>Preferred Skills</h4>
      <ChipList items={data.preferred_skills} variant="neutral" emptyLabel="No preferred skills detected." />

      <h4>Education Requirements</h4>
      <ChipList
        items={data.education_requirements}
        variant="neutral"
        emptyLabel="No education requirements detected."
      />

      <h4>Experience Requirements</h4>
      <ChipList
        items={data.experience_requirements}
        variant="neutral"
        emptyLabel="No experience requirements detected."
      />

      <h4>Certifications</h4>
      <ChipList items={data.certifications} variant="neutral" emptyLabel="No certifications detected." />

      <h4>Languages</h4>
      <ChipList items={data.languages} variant="neutral" emptyLabel="No languages detected." />
    </div>
  );
}

export default ParsedJobDescriptionView;
