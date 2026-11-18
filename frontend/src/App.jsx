import { useCallback, useEffect, useRef, useState } from "react";
import Navbar from "./components/Navbar.jsx";
import ChatWindow from "./components/ChatWindow.jsx";
import ChatInput from "./components/ChatInput.jsx";
import EmergencyAlert from "./components/EmergencyAlert.jsx";
import { ApiError, checkHealth, sendChatMessage } from "./services/api.js";
import { detectLanguage } from "./utils/language.js";
import "./styles/main.css";

const MAX_HISTORY = 8; // recent messages sent to the backend (limits token usage)

const WELCOME = {
  id: "welcome",
  role: "assistant",
  lang: "en",
  isWelcome: true,
  content:
    "Hello! I'm **MediAssist AI**. I can explain general health topics, common symptoms and medical terms .\n\n" +
    "আসসালামু আলাইকুম! আপনি আমাকে সাধারণ স্বাস্থ্য বিষয়ে প্রশ্ন করতে পারেন।\n\n" +
    "I'm an AI, not a doctor, and I can't diagnose or prescribe. In an emergency, call your local emergency number right away.",
};

// Localized text for errors that happen before/without a server message.
const ERR = {
  network: {
    en: "Can't reach the server. Check that the backend is running and try again.",
    bn: "সার্ভারের সাথে সংযোগ করা যাচ্ছে না। ব্যাকএন্ড চালু আছে কিনা দেখে আবার চেষ্টা করুন।",
  },
  timeout: {
    en: "The request took too long. Please try again.",
    bn: "অনুরোধটি সম্পন্ন হতে অনেক সময় লাগছে। আবার চেষ্টা করুন।",
  },
  unknown: {
    en: "Something went wrong. Please try again.",
    bn: "কিছু একটা সমস্যা হয়েছে। আবার চেষ্টা করুন।",
  },
};

let idCounter = 0;
const nextId = () => `m${Date.now()}-${idCounter++}`;

export default function App() {
  const [messages, setMessages] = useState([WELCOME]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null); // { text, retryText, retryable }
  const [backendStatus, setBackendStatus] = useState("checking");
  const [emergencyActive, setEmergencyActive] = useState(false);
  const abortRef = useRef(null);

  const refreshHealth = useCallback(async () => {
    const health = await checkHealth();
    if (!health) setBackendStatus("offline");
    else if (health.llm_state === "ready") setBackendStatus("online");
    else if (health.llm_state === "loading") setBackendStatus("loading"); // local model still starting
    else setBackendStatus("model_error"); // model server not running / not configured
  }, []);

  useEffect(() => { refreshHealth(); }, [refreshHealth]);

  // While the local model is starting up, re-check every 5 seconds.
  useEffect(() => {
    if (backendStatus !== "loading") return undefined;
    const timer = setTimeout(refreshHealth, 5000);
    return () => clearTimeout(timer);
  }, [backendStatus, refreshHealth]);

  const send = useCallback(
    async (text, { isRetry = false } = {}) => {
      const trimmed = text.trim();
      if (!trimmed || loading) return;
      const lang = detectLanguage(trimmed);

      // On retry the failed user bubble is already the last message; don't duplicate it.
      const base = isRetry ? messages : [...messages, { id: nextId(), role: "user", content: trimmed, lang }];
      // History = everything before the new user message (no welcome/error bubbles), trimmed.
      const history = base
        .slice(0, -1)
        .filter((m) => !m.isWelcome)
        .slice(-MAX_HISTORY)
        .map(({ role, content }) => ({ role, content }));

      setMessages(base);
      setError(null);
      setLoading(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        const data = await sendChatMessage({ message: trimmed, history, signal: controller.signal });
        setMessages((prev) => [
          ...prev,
          { id: nextId(), role: "assistant", content: data.reply, lang: data.language, emergency: data.emergency },
        ]);
        setEmergencyActive(Boolean(data.emergency));
        setBackendStatus("online");
      } catch (err) {
        if (err.name === "AbortError") return; // user pressed "New chat"
        let text;
        if (err instanceof ApiError && err.kind === "server") text = err.message; // already localized by the backend
        else if (err instanceof ApiError) text = ERR[err.kind][lang];
        else text = ERR.unknown[lang];
        if (err instanceof ApiError && err.kind === "network") setBackendStatus("offline");
        else if (err instanceof ApiError && err.status === 503) refreshHealth(); // model loading / server down
        setError({ text, retryText: trimmed, retryable: true });
      } finally {
        if (abortRef.current === controller) abortRef.current = null;
        setLoading(false);
      }
    },
    [messages, loading],
  );

  const handleReset = () => {
    abortRef.current?.abort();
    setMessages([WELCOME]);
    setError(null);
    setLoading(false);
    setEmergencyActive(false);
    refreshHealth();
  };

  return (
    <div className="app">
      <Navbar status={backendStatus} onReset={handleReset} resetDisabled={messages.length <= 1 && !error} />
      {emergencyActive && <EmergencyAlert onDismiss={() => setEmergencyActive(false)} />}
      <ChatWindow
        messages={messages}
        loading={loading}
        error={error}
        showSuggestions={messages.length === 1}
        onSuggestion={(s) => send(s)}
        onRetry={() => error && send(error.retryText, { isRetry: true })}
        onDismissError={() => setError(null)}
      />
      <ChatInput onSend={(t) => send(t)} disabled={loading} />
    </div>
  );
}
