// All communication with the FastAPI backend. NO secrets here: the Hugging Face token
// only ever exists on the server.
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
// Local models can be slow (CPU). Keep this a bit above SERVER_TIMEOUT_SECONDS in backend/.env
const REQUEST_TIMEOUT_MS = Number(import.meta.env.VITE_REQUEST_TIMEOUT_MS) || 200_000;

export class ApiError extends Error {
  // kind: "network" (server unreachable) | "timeout" | "server" (backend returned an error)
  constructor(message, { kind = "server", status = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.status = status;
  }
}

async function request(path, options = {}, externalSignal) {
  const controller = new AbortController();
  let timedOut = false;
  const onAbort = () => controller.abort();
  externalSignal?.addEventListener("abort", onAbort);
  const timer = setTimeout(() => { timedOut = true; controller.abort(); }, REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(`${API_BASE_URL}${path}`, { ...options, signal: controller.signal });
    let data = null;
    try { data = await response.json(); } catch { /* non-JSON body */ }

    if (!response.ok) {
      const detail = typeof data?.detail === "string" ? data.detail : null;
      throw new ApiError(detail || `Server error (${response.status})`, { kind: "server", status: response.status });
    }
    return data;
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err.name === "AbortError") {
      if (timedOut) throw new ApiError("Request timed out", { kind: "timeout" });
      throw err; // aborted on purpose by the app (e.g. "New chat"): caller ignores it
    }
    throw new ApiError("Cannot reach the server", { kind: "network" });
  } finally {
    clearTimeout(timer);
    externalSignal?.removeEventListener("abort", onAbort);
  }
}

/** POST /chat -> { reply, language, emergency, source, emergency_signs } */
export function sendChatMessage({ message, history, signal }) {
  return request(
    "/chat",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    },
    signal,
  );
}

/** GET /health -> { status, llm_state: "ready"|"loading"|"failed"|"not_configured", ... } or null if unreachable */
export async function checkHealth() {
  try {
    const data = await request("/health", { method: "GET" });
    return data?.status === "ok" ? data : null;
  } catch {
    return null;
  }
}
