import { useEffect, useState } from "react";
import { listAnalyses } from "../../services/analysisService";
import type { AnalysisListResponse } from "../../types/analysisHistory";
import AnalysisHistoryCard from "./AnalysisHistoryCard";
import Card from "../ui/Card";
import Spinner from "../ui/Spinner";
import ErrorBanner from "../ui/ErrorBanner";
import EmptyState from "../ui/EmptyState";
import "./history.css";

const PAGE_SIZE = 10;

type LoadState = "loading" | "success" | "error";

interface AnalysisHistoryProps {
  onViewDetails: (analysisId: string) => void;
  onAnalyzeResume: () => void;
}

/**
 * Phase 11: the authenticated user's own analysis history - fetched from
 * GET /api/analyses (never recomputed). Ownership is enforced entirely
 * server-side via the caller's JWT; this component just renders whatever
 * page of results comes back.
 */
function AnalysisHistory({ onViewDetails, onAnalyzeResume }: AnalysisHistoryProps) {
  const [page, setPage] = useState(1);
  const [state, setState] = useState<LoadState>("loading");
  const [data, setData] = useState<AnalysisListResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    let cancelled = false;
    // Resets the view back to "loading" on every page change, not just on
    // mount (the initial state is already "loading") - intentional, and
    // safe under React 18's automatic batching of same-tick setState calls.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState("loading");
    setErrorMessage("");

    listAnalyses(page, PAGE_SIZE)
      .then((response) => {
        if (cancelled) return;
        setData(response);
        setState("success");
      })
      .catch((error) => {
        if (cancelled) return;
        setErrorMessage(error instanceof Error ? error.message : "Failed to load analysis history.");
        setState("error");
      });

    return () => {
      cancelled = true;
    };
  }, [page]);

  if (state === "loading") {
    return (
      <Card title="Recent Analyses">
        <Spinner label="Loading analysis history..." />
      </Card>
    );
  }

  if (state === "error") {
    return (
      <Card title="Recent Analyses">
        <ErrorBanner message={errorMessage} />
      </Card>
    );
  }

  if (!data || data.items.length === 0) {
    return (
      <Card title="Recent Analyses">
        <EmptyState
          title="No analyses yet."
          message="Match a resume against a job description to see it show up here."
        />
        <div style={{ marginTop: "0.75rem" }}>
          <button type="button" className="ui-button ui-button-primary" onClick={onAnalyzeResume}>
            Analyze a Resume
          </button>
        </div>
      </Card>
    );
  }

  return (
    <Card title="Recent Analyses">
      <p className="ui-field-hint" style={{ marginTop: 0 }}>
        {data.total} total {data.total === 1 ? "analysis" : "analyses"}
      </p>

      <div className="history-card-list">
        {data.items.map((item) => (
          <AnalysisHistoryCard key={item.analysis_id} item={item} onViewDetails={onViewDetails} />
        ))}
      </div>

      {data.total_pages > 1 && (
        <div className="history-pagination">
          <button
            type="button"
            className="ui-button ui-button-secondary"
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
          >
            Previous
          </button>
          <span className="ui-field-hint">
            Page {data.page} of {data.total_pages}
          </span>
          <button
            type="button"
            className="ui-button ui-button-secondary"
            onClick={() => setPage((current) => Math.min(data.total_pages, current + 1))}
            disabled={page >= data.total_pages}
          >
            Next
          </button>
        </div>
      )}
    </Card>
  );
}

export default AnalysisHistory;
