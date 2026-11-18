// Client-side language detection (UI only: styling and localized messages).
// The backend does its own detection to decide the model's reply language.
const BANGLA = /[\u0980-\u09FF]/g;
const LATIN = /[A-Za-z]/g;

export function detectLanguage(text) {
  const bn = (text.match(BANGLA) || []).length;
  const en = (text.match(LATIN) || []).length;
  if (bn === 0) return "en";
  return bn / (bn + en) >= 0.4 ? "bn" : "en";
}
