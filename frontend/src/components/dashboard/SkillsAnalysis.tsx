import Card from "./Card";
import MatchList from "./MatchList";

interface SkillsAnalysisProps {
  matchedRequiredSkills: string[];
  missingRequiredSkills: string[];
  matchedPreferredSkills: string[];
  missingPreferredSkills: string[];
}

function SkillsAnalysis({
  matchedRequiredSkills,
  missingRequiredSkills,
  matchedPreferredSkills,
  missingPreferredSkills,
}: SkillsAnalysisProps) {
  return (
    <Card title="Skills Analysis">
      <div className="dash-grid-2">
        <div>
          <p className="dash-subheading">
            Matched Required Skills <span className="dash-count">({matchedRequiredSkills.length})</span>
          </p>
          <MatchList items={matchedRequiredSkills} variant="matched" emptyLabel="No required skills matched." />
        </div>
        <div>
          <p className="dash-subheading">
            Missing Required Skills <span className="dash-count">({missingRequiredSkills.length})</span>
          </p>
          <MatchList items={missingRequiredSkills} variant="missing" emptyLabel="No required skills missing." />
        </div>
        <div>
          <p className="dash-subheading">
            Matched Preferred Skills <span className="dash-count">({matchedPreferredSkills.length})</span>
          </p>
          <MatchList items={matchedPreferredSkills} variant="matched" emptyLabel="No preferred skills matched." />
        </div>
        <div>
          <p className="dash-subheading">
            Missing Preferred Skills <span className="dash-count">({missingPreferredSkills.length})</span>
          </p>
          <MatchList items={missingPreferredSkills} variant="missing" emptyLabel="No preferred skills missing." />
        </div>
      </div>
    </Card>
  );
}

export default SkillsAnalysis;
