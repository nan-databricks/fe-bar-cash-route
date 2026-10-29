import { useState } from "react";
import { Send, Sparkles } from "lucide-react";
import { askGenie, type GenieResponse } from "../data/api";

const SUGGESTIONS = [
  "Which 10 ATMs are most at risk of cash-out tomorrow?",
  "Compare optimized vs baseline CIT cost per depot",
  "How much idle cash is sitting in branches in Nam Phong?",
  "Which vans have the most stops on the optimized plan?",
];

interface Turn {
  question: string;
  answer?: GenieResponse;
  error?: string;
}

function fmt(v: unknown): string {
  if (v === null || v === undefined) return "—";
  const n = Number(v);
  if (typeof v !== "boolean" && v !== "" && Number.isFinite(n) && String(v).trim() !== "") {
    return Math.abs(n) >= 1000 ? n.toLocaleString("en-US", { maximumFractionDigits: 0 }) : n.toLocaleString("en-US", { maximumFractionDigits: 2 });
  }
  return String(v);
}

/** "Ask SNB Ops" — chat with the Genie space SNB Cash Ops Assistant via POST /api/genie/ask. */
export default function GeniePage() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | undefined>();
  const [busy, setBusy] = useState(false);

  const ask = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setInput("");
    setBusy(true);
    setTurns((t) => [...t, { question }]);
    try {
      const answer = await askGenie(question, conversationId);
      if (answer.conversation_id && answer.source === "genie") setConversationId(answer.conversation_id);
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, answer } : x)));
    } catch (e) {
      setTurns((t) => t.map((x, i) => (i === t.length - 1 ? { ...x, error: String(e) } : x)));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="track-page genie-page">
      <div className="page-toolbar">
        <span className="pt-title">
          <Sparkles size={16} color="#f2a900" /> Ask SNB Ops · Genie space “SNB Cash Ops Assistant”
        </span>
        {conversationId && (
          <button className="btn sm ghost" onClick={() => { setConversationId(undefined); setTurns([]); }}>
            New conversation
          </button>
        )}
      </div>

      <div className="panel genie-chat">
        <div className="panel-body genie-scroll">
          {turns.length === 0 && (
            <div className="genie-empty">
              <p>Ask a question about cash positions, forecasts, replenishment orders or CIT routes. Genie writes the SQL over the governed <code>snb_cash_ops</code> gold tables.</p>
              <div className="genie-suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="btn sm ghost" onClick={() => ask(s)}>{s}</button>
                ))}
              </div>
            </div>
          )}
          {turns.map((t, i) => (
            <div key={i} className="genie-turn">
              <div className="genie-q">{t.question}</div>
              {!t.answer && !t.error && <div className="genie-a muted">Genie is thinking…</div>}
              {t.error && <div className="genie-a error-text">{t.error}</div>}
              {t.answer && (
                <div className="genie-a">
                  <div className="genie-meta">
                    <span className={`source-chip ${t.answer.source === "genie" ? "live" : ""}`}>
                      {t.answer.source === "genie" ? "Genie · live" : "mock answer"}
                    </span>
                    {t.answer.note && <span className="hint">{t.answer.note}</span>}
                  </div>
                  {t.answer.text && <div className="genie-text">{t.answer.text}</div>}
                  {t.answer.sql && (
                    <details className="genie-sql">
                      <summary>Generated SQL</summary>
                      <pre>{t.answer.sql}</pre>
                    </details>
                  )}
                  {t.answer.columns.length > 0 && (
                    <div className="genie-table-wrap">
                      <table className="branch-table">
                        <thead>
                          <tr>{t.answer.columns.map((c) => <th key={c}>{c}</th>)}</tr>
                        </thead>
                        <tbody>
                          {t.answer.rows.slice(0, 50).map((r, ri) => (
                            <tr key={ri}>{r.map((v, ci) => <td key={ci}>{fmt(v)}</td>)}</tr>
                          ))}
                        </tbody>
                      </table>
                      {t.answer.rows.length > 50 && <div className="hint">Showing 50 of {t.answer.rows.length} rows</div>}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
        <div className="genie-input">
          <input
            className="select-inline"
            value={input}
            placeholder="Ask about cash-out risk, idle cash, route cost…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask(input)}
            disabled={busy}
          />
          <button className="btn primary" onClick={() => ask(input)} disabled={busy || !input.trim()}>
            <Send size={14} /> Ask
          </button>
        </div>
      </div>
    </div>
  );
}
