import Card from "./Card";
import MatchList from "./MatchList";
import type { LanguageMatchResult } from "../../types/match";

interface LanguagesAnalysisProps {
  languageMatch: LanguageMatchResult;
}

function LanguagesAnalysis({ languageMatch }: LanguagesAnalysisProps) {
  return (
    <Card title="Languages">
      <div className="dash-grid-2">
        <div>
          <p className="dash-subheading">
            Matched <span className="dash-count">({languageMatch.matched.length})</span>
          </p>
          <MatchList items={languageMatch.matched} variant="matched" emptyLabel="No languages matched." />
        </div>
        <div>
          <p className="dash-subheading">
            Missing <span className="dash-count">({languageMatch.missing.length})</span>
          </p>
          <MatchList items={languageMatch.missing} variant="missing" emptyLabel="No languages missing." />
        </div>
      </div>
    </Card>
  );
}

export default LanguagesAnalysis;
