export default function TypingIndicator() {
  return (
    <div className="message message--assistant" aria-live="polite">
      <div className="message__avatar message__avatar--ai" aria-hidden="true">✚</div>
      <div className="bubble bubble--assistant typing" aria-label="MediAssist AI is typing">
        <span /><span /><span />
      </div>
    </div>
  );
}
