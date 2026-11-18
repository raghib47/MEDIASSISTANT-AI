const STATUS_TEXT = {
  checking: "Connecting…",
  online: "Online",
  offline: "Backend offline",
  loading: "Model starting…",
  model_error: "AI model offline",
};

export default function Navbar({ status, onReset, resetDisabled }) {
  return (
    <header className="navbar">
      <div className="navbar__brand">
        <div className="navbar__logo" aria-hidden="true">
          <svg viewBox="0 0 64 64" width="26" height="26">
            <path d="M26 14h12v12h12v12H38v12H26V38H14V26h12z" fill="#fff" />
          </svg>
        </div>
        <div>
          <h1 className="navbar__title">MediAssist AI</h1>
          <p className="navbar__tagline">AI-Powered Health Assistant</p>
        </div>
      </div>

      <div className="navbar__actions">
        <span className={`status status--${status}`} role="status">
          <span className="status__dot" aria-hidden="true" />
          {STATUS_TEXT[status]}
        </span>
        <button type="button" className="btn btn--ghost" onClick={onReset} disabled={resetDisabled}>
          ↺ New chat / নতুন চ্যাট
        </button>
      </div>
    </header>
  );
}
