import { renderRichText } from "../utils/formatText.jsx";

export default function ChatMessage({ message }) {
  const isUser = message.role === "user";
  const classes = [
    "bubble",
    isUser ? "bubble--user" : "bubble--assistant",
    message.emergency ? "bubble--emergency" : "",
  ].join(" ");

  return (
    <div className={`message ${isUser ? "message--user" : "message--assistant"}`}>
      {!isUser && (
        <div className={`message__avatar message__avatar--ai ${message.emergency ? "message__avatar--alert" : ""}`} aria-hidden="true">
          {message.emergency ? "!" : "✚"}
        </div>
      )}
      {/* lang attribute lets CSS pick the Bangla font and helps screen readers */}
      <div className={classes} lang={message.lang || "en"}>
        {message.emergency && <div className="bubble__label">Emergency warning · জরুরি সতর্কতা</div>}
        {isUser ? <p>{message.content}</p> : renderRichText(message.content)}
      </div>
    </div>
  );
}
