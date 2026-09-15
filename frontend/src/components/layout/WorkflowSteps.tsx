import "./layout.css";

export type StepStatus = "complete" | "current" | "upcoming";

export interface WorkflowStep {
  label: string;
  status: StepStatus;
}

interface WorkflowStepsProps {
  steps: WorkflowStep[];
}

function WorkflowSteps({ steps }: WorkflowStepsProps) {
  return (
    <ol className="workflow-steps" aria-label="Analysis workflow">
      {steps.map((step, index) => (
        <li
          key={step.label}
          className={`workflow-step workflow-step-${step.status}`}
          aria-current={step.status === "current" ? "step" : undefined}
        >
          <span className="workflow-step-marker" aria-hidden="true">
            {step.status === "complete" ? "✓" : index + 1}
          </span>
          <span className="workflow-step-label">{step.label}</span>
          {index < steps.length - 1 && (
            <span
              className="workflow-step-connector"
              aria-hidden="true"
              style={step.status === "complete" ? { background: "var(--color-success)" } : undefined}
            />
          )}
        </li>
      ))}
    </ol>
  );
}

export default WorkflowSteps;
