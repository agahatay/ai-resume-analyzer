import Card from "../ui/Card";
import { ChipList } from "../ui/Chip";
import type { CertificationMatchResult } from "../../types/match";

interface CertificationsAnalysisProps {
  certificationMatch: CertificationMatchResult;
}

function CertificationsAnalysis({ certificationMatch }: CertificationsAnalysisProps) {
  return (
    <Card title="Certifications">
      <div className="dash-grid-2">
        <div>
          <p className="dash-subheading">
            Matched <span className="dash-count">({certificationMatch.matched.length})</span>
          </p>
          <ChipList items={certificationMatch.matched} variant="matched" emptyLabel="No certifications matched." />
        </div>
        <div>
          <p className="dash-subheading">
            Missing <span className="dash-count">({certificationMatch.missing.length})</span>
          </p>
          <ChipList items={certificationMatch.missing} variant="missing" emptyLabel="No certifications missing." />
        </div>
      </div>
    </Card>
  );
}

export default CertificationsAnalysis;
