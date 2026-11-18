import { Fragment } from "react";

// Minimal, XSS-safe formatter for model replies. It builds React elements (never raw HTML)
// and supports only: paragraphs, "-"/"*" bullets, "1." numbered lists, **bold**, "#" headings.

function renderInline(text, keyPrefix) {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) => {
    const isBold = part.length > 4 && part.startsWith("**") && part.endsWith("**");
    return isBold ? (
      <strong key={`${keyPrefix}-${i}`}>{part.slice(2, -2)}</strong>
    ) : (
      <Fragment key={`${keyPrefix}-${i}`}>{part}</Fragment>
    );
  });
}

const BULLET = /^\s*[-*•]\s+(.*)$/;
const NUMBERED = /^\s*(?:\d+|[০-৯]+)[.)]\s+(.*)$/;
const HEADING = /^\s*#{1,6}\s+(.*)$/;

export function renderRichText(text) {
  const blocks = [];
  let paragraph = [];
  let list = null; // { ordered: boolean, items: string[] }

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "p", text: paragraph.join(" ") });
      paragraph = [];
    }
  };
  const flushList = () => {
    if (list) {
      blocks.push({ type: list.ordered ? "ol" : "ul", items: list.items });
      list = null;
    }
  };

  for (const rawLine of text.replace(/\r/g, "").split("\n")) {
    const line = rawLine.trimEnd();
    let m;
    if (!line.trim()) {
      flushParagraph();
      flushList();
    } else if ((m = line.match(HEADING))) {
      flushParagraph();
      flushList();
      blocks.push({ type: "h", text: m[1] });
    } else if ((m = line.match(BULLET))) {
      flushParagraph();
      if (!list || list.ordered) { flushList(); list = { ordered: false, items: [] }; }
      list.items.push(m[1]);
    } else if ((m = line.match(NUMBERED))) {
      flushParagraph();
      if (!list || !list.ordered) { flushList(); list = { ordered: true, items: [] }; }
      list.items.push(m[1]);
    } else {
      flushList();
      paragraph.push(line.trim());
    }
  }
  flushParagraph();
  flushList();

  return blocks.map((b, i) => {
    if (b.type === "p") return <p key={i}>{renderInline(b.text, i)}</p>;
    if (b.type === "h") return <p key={i}><strong>{renderInline(b.text, i)}</strong></p>;
    const Tag = b.type;
    return (
      <Tag key={i}>
        {b.items.map((item, j) => <li key={j}>{renderInline(item, `${i}-${j}`)}</li>)}
      </Tag>
    );
  });
}
