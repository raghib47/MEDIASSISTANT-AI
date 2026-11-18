import { useEffect, useRef } from "react";
import ChatMessage from "./ChatMessage.jsx";
import TypingIndicator from "./TypingIndicator.jsx";

const SUGGESTIONS = [
  "What are common symptoms of dehydration?",
  "How can I prevent seasonal flu?",
  "ডায়াবেটিসের সাধারণ লক্ষণ কী?",
  "উচ্চ রক্তচাপ নিয়ন্ত্রণে কী করা উচিত?",
];

export default function ChatWindow({ messages, loading, error, onRetry, onDismissError, onSuggestion, showSuggestions }) {
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading, error]);

  return (
    <main className="chat-window" aria-live="polite">
      <div className="chat-window__inner">
        {messages.map((m) => <ChatMessage key={m.id} message={m} />)}

        {showSuggestions && (
          <div className="suggestions" aria-label="Suggested questions">
            {SUGGESTIONS.map((s) => (
              <button key={s} type="button" className="chip" lang={/[\u0980-\u09FF]/.test(s) ? "bn" : "en"} onClick={() => onSuggestion(s)}>
                {s}
              </button>
            ))}
          </div>
        )}

        {loading && <TypingIndicator />}

        {error && (
          <div className="error-banner" role="alert">
            <span>{error.text}</span>
            <div className="error-banner__actions">
              {error.retryable && (
                <button type="button" className="btn btn--small" onClick={onRetry}>Retry / আবার চেষ্টা করুন</button>
              )}
              <button type="button" className="btn btn--small btn--ghost" onClick={onDismissError}>Dismiss</button>
            </div>
          </div>
        )}
        <div ref={endRef} />
      </div>
    </main>
  );
}
