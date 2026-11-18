const EMERGENCY_NUMBER = import.meta.env.VITE_EMERGENCY_NUMBER || "999";

// Sticky banner shown while the latest answer came from the emergency safety rules.
export default function EmergencyAlert({ onDismiss }) {
  return (
    <div className="emergency-alert" role="alert">
      <div className="emergency-alert__text">
        <strong>⚠️ Possible emergency · সম্ভাব্য জরুরি অবস্থা</strong>
        <span>
          Get urgent medical help now. জরুরি চিকিৎসা সহায়তা নিন।
        </span>
      </div>
      <a className="btn btn--danger" href={`tel:${EMERGENCY_NUMBER}`}>
        📞 Call {EMERGENCY_NUMBER}
      </a>
      <button type="button" className="emergency-alert__close" onClick={onDismiss} aria-label="Dismiss warning">
        ×
      </button>
    </div>
  );
}
