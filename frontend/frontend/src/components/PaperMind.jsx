import { useState, useRef, useEffect, useCallback } from "react";
import {
  Search, Upload, FileText, ExternalLink, Users, Calendar,
  Sparkles, Loader2, AlertCircle, Download, MessageSquare,
  Send, BookOpen, ChevronDown, ChevronUp, X, Brain, Quote
} from "lucide-react";

const API_BASE = "http://localhost:8000";

// ── Helpers ──────────────────────────────────────────────────────────────────

function sourceBadge(source) {
  const map = {
    arxiv: { bg: "bg-orange-100 text-orange-800 border-orange-200", label: "arXiv" },
    semantic_scholar: { bg: "bg-sky-100 text-sky-800 border-sky-200", label: "S2" },
  };
  return map[source] || { bg: "bg-stone-100 text-stone-700 border-stone-200", label: source };
}

function scoreColor(score) {
  if (score >= 0.8) return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (score >= 0.6) return "text-amber-700 bg-amber-50 border-amber-200";
  return "text-rose-700 bg-rose-50 border-rose-200";
}

// Render inline citation markers [1] as superscript chips
function AnswerText({ text }) {
  const parts = text.split(/(\[\d+\])/g);
  return (
    <span>
      {parts.map((p, i) => {
        const m = p.match(/^\[(\d+)\]$/);
        if (m) return (
          <sup key={i} className="inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-amber-400 text-stone-900 rounded-full mx-0.5 align-super leading-none">
            {m[1]}
          </sup>
        );
        return <span key={i}>{p}</span>;
      })}
    </span>
  );
}

// ── Paper Card ────────────────────────────────────────────────────────────────

