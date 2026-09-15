import { useEffect, useState } from "react";
import StatusBadge from "../components/StatusBadge";
import { getHealth } from "../services/healthService";

function HomePage() {
  const [status, setStatus] = useState<string>("checking...");

  useEffect(() => {
    getHealth()
      .then((health) => setStatus(health.status))
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <main>
      <h1>AI Resume Analyzer</h1>
      <StatusBadge status={status} />
    </main>
  );
}

export default HomePage;
