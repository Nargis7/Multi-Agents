import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import {
  Search,
  BookOpen,
  PenLine,
  ShieldCheck,
  Check,
  Copy,
  Download,
  AlertCircle,
} from "lucide-react";

const API_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000/api/research";

const STEPS = [
  { icon: Search, title: "Search", idle: "Finds sources" },
  { icon: BookOpen, title: "Read", idle: "Scrapes the best page" },
  { icon: PenLine, title: "Write", idle: "Drafts the report" },
  { icon: ShieldCheck, title: "Review", idle: "Scores the draft" },
];

const EXAMPLES = [
  "Latest advances in federated learning",
  "How retrieval-augmented generation works",
  "Impact of AI on software engineering jobs",
];

const TABS = [
  { id: "report", label: "Report" },
  { id: "feedback", label: "Critic's review" },
  { id: "search", label: "Search results" },
  { id: "scraped", label: "Scraped page" },
];

const parseScore = (text) => {
  const m = text.match(/Score:\s*(\d+(?:\.\d+)?)\s*\/\s*10/);
  return m ? parseFloat(m[1]) : null;
};

const countSources = (text) =>
  new Set(text.match(/https?:\/\/[^\s)\]>"']+/g) || []).size;

const mdComponents = {
  a: (props) => <a {...props} target="_blank" rel="noreferrer" />,
};

function ScoreRing({ score }) {
  const r = 50;
  const c = 2 * Math.PI * r;
  const pct = score == null ? 0 : Math.min(score / 10, 1);
  const tone = score == null ? "none" : score >= 8 ? "good" : score >= 6 ? "ok" : "low";
  return (
    <div className={`ring ring-${tone}`}>
      <svg viewBox="0 0 120 120" aria-hidden="true">
        <circle className="ring-bg" cx="60" cy="60" r={r} />
        <circle
          className="ring-fg"
          cx="60"
          cy="60"
          r={r}
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
        />
      </svg>
      <div className="ring-label">
        <strong>{score == null ? "–" : score}</strong>
        <span>out of 10</span>
      </div>
    </div>
  );
}

export default function App() {
  const [topic, setTopic] = useState("");
  const [step, setStep] = useState(0); // 0 idle, 1-4 running step, 5 finished
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [tab, setTab] = useState("report");
  const [copied, setCopied] = useState(false);

  const stats = useMemo(() => {
    if (!result) return null;
    return {
      score: parseScore(result.feedback),
      sources: countSources(result.report),
      words: result.report.split(/\s+/).filter(Boolean).length,
    };
  }, [result]);

  async function run(e) {
    e?.preventDefault();
    const q = topic.trim();
    if (!q || loading) return;

    setError("");
    setResult(null);
    setTab("report");
    setStep(1);
    setLoading(true);

    try {
      const res = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: q }),
      });
      if (!res.ok || !res.body) throw new Error(`The server answered with status ${res.status}`);

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split("\n\n");
        buffer = chunks.pop();

        for (const chunk of chunks) {
          if (!chunk.startsWith("data: ")) continue;
          const msg = JSON.parse(chunk.slice(6));
          if (msg.type === "step") setStep(msg.step);
          else if (msg.type === "result") {
            setResult(msg.data);
            setStep(5);
          } else if (msg.type === "error") throw new Error(msg.message);
        }
      }
    } catch (err) {
      setError(err.message || "Unknown error");
      setStep(0);
    } finally {
      setLoading(false);
    }
  }

  async function copyReport() {
    await navigator.clipboard.writeText(result.report);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }

  function downloadReport() {
    const blob = new Blob([result.report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "research_report.md";
    a.click();
    URL.revokeObjectURL(url);
  }

  const fill = step === 0 ? 0 : step >= 5 ? 1 : (step - 1) / (STEPS.length - 1);

  return (
    <div className="shell">
      <header className="topbar">
        <span className="logo">Relay</span>
        <span className="tagline">Four agents, one sourced report</span>
      </header>

      <section className="hero">
        <h1>What should we look into?</h1>
        <p className="lede">
          Relay searches the web, reads the best source, writes a report and has a critic review
          it. Everything runs on your machine.
        </p>

        <form className="ask" onSubmit={run}>
          <input
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Type a topic, e.g. federated learning in healthcare"
            aria-label="Research topic"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !topic.trim()}>
            {loading ? "Researching" : "Start research"}
          </button>
        </form>

        <div className="examples">
          <span>Try:</span>
          {EXAMPLES.map((ex) => (
            <button key={ex} type="button" disabled={loading} onClick={() => setTopic(ex)}>
              {ex}
            </button>
          ))}
        </div>
      </section>

      <section className="track" style={{ "--fill": fill }} aria-label="Pipeline progress">
        <div className="track-line" aria-hidden="true">
          <div className="track-fill" />
        </div>
        {STEPS.map((s, i) => {
          const n = i + 1;
          const state = step >= 5 || step > n ? "done" : loading && step === n ? "active" : "idle";
          const Icon = s.icon;
          return (
            <div className={`node node-${state}`} key={s.title}>
              <div className="node-dot">{state === "done" ? <Check size={20} /> : <Icon size={20} />}</div>
              <div className="node-title">{s.title}</div>
              <div className="node-note" aria-live="polite">
                {state === "done" ? "Done" : state === "active" ? "Working" : s.idle}
              </div>
            </div>
          );
        })}
      </section>

      {loading && (
        <p className="hint">A local model can take a minute or two per step. You can keep this tab open.</p>
      )}

      {error && (
        <div className="error" role="alert">
          <AlertCircle size={20} />
          <div>
            <strong>Research failed:</strong> {error}. Check that the API is running on port 8000,
            Ollama is started and TAVILY_API_KEY is set in your .env file.
          </div>
        </div>
      )}

      {result && stats && (
        <section className="results">
          <aside className="rail">
            <div className="panel">
              <h2>Critic's score</h2>
              <ScoreRing score={stats.score} />
              {stats.score == null && (
                <p className="muted">The critic did not return a score in the expected format.</p>
              )}
            </div>

            <div className="panel">
              <dl className="stats">
                <div>
                  <dt>Sources cited</dt>
                  <dd>{stats.sources}</dd>
                </div>
                <div>
                  <dt>Report length</dt>
                  <dd>{stats.words} words</dd>
                </div>
              </dl>
              <div className="actions">
                <button type="button" onClick={copyReport}>
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                  {copied ? "Copied" : "Copy report"}
                </button>
                <button type="button" onClick={downloadReport}>
                  <Download size={16} /> Download .md
                </button>
              </div>
            </div>
          </aside>

          <article className="reader">
            <div className="tabs" role="tablist">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  role="tab"
                  aria-selected={tab === t.id}
                  className={tab === t.id ? "tab tab-on" : "tab"}
                  onClick={() => setTab(t.id)}
                >
                  {t.label}
                </button>
              ))}
            </div>

            <div className="pane" role="tabpanel">
              {tab === "report" && (
                <div className="prose">
                  <ReactMarkdown components={mdComponents}>{result.report}</ReactMarkdown>
                </div>
              )}
              {tab === "feedback" && (
                <div className="prose">
                  <ReactMarkdown components={mdComponents}>{result.feedback}</ReactMarkdown>
                </div>
              )}
              {tab === "search" && <pre className="raw">{result.search_results}</pre>}
              {tab === "scraped" && <pre className="raw">{result.scraped_content}</pre>}
            </div>
          </article>
        </section>
      )}
    </div>
  );
}