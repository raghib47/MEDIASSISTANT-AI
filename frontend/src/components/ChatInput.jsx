import { useEffect, useRef, useState } from "react";

const MAX_CHARS = Number(import.meta.env.VITE_MAX_MESSAGE_CHARS) || 1500;

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState("");
  const textareaRef = useRef(null);

  // Auto-grow the textarea up to a limit
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`;
  }, [text]);

  const submit = () => {
    const value = text.trim();
    if (!value || disabled) return;
    onSend(value);
    setText("");
  };

  const handleKeyDown = (e) => {
    // Don't send while an IME (e.g. Avro/Bangla keyboards) is composing a word.
    if (e.nativeEvent.isComposing || e.keyCode === 229) return;
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const nearLimit = text.length > MAX_CHARS * 0.85;

  return (
    <div className="chat-input">
      <div className="chat-input__row">
        <textarea
          ref={textareaRef}
          className="chat-input__field"
          value={text}
          rows={1}
          maxLength={MAX_CHARS}
          placeholder="Ask a health question… / স্বাস্থ্য বিষয়ে প্রশ্ন লিখুন…"
          aria-label="Message"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <button
          type="button"
          className="btn btn--primary chat-input__send"
          onClick={submit}
          disabled={disabled || !text.trim()}
          aria-label="Send message"
        >
          Send ➤
        </button>
      </div>
      <div className="chat-input__meta">
        <span>
          MediAssist AI shares general information only. It is not a doctor and can make mistakes.
          এটি ডাক্তার নয়, ভুল হতে পারে।
        </span>
        {nearLimit && <span className="chat-input__count">{text.length}/{MAX_CHARS}</span>}
      </div>
    </div>
  );
}
