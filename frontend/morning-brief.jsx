import { useState } from "react";

const CATEGORIES = [
  {
    id: "tech",
    label: "Technology",
    icon: "⬡",
    color: "#00D4FF",
    query: "latest technology AI hardware semiconductor news today site:techcrunch.com OR site:theverge.com OR site:wired.com OR site:reuters.com OR site:ft.com",
  },
  {
    id: "politics",
    label: "Geopolitics",
    icon: "◈",
    color: "#FF6B35",
    query: "major geopolitics world politics news today site:reuters.com OR site:bbc.com OR site:aljazeera.com OR site:apnews.com OR site:scmp.com",
  },
  {
    id: "economy",
    label: "Economy",
    icon: "◎",
    color: "#FFD700",
    query: "global economy markets finance news today site:ft.com OR site:reuters.com OR site:bloomberg.com OR site:nikkei.com",
  },
  {
    id: "startups",
    label: "Startups",
    icon: "△",
    color: "#A8FF78",
    query: "startup funding round venture capital news today site:techcrunch.com OR site:crunchbase.com OR site:axios.com",
  },
  {
    id: "ai_forecast",
    label: "AI Forecast",
    icon: "✦",
    color: "#C77DFF",
    query: "AI capabilities milestones frontier models agentic AI breakthroughs research today",
    special: true,
  },
];

async function fetchNewsDigest(category) {
  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", year: "numeric", month: "long", day: "numeric",
  });

  let specialFocus = "";
  if (category.special) {
    specialFocus = `

SPECIAL FOCUS for AI Forecast:
- What new capabilities are emerging (be specific: agents doing X, models at Y benchmark)
- What is becoming POSSIBLE that wasn't last month
- Concrete 30-90 day predictions
- Frontier lab announcements (Anthropic, OpenAI, Google DeepMind, Meta, xAI, Chinese labs)
- Research papers with practical implications
The signal field is especially important - give a clear falsifiable forecast.`;
  }

  const systemPrompt = `You are a world-class news analyst producing a balanced morning briefing. Today is ${today}.

BALANCE REQUIREMENTS:
- Include Western perspectives (Reuters, AP, BBC, FT)
- Include Asian perspectives (Nikkei Asia, SCMP, NHK World)
- Include Global South perspectives (Al Jazeera) where relevant
- For China/Russia: include state media stance ONLY tagged as "State Media"
- Flag underrepresented regions in bias_note${specialFocus}

OUTPUT: ONLY valid JSON. No markdown fences, no preamble.
{
  "headline": "One sharp sentence",
  "tldr": "2-3 sentence summary readable in 20 seconds",
  "stories": [
    {
      "title": "Story title",
      "summary": "2-3 sentence summary",
      "source": "Publication name",
      "source_region": "Western|Asia|Middle East|Global South|State Media",
      "source_url": "https://... MANDATORY direct link",
      "significance": "Why it matters in 1 sentence",
      "trend_signal": "bull|bear|neutral|watch"
    }
  ],
  "signal": "Forward-looking insight: 30-90 day horizon",
  "bias_note": "Which regions are underrepresented today"
}

Include 3-4 stories. EVERY story MUST have a working source_url.`;

  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-20250514",
      max_tokens: 2000,
      tools: [{ type: "web_search_20250305", name: "web_search" }],
      system: systemPrompt,
      messages: [{ role: "user", content: `Search for the most important ${category.label} news from the last 24 hours. Focus on: ${category.query}. Every story must include source_url.` }],
    }),
  });

  const data = await response.json();
  const text = data.content.filter(b => b.type === "text").map(b => b.text).join("");
  const clean = text.replace(/```json|```/g, "").trim();
  const match = clean.match(/\{[\s\S]*\}/);
  if (!match) throw new Error("No JSON found");
  return JSON.parse(match[0]);
}

const SIGNAL_COLORS = { bull: "#A8FF78", bear: "#FF6B6B", neutral: "#888", watch: "#FFD700" };
const SIGNAL_LABELS = { bull: "↑", bear: "↓", neutral: "–", watch: "◉" };