function PaperCard({ paper, rank, selected, onToggle }) {
  const [expanded, setExpanded] = useState(false);
  const badge = sourceBadge(paper.source);
  const score = paper.relevance_score ? Math.round(paper.relevance_score * 100) : null;

  return (
    <article
      className={`relative rounded-2xl border transition-all duration-200 cursor-pointer ${
        selected
          ? "border-amber-400 bg-amber-50/60 shadow-md shadow-amber-100"
          : "border-stone-200 bg-white hover:border-stone-300 hover:shadow-sm"
      }`}
      onClick={onToggle}
    >
      {/* Selection indicator */}
      <div className={`absolute top-3 right-3 w-5 h-5 rounded-full border-2 flex items-center justify-center transition-all ${
        selected ? "border-amber-500 bg-amber-500" : "border-stone-300 bg-white"
      }`}>
        {selected && <span className="text-white text-[10px] font-bold">✓</span>}
      </div>

      <div className="p-5 pr-12">
        {/* Rank + Title */}
        <div className="flex items-start gap-3 mb-3">
          <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-stone-900 text-amber-400 flex items-center justify-center text-xs font-black">
            {rank}
          </span>
          <h3 className="text-sm font-semibold text-stone-900 leading-snug">{paper.title}</h3>
        </div>

        {/* Meta row */}
        <div className="flex flex-wrap gap-1.5 mb-3 ml-10">
          <span className={`px-2 py-0.5 text-[11px] font-semibold rounded border ${badge.bg}`}>{badge.label}</span>
          {score && (
            <span className={`px-2 py-0.5 text-[11px] font-semibold rounded border ${scoreColor(paper.relevance_score)}`}>
              {score}% match
            </span>
          )}
          {paper.published && (
            <span className="flex items-center gap-1 px-2 py-0.5 text-[11px] text-stone-500 bg-stone-100 rounded border border-stone-200">
              <Calendar className="w-3 h-3" />{paper.published}
            </span>
          )}
          {paper.citation_count > 0 && (
            <span className="px-2 py-0.5 text-[11px] text-stone-500 bg-stone-100 rounded border border-stone-200">
              {paper.citation_count.toLocaleString()} cites
            </span>
          )}
        </div>

        {/* Authors */}
        {paper.authors?.length > 0 && (
          <div className="flex items-center gap-1.5 mb-3 ml-10 text-xs text-stone-500">
            <Users className="w-3 h-3 flex-shrink-0" />
            <span className="truncate">
              {paper.authors.slice(0, 3).join(", ")}
              {paper.authors.length > 3 && ` +${paper.authors.length - 3}`}
            </span>
          </div>
        )}

        {/* AI Explanation */}
        {paper.explanation && (
          <div className="ml-10 mb-3 p-2.5 bg-violet-50 border border-violet-200 rounded-lg">
            <div className="flex gap-2">
              <Sparkles className="w-3.5 h-3.5 text-violet-500 mt-0.5 flex-shrink-0" />
              <p className="text-xs text-violet-800 leading-relaxed">{paper.explanation}</p>
            </div>
          </div>
        )}

        {/* Abstract */}
        <div className="ml-10">
          <p className={`text-xs text-stone-600 leading-relaxed ${expanded ? "" : "line-clamp-2"}`}>
            {paper.abstract}
          </p>
          {paper.abstract?.length > 200 && (
            <button
              onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
              className="mt-1 text-xs text-amber-600 hover:text-amber-800 flex items-center gap-1"
            >
              {expanded ? <><ChevronUp className="w-3 h-3" />Less</> : <><ChevronDown className="w-3 h-3" />More</>}
            </button>
          )}
        </div>

        {/* Footer */}
        <div className="mt-3 ml-10 pt-3 border-t border-stone-100 flex items-center justify-between">
          <div className="flex gap-3">
            {paper.pdf_url && (
              <a href={paper.pdf_url} target="_blank" rel="noreferrer"
                onClick={e => e.stopPropagation()}
                className="text-xs text-rose-600 hover:text-rose-800 font-semibold">PDF</a>
            )}
          </div>
          {paper.url && (
            <a href={paper.url} target="_blank" rel="noreferrer"
              onClick={e => e.stopPropagation()}
              className="flex items-center gap-1.5 px-2.5 py-1 bg-stone-900 text-amber-400 rounded-lg text-xs font-semibold hover:bg-stone-700 transition-colors">
              Read <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      </div>
    </article>
  );
}

// ── Analyst Chat Message ──────────────────────────────────────────────────────

function ChatMessage({ msg }) {
  const [showCitations, setShowCitations] = useState(false);

  if (msg.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] px-4 py-2.5 bg-stone-900 text-amber-50 rounded-2xl rounded-tr-sm text-sm leading-relaxed">
          {msg.content}
        </div>
      </div>
    );
  }

  if (msg.role === "thinking") {
    return (
      <div className="flex items-center gap-2 text-stone-400 text-sm py-2">
        <Loader2 className="w-4 h-4 animate-spin" />
        <span>Analysing {msg.papers_count} papers…</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="bg-white border border-stone-200 rounded-2xl rounded-tl-sm p-4 shadow-sm">
        <div className="flex items-start gap-2 mb-2">
          <Brain className="w-4 h-4 text-amber-500 mt-0.5 flex-shrink-0" />
          <span className="text-[11px] font-bold text-stone-400 uppercase tracking-wider">Synthesis</span>
        </div>
        <div className="text-sm text-stone-800 leading-relaxed whitespace-pre-wrap">
          {msg.content.split('\n').map((line, i) => (
            <p key={i} className={line.startsWith('#') ? "font-bold text-stone-900 mt-2" : "mb-1"}>
              <AnswerText text={line.replace(/^#+\s*/, '')} />
            </p>
          ))}
        </div>
        {msg.citations?.length > 0 && (
          <button
            onClick={() => setShowCitations(!showCitations)}
            className="mt-3 flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-800 font-semibold"
          >
            <Quote className="w-3 h-3" />
            {msg.citations.length} source{msg.citations.length !== 1 ? "s" : ""} cited
            {showCitations ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        )}
      </div>

      {showCitations && msg.citations?.length > 0 && (
        <div className="space-y-2 pl-2">
          {msg.citations.map((c, i) => (
            <div key={i} className="bg-amber-50 border border-amber-200 rounded-xl p-3">
              <div className="flex items-start justify-between gap-2 mb-1">
                <p className="text-xs font-semibold text-stone-800 leading-tight">{c.title}</p>
                {c.url && (
                  <a href={c.url} target="_blank" rel="noreferrer"
                    className="flex-shrink-0 text-amber-600 hover:text-amber-800">
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
              <p className="text-[11px] text-stone-500 mb-1.5">
                {c.authors?.slice(0, 2).join(", ")}{c.authors?.length > 2 ? " et al." : ""} · {c.published}
              </p>
              <p className="text-[11px] text-stone-600 italic leading-relaxed line-clamp-3">
                "{c.chunk_text}"
              </p>
            </div>
          ))}
        </div>
      )}

      {msg.processing_time && (
        <p className="text-[11px] text-stone-400 pl-2">
          Consulted {msg.papers_consulted} papers · {msg.processing_time}s
        </p>
      )}
    </div>
  );
}

// ── Analyst Chat Panel ────────────────────────────────────────────────────────

function AnalystPanel({ papers, onClose }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef(null);

  const SUGGESTED = [
    "What are the main findings across these papers?",
    "What methodologies are commonly used?",
    "What are the key limitations identified?",
    "What future directions do authors suggest?",
  ];

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const ask = useCallback(async (q = question) => {
    if (!q.trim() || loading) return;
    const userMsg = { role: "user", content: q };
    const thinkingMsg = { role: "thinking", papers_count: papers.length };
    setMessages(prev => [...prev, userMsg, thinkingMsg]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q,
          paper_ids: papers.map(p => p.id),
          session_papers: papers.map(p => ({
            id: p.id, title: p.title, abstract: p.abstract,
            authors: p.authors, url: p.url, published: p.published,
          })),
          top_k: 8,
        }),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Analysis failed");
      }

      const data = await res.json();
      setMessages(prev => {
        const next = prev.filter(m => m.role !== "thinking");
        return [...next, {
          role: "assistant",
          content: data.answer,
          citations: data.citations,
          papers_consulted: data.papers_consulted,
          processing_time: data.processing_time,
        }];
      });
    } catch (err) {
      setMessages(prev => {
        const next = prev.filter(m => m.role !== "thinking");
        return [...next, { role: "assistant", content: `Error: ${err.message}`, citations: [] }];
      });
    } finally {
      setLoading(false);
    }
  }, [question, papers, loading]);

  return (
    <div className="flex flex-col h-full">
      {/* Panel Header */}
      <div className="flex items-center justify-between px-5 py-4 border-b border-stone-200 bg-stone-50">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-amber-500" />
          <div>
            <h3 className="text-sm font-bold text-stone-900">Paper Analyst</h3>
            <p className="text-xs text-stone-500">{papers.length} paper{papers.length !== 1 ? "s" : ""} loaded</p>
          </div>
        </div>
        <button onClick={onClose} className="p-1.5 hover:bg-stone-200 rounded-lg transition-colors">
          <X className="w-4 h-4 text-stone-500" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        {messages.length === 0 && (
          <div className="space-y-4">
            <div className="text-center py-6">
              <BookOpen className="w-10 h-10 text-stone-300 mx-auto mb-3" />
              <p className="text-sm text-stone-500 font-medium">Ask anything about your papers</p>
              <p className="text-xs text-stone-400 mt-1">Get synthesised, cited answers in seconds</p>
            </div>
            <div className="space-y-2">
              <p className="text-xs text-stone-400 font-semibold uppercase tracking-wider">Suggested questions</p>
              {SUGGESTED.map((s, i) => (
                <button key={i} onClick={() => ask(s)}
                  className="w-full text-left text-xs px-3 py-2.5 bg-white border border-stone-200 rounded-xl hover:border-amber-300 hover:bg-amber-50 transition-all text-stone-700">
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => <ChatMessage key={i} msg={msg} />)}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="px-5 py-4 border-t border-stone-200 bg-white">
        <div className="flex gap-2">
          <input
            value={question}
            onChange={e => setQuestion(e.target.value)}
            onKeyDown={e => e.key === "Enter" && !e.shiftKey && ask()}
            placeholder="Ask a question about these papers…"
            disabled={loading}
            className="flex-1 text-sm px-3.5 py-2.5 border border-stone-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent disabled:opacity-50 bg-stone-50 placeholder:text-stone-400"
          />
          <button onClick={() => ask()} disabled={loading || !question.trim()}
            className="p-2.5 bg-stone-900 text-amber-400 rounded-xl disabled:opacity-40 hover:bg-stone-700 transition-colors flex-shrink-0">
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────

export default function PaperMindAnalyst() {
  const [query, setQuery] = useState("");
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchStats, setSearchStats] = useState(null);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [analystOpen, setAnalystOpen] = useState(false);
  const fileInputRef = useRef(null);

  const selectedPapers = papers.filter(p => selectedIds.has(p.id));

  const search = async (q = query) => {
    if (!q.trim()) return;
    setLoading(true);
    setError("");
    setPapers([]);
    setSelectedIds(new Set());
    setAnalystOpen(false);

    try {
      const res = await fetch(`${API_BASE}/recommend`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: q, max_results: 15, sources: ["semantic_scholar", "arxiv"] }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Search failed");
      }
      const data = await res.json();
      setPapers(data.papers);
      setSearchStats({ total: data.total_found, time: data.processing_time, query: data.query });
      // Auto-select all papers for analyst
      setSelectedIds(new Set(data.papers.map(p => p.id)));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setLoading(true);
    setError("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/upload-document`, { method: "POST", body: formData });
      if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
      const data = await res.json();
      setPapers(data.recommendations.papers);
      setSearchStats({ total: data.recommendations.total_found, time: data.recommendations.processing_time, query: data.extracted_terms });
      setQuery(data.extracted_terms);
      setSelectedIds(new Set(data.recommendations.papers.map(p => p.id)));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (id) => {
    setSelectedIds(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const selectAll = () => setSelectedIds(new Set(papers.map(p => p.id)));
  const clearAll = () => setSelectedIds(new Set());

  const exportResults = () => {
    const blob = new Blob([JSON.stringify({ query: searchStats?.query, papers }, null, 2)], { type: "application/json" });
    const a = Object.assign(document.createElement("a"), {
      href: URL.createObjectURL(blob),
      download: `papermind_${new Date().toISOString().split("T")[0]}.json`,
    });
    a.click();
  };

  return (
    <div className="min-h-screen bg-[#f5f3ef] font-['Georgia',serif]">
      {/* ── Top Bar ── */}
      <header className="bg-stone-900 text-amber-50 px-6 py-4 flex items-center justify-between sticky top-0 z-50 shadow-lg">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 bg-amber-400 rounded-xl flex items-center justify-center">
            <Brain className="w-5 h-5 text-stone-900" />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight leading-none">PaperMind</h1>
            <p className="text-[11px] text-amber-300 font-sans tracking-widest uppercase">Research Analyst</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {papers.length > 0 && (
            <>
              <button onClick={exportResults}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-stone-700 hover:bg-stone-600 text-amber-200 rounded-lg transition-colors font-sans">
                <Download className="w-3.5 h-3.5" />Export
              </button>
              <button
                onClick={() => { if (selectedPapers.length > 0) setAnalystOpen(true); }}
                disabled={selectedPapers.length === 0}
                className="flex items-center gap-1.5 px-4 py-1.5 text-xs bg-amber-400 hover:bg-amber-300 text-stone-900 rounded-lg transition-colors font-sans font-bold disabled:opacity-40">
                <MessageSquare className="w-3.5 h-3.5" />
                Analyse {selectedPapers.length > 0 ? `(${selectedPapers.length})` : ""}
              </button>
            </>
          )}
        </div>
      </header>

      <div className={`flex transition-all duration-300 ${analystOpen ? "gap-0" : ""}`}>
        {/* ── Main Column ── */}
        <div className={`flex-1 transition-all duration-300 ${analystOpen ? "lg:w-[60%]" : "w-full"} min-w-0`}>
          <div className="max-w-4xl mx-auto px-6 py-8">

            {/* ── Search Box ── */}
            <div className="bg-white rounded-3xl shadow-sm border border-stone-200 p-6 mb-6">
              <h2 className="text-xl font-bold text-stone-900 mb-1">Research Paper Analyst</h2>
              <p className="text-sm text-stone-500 mb-5 font-sans">
                Search arXiv & Semantic Scholar, then chat with your papers for synthesised, cited answers.
              </p>

              <div className="flex gap-3 mb-4">
                <div className="relative flex-1">
                  <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" />
                  <input
                    value={query}
                    onChange={e => setQuery(e.target.value)}
                    onKeyDown={e => e.key === "Enter" && search()}
                    placeholder="e.g. RAG chunking strategies for LLMs…"
                    className="w-full pl-10 pr-4 py-3 text-sm border border-stone-200 rounded-2xl focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent font-sans bg-stone-50"
                    disabled={loading}
                  />
                </div>
                <button onClick={() => search()} disabled={loading || !query.trim()}
                  className="px-5 py-3 bg-stone-900 text-amber-400 rounded-2xl text-sm font-bold disabled:opacity-40 hover:bg-stone-700 transition-colors font-sans flex items-center gap-2">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                  Search
                </button>
              </div>

              <div className="flex items-center gap-3">
                <div className="flex-1 h-px bg-stone-100" />
                <span className="text-xs text-stone-400 font-sans">or</span>
                <div className="flex-1 h-px bg-stone-100" />
              </div>

              <div className="mt-3">
                <input type="file" ref={fileInputRef} onChange={handleUpload} accept=".txt,.md,.pdf" className="hidden" />
                <button onClick={() => fileInputRef.current?.click()} disabled={loading}
                  className="w-full flex items-center justify-center gap-2 py-2.5 border-2 border-dashed border-stone-200 rounded-2xl text-sm text-stone-500 hover:border-amber-300 hover:text-amber-600 hover:bg-amber-50 transition-all font-sans disabled:opacity-40">
                  <Upload className="w-4 h-4" />
                  Upload a document to find related papers
                </button>
              </div>
            </div>

            {/* ── Error ── */}
            {error && (
              <div className="mb-4 flex items-start gap-3 p-4 bg-red-50 border border-red-200 rounded-2xl">
                <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                <p className="text-sm text-red-700 font-sans">{error}</p>
              </div>
            )}

            {/* ── Loading ── */}
            {loading && (
              <div className="text-center py-16">
                <Loader2 className="w-8 h-8 animate-spin text-amber-500 mx-auto mb-3" />
                <p className="text-stone-500 font-sans text-sm">Fetching and ranking papers…</p>
              </div>
            )}

            {/* ── Stats + Select Controls ── */}
            {searchStats && !loading && papers.length > 0 && (
              <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                <div className="flex items-center gap-2 text-sm text-stone-600 font-sans">
                  <span className="font-semibold text-stone-900">{papers.length} papers</span>
                  <span className="text-stone-400">for "{searchStats.query}"</span>
                  <span className="text-stone-300">·</span>
                  <span className="text-stone-400">{searchStats.time}s</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-stone-400 font-sans">Select papers for analysis:</span>
                  <button onClick={selectAll} className="text-xs px-2.5 py-1 bg-amber-100 text-amber-700 rounded-lg hover:bg-amber-200 transition-colors font-sans font-semibold">All</button>
                  <button onClick={clearAll} className="text-xs px-2.5 py-1 bg-stone-100 text-stone-600 rounded-lg hover:bg-stone-200 transition-colors font-sans">None</button>
                </div>
              </div>
            )}

            {/* ── Papers Grid ── */}
            {!loading && papers.length > 0 && (
              <div className="grid gap-4">
                {papers.map((paper, i) => (
                  <PaperCard
                    key={paper.id || i}
                    paper={paper}
                    rank={i + 1}
                    selected={selectedIds.has(paper.id)}
                    onToggle={() => toggleSelect(paper.id)}
                  />
                ))}
              </div>
            )}

            {/* ── Empty State ── */}
            {!loading && papers.length === 0 && !error && (
              <div className="text-center py-20">
                <FileText className="w-12 h-12 text-stone-300 mx-auto mb-4" />
                <h3 className="text-lg font-bold text-stone-700 mb-2">Start your research</h3>
                <p className="text-stone-400 font-sans text-sm max-w-sm mx-auto">
                  Search for a topic to load papers, then select them and open the Analyst to ask questions with cited answers.
                </p>
                <div className="mt-6 flex flex-wrap justify-center gap-2">
                  {["RAG chunking strategies", "LLM hallucination detection", "Vision transformer efficiency", "Diffusion model fine-tuning"].map(s => (
                    <button key={s} onClick={() => { setQuery(s); search(s); }}
                      className="px-3 py-1.5 text-xs bg-white border border-stone-200 rounded-lg text-stone-600 hover:border-amber-300 hover:text-amber-700 hover:bg-amber-50 transition-all font-sans">
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── Analyst Side Panel ── */}
        {analystOpen && (
          <div className="w-full lg:w-[420px] flex-shrink-0 bg-white border-l border-stone-200 sticky top-[61px] h-[calc(100vh-61px)] flex flex-col shadow-xl">
            <AnalystPanel papers={selectedPapers} onClose={() => setAnalystOpen(false)} />
          </div>
        )}
      </div>

      {/* ── Floating Analyst Button (when papers loaded, panel closed) ── */}
      {!analystOpen && selectedPapers.length > 0 && (
        <button
          onClick={() => setAnalystOpen(true)}
          className="fixed bottom-6 right-6 flex items-center gap-2 px-5 py-3 bg-stone-900 text-amber-400 rounded-2xl shadow-2xl hover:bg-stone-700 transition-all text-sm font-bold font-sans z-40 animate-bounce-once"
        >
          <Brain className="w-4 h-4" />
          Analyse {selectedPapers.length} Papers
        </button>
      )}
    </div>
  );
}