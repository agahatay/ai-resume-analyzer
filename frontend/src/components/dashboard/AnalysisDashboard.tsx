import "./dashboard.css";
import ScoreOverview from "./ScoreOverview";
import SkillsAnalysis from "./SkillsAnalysis";
import SemanticMatches from "./SemanticMatches";
import EducationAnalysis from "./EducationAnalysis";
import ExperienceAnalysis from "./ExperienceAnalysis";
import CertificationsAnalysis from "./CertificationsAnalysis";
import LanguagesAnalysis from "./LanguagesAnalysis";
import Recommendations from "./Recommendations";
import Spinner from "../ui/Spinner";
import type { ResumeMatchResponse } from "../../types/match";
import type { ParsedResume } from "../../types/resume";
import type { ParsedJobDescription } from "../../types/jobDescription";

interface AnalysisDashboardProps {
  data: ResumeMatchResponse;
  resume: ParsedResume;
  jobDescription: ParsedJobDescription;
  onAnalyzeAgain: () => void;
  isAnalyzing: boolean;
}

function AnalysisDashboard({ data, resume, jobDescription, onAnalyzeAgain, isAnalyzing }: AnalysisDashboardProps) {
  return (
    <div className="dashboard">
      <div className="dash-header">
        <h2 style={{ margin: 0 }}>5. Analysis Dashboard</h2>
        <button
          className="ui-button ui-button-secondary"
          onClick={onAnalyzeAgain}
          disabled={isAnalyzing}
          aria-label="Re-run matching analysis"
        >
          {isAnalyzing ? <Spinner label="Analyzing..." /> : "Analyze Again"}
        </button>
      </div>

      <ScoreOverview
        deterministicScore={data.deterministic_match.score}
        semanticScore={data.semantic_match.semantic_score}
        combinedScore={data.combined_match_score}
        formula={data.combined_score_formula}
      />

      <SkillsAnalysis
        matchedRequiredSkills={data.matched_skills}
        missingRequiredSkills={data.missing_required_skills}
        matchedPreferredSkills={data.matched_preferred_skills}
        missingPreferredSkills={data.missing_preferred_skills}
      />

      <SemanticMatches
        matches={data.semantic_match.semantic_matches}
        modelName={data.semantic_match.model_name}
        similarityThreshold={data.semantic_match.similarity_threshold}
      />

      <EducationAnalysis
        educationMatch={data.education_match}
        resumeEducation={resume.education}
        jobRequirements={jobDescription.education_requirements}
      />

      <ExperienceAnalysis
        experienceMatch={data.experience_match}
        resumeExperience={resume.work_experience}
        jobRequirements={jobDescription.experience_requirements}
      />

      <CertificationsAnalysis certificationMatch={data.certification_match} />

      <LanguagesAnalysis languageMatch={data.language_match} />

      <Recommendations data={data} />
    </div>
  );
}

export default AnalysisDashboard;