function StoryCard({ story, accent }) {
  const hasUrl = story.source_url && story.source_url.startsWith("http");
  const titleStyle = {
    fontFamily: "'Georgia', serif",
    fontSize: "15px",
    fontWeight: "600",
    color: hasUrl ? "#E8E8E0" : "#888",
    marginBottom: "6px",
    lineHeight: "1.4",
    textDecoration: "none",
    display: "block",
    cursor: hasUrl ? "pointer" : "default",
  };
  const TitleEl = hasUrl ? "a" : "div";

  return (
    <div style={{ borderLeft: `2px solid ${accent}`, paddingLeft: "16px", marginBottom: "20px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
        <span style={{ fontSize: "11px", color: accent, fontFamily: "monospace", letterSpacing: "0.1em", textTransform: "uppercase" }}>
          {story.source_region}
        </span>
        <span style={{ color: "#444", fontSize: "11px" }}>·</span>
        <span style={{ fontSize: "11px", color: "#888" }}>{story.source}</span>
        {hasUrl && <span style={{ fontSize: "10px", color: "#555", marginLeft: "4px" }}>↗</span>}
        <span style={{ marginLeft: "auto", fontSize: "13px", color: SIGNAL_COLORS[story.trend_signal] || "#888", fontWeight: "700" }}>
          {SIGNAL_LABELS[story.trend_signal]}
        </span>
      </div>
      <TitleEl
        {...(hasUrl ? { href: story.source_url, target: "_blank", rel: "noopener noreferrer" } : {})}
        style={titleStyle}
      >
        {story.title}
      </TitleEl>
      <div style={{ fontSize: "13px", color: "#999", lineHeight: "1.6", marginBottom: "6px" }}>
        {story.summary}
      </div>
      <div style={{ fontSize: "12px", color: "#666", fontStyle: "italic", lineHeight: "1.4" }}>
        ↳ {story.significance}
      </div>
    </div>
  );
}

function CategoryPanel({ category, data, loading, error, onLoad }) {
  return (
    <div style={{ background: "#111", border: "1px solid #222", borderTop: `3px solid ${category.color}`, padding: "24px", minHeight: "200px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "20px", color: category.color }}>{category.icon}</span>
          <span style={{ fontFamily: "monospace", fontSize: "13px", letterSpacing: "0.15em", color: category.color, textTransform: "uppercase" }}>
            {category.label}
          </span>
        </div>
        {!data && !loading && (
          <button onClick={onLoad} style={{ background: "transparent", border: `1px solid ${category.color}`, color: category.color, padding: "4px 12px", fontSize: "11px", fontFamily: "monospace", letterSpacing: "0.1em", cursor: "pointer", textTransform: "uppercase" }}>
            Load
          </button>
        )}
      </div>

      {loading && (
        <div style={{ padding: "20px 0" }}>
          <div style={{ color: "#555", fontSize: "12px", fontFamily: "monospace", marginBottom: "8px" }}>searching sources...</div>
          {[1, 2, 3].map(i => (
            <div key={i} style={{ height: "8px", background: "#1a1a1a", borderRadius: "2px", width: `${60 + i * 12}%`, marginBottom: "8px", animation: "pulse 1.5s infinite" }} />
          ))}
        </div>
      )}

      {error && <div style={{ color: "#FF6B6B", fontSize: "13px", padding: "12px 0" }}>⚠ {error}</div>}

      {data && (
        <div>
          <div style={{ fontFamily: "'Georgia', serif", fontSize: "18px", fontWeight: "700", color: "#F0EFE6", marginBottom: "10px", lineHeight: "1.3" }}>
            {data.headline}
          </div>
          <div style={{ fontSize: "13px", color: "#AAA", lineHeight: "1.7", marginBottom: "24px", paddingBottom: "20px", borderBottom: "1px solid #1E1E1E" }}>
            {data.tldr}
          </div>
          {data.stories?.map((s, i) => <StoryCard key={i} story={s} accent={category.color} />)}
          {data.signal && (
            <div style={{ marginTop: "20px", padding: "14px", background: "#0A0A0A", border: "1px solid #222", borderLeft: `2px solid ${category.color}` }}>
              <div style={{ fontSize: "10px", color: "#555", fontFamily: "monospace", letterSpacing: "0.15em", marginBottom: "6px", textTransform: "uppercase" }}>
                30–90 Day Signal
              </div>
              <div style={{ fontSize: "13px", color: "#CCC", lineHeight: "1.6" }}>{data.signal}</div>
            </div>
          )}
          {data.bias_note && (
            <div style={{ marginTop: "12px", fontSize: "11px", color: "#555", fontStyle: "italic" }}>
              Coverage note: {data.bias_note}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function MorningBrief() {
  const [panelData, setPanelData] = useState({});
  const [panelLoading, setPanelLoading] = useState({});
  const [panelError, setPanelError] = useState({});
  const [loadingAll, setLoadingAll] = useState(false);

  const today = new Date().toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  });

  const loadCategory = async (cat) => {
    if (panelData[cat.id] || panelLoading[cat.id]) return;
    setPanelLoading(p => ({ ...p, [cat.id]: true }));
    setPanelError(p => ({ ...p, [cat.id]: null }));
    try {
      const data = await fetchNewsDigest(cat);
      setPanelData(p => ({ ...p, [cat.id]: data }));
    } catch (e) {
      setPanelError(p => ({ ...p, [cat.id]: `Failed: ${e.message}` }));
    } finally {
      setPanelLoading(p => ({ ...p, [cat.id]: false }));
    }
  };

  const loadAll = async () => {
    setLoadingAll(true);
    await Promise.all(CATEGORIES.map(loadCategory));
    setLoadingAll(false);
  };

  const importJSON = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      try {
        const briefs = JSON.parse(ev.target.result);
        // Expected: array of {category, headline, tldr, signal, bias_note, stories: [...]}
        const newData = {};
        briefs.forEach(b => {
          newData[b.category] = {
            headline: b.headline,
            tldr: b.tldr,
            signal: b.signal,
            bias_note: b.bias_note,
            stories: b.stories,
          };
        });
        setPanelData(newData);
      } catch (err) {
        alert(`Failed to import: ${err.message}`);
      }
    };
    reader.readAsText(file);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0D0D0D", color: "#E8E8E0", fontFamily: "'Helvetica Neue', sans-serif" }}>
      <style>{`
        @keyframes pulse { 0%,100%{opacity:0.4} 50%{opacity:1} }
        * { box-sizing: border-box; }
        button:hover { opacity: 0.8; }
        a:hover { color: #fff !important; }
      `}</style>

      <div style={{ padding: "32px 24px 20px", borderBottom: "1px solid #1A1A1A", display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ fontFamily: "monospace", fontSize: "10px", letterSpacing: "0.3em", color: "#444", textTransform: "uppercase", marginBottom: "8px" }}>
            Morning Brief
          </div>
          <div style={{ fontFamily: "'Georgia', serif", fontSize: "28px", fontWeight: "700", color: "#F0EFE6", letterSpacing: "-0.02em" }}>
            {today}
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <label style={{ background: "transparent", color: "#888", border: "1px solid #333", padding: "10px 16px", fontSize: "11px", fontFamily: "monospace", letterSpacing: "0.15em", textTransform: "uppercase", cursor: "pointer" }}>
            Import JSON
            <input type="file" accept=".json" onChange={importJSON} style={{ display: "none" }} />
          </label>
          <button onClick={loadAll} disabled={loadingAll} style={{ background: "#F0EFE6", color: "#0D0D0D", border: "none", padding: "10px 24px", fontSize: "12px", fontFamily: "monospace", letterSpacing: "0.15em", textTransform: "uppercase", cursor: loadingAll ? "not-allowed" : "pointer", opacity: loadingAll ? 0.6 : 1, fontWeight: "700" }}>
            {loadingAll ? "Loading..." : "Load Live"}
          </button>
        </div>
      </div>

      <div style={{ padding: "10px 24px", borderBottom: "1px solid #1A1A1A", display: "flex", gap: "20px", flexWrap: "wrap" }}>
        {Object.entries(SIGNAL_LABELS).map(([key, sym]) => (
          <span key={key} style={{ fontSize: "11px", color: "#555" }}>
            <span style={{ color: SIGNAL_COLORS[key], fontWeight: "700" }}>{sym}</span> {key.charAt(0).toUpperCase() + key.slice(1)}
          </span>
        ))}
        <span style={{ fontSize: "11px", color: "#333", marginLeft: "auto" }}>
          Click story titles to open source
        </span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: "1px", background: "#1A1A1A", padding: "1px" }}>
        {CATEGORIES.map(cat => (
          <CategoryPanel key={cat.id} category={cat} data={panelData[cat.id]} loading={panelLoading[cat.id]} error={panelError[cat.id]} onLoad={() => loadCategory(cat)} />
        ))}
      </div>

      <div style={{ padding: "16px 24px", borderTop: "1px solid #1A1A1A", fontSize: "11px", color: "#333", display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
        <span>State media sources tagged as reference only — interpret with caution.</span>
        <span>Import data/exports/YYYY-MM-DD.json from your repo for archived briefs</span>
      </div>
    </div>
  );
}
