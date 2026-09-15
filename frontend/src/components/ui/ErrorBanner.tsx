import "./ui.css";

interface ErrorBannerProps {
  message: string;
}

function ErrorBanner({ message }: ErrorBannerProps) {
  return (
    <div className="ui-error-banner" role="alert">
      <span className="ui-error-banner-icon" aria-hidden="true">
        ⚠
      </span>
      <span>{message}</span>
    </div>
  );
}

export default ErrorBanner;
