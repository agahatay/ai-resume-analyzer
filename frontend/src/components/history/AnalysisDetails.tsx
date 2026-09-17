import { useEffect, useState } from "react";
import { getAnalysisDetail } from "../../services/analysisService";
import type { AnalysisDetailResponse } from "../../types/analysisHistory";
import ParsedResumeView from "../ParsedResumeView";
import ParsedJobDescriptionView from "../ParsedJobDescriptionView";
import ScoreOverview from "../dashboard/ScoreOverview";
import SemanticMatches from "../dashboard/SemanticMatches";
import Card from "../ui/Card";
import Spinner from "../ui/Spinner";
import ErrorBanner from "../ui/ErrorBanner";
import { ChipList } from "../ui/Chip";
import "../dashboard/dashboard.css";
import "./history.css";

interface AnalysisDetailsProps {
  analysisId: string;
  onBack: () => void;
}

type LoadState = "loading" | "success" | "error";

function formatDate(iso: string): string {
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? iso : date.toLocaleString();
}

/**
 * Phase 11: renders one historical analysis from
 * GET /api/analyses/{analysis_id} only - the matcher is never rerun.
 *
 * This is deliberately NOT the live-match <AnalysisDashboard> reused
 * as-is: that component (and its Recommendations/*Analysis subcomponents)
 * requires the full deterministic breakdown - matched_skills,
 * education_match, experience_match, certification_match, language_match
 * - and only the three numeric scores plus the "missing" lists were ever
 * persisted per analysis (see analysis_repository.save_analysis_result).
 * Reconstructing the rest would mean either re-running the matcher
 * (explicitly disallowed for this endpoint) or fabricating data that was
 * never actually stored. So this view reuses every dashboard building
 * block that genuinely is backed by persisted data (ScoreOverview,
 * SemanticMatches, ParsedResumeView, ParsedJobDescriptionView) and
 * presents the persisted summary/missing-lists directly, rather than
 * force-fitting incomplete data into the live dashboard's full shape.
 */
function AnalysisDetails({ analysisId, onBack }: AnalysisDetailsProps) {
  const [state, setState] = useState<LoadState>("loading");
  const [data, setData] = useState<AnalysisDetailResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    setState("loading");
    setErrorMessage("");
    setData(null);

    getAnalysisDetail(analysisId)
      .then((response) => {
        if (cancelled) return;
        setData(response);
        setState("success");
      })
      .catch((error) => {
        if (cancelled) return;
        setErrorMessage(error instanceof Error ? error.message : "Failed to load this analysis.");
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  return (
    <div className="dashboard">
      <div className="dash-header">
        <h2 style={{ margin: 0 }}>Analysis Details</h2>
        <button type="button" className="ui-button ui-button-secondary" onClick={onBack}>
          Back to History
        </button>
      </div>

      {state === "loading" && (
        <Card>
          <Spinner label="Loading analysis..." />
        </Card>
      )}

      {state === "error" && (
        <Card>
          <ErrorBanner message={errorMessage} />
        </Card>
      )}

      {state === "success" && data && (
        <>
          <p className="ui-field-hint" style={{ margin: 0 }}>
            Analyzed on {formatDate(data.created_at)}
          </p>

          <ScoreOverview
            deterministicScore={data.deterministic_score}
            semanticScore={data.semantic_score}
            combinedScore={data.combined_score}
            formula={data.combined_score_formula}
          />

          <Card title="Summary">
            <p style={{ margin: 0 }}>{data.summary}</p>
          </Card>

          <Card title="Gaps Identified In This Analysis">
            <h4>Missing Required Skills</h4>
            <ChipList
              items={data.recommendations.missing_required_skills}
              variant="missing"
              emptyLabel="None - every required skill was matched."
            />
            <h4>Missing Preferred Skills</h4>
            <ChipList
              items={data.recommendations.missing_preferred_skills}
              variant="missing"
              emptyLabel="None - every preferred skill was matched."
            />
            <h4>Missing Certifications</h4>
            <ChipList
              items={data.recommendations.missing_certifications}
              variant="missing"
              emptyLabel="None - every required certification was matched."
            />
            <h4>Missing Languages</h4>
            <ChipList
              items={data.recommendations.missing_languages}
              variant="missing"
              emptyLabel="None - every required language was matched."
            />
          </Card>

          <SemanticMatches
            matches={data.semantic_matches}
            modelName={data.semantic_model_name}
            similarityThreshold={data.semantic_similarity_threshold}
          />

          <Card title="Resume">
            <ParsedResumeView data={data.resume} />
          </Card>

          <Card title="Job Description">
            <ParsedJobDescriptionView data={data.job_description} />
          </Card>
        </>
      )}
    </div>
  );
}

export default AnalysisDetails;
