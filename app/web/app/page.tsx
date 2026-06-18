"use client";

import { useEffect, useState } from "react";

type CompareRow = {
  bank: string;
  bank_name: string;
  value: any;
  comparable: boolean;
  note: string | null;
  source_span: string | null;
};

type ChatResp = {
  answer: string;
  handler: string;
  field: string | null;
  sources: any[];
};

const FIELDS = [
  { key: "kar_payi_orani", label: "Kâr Payı Oranı" },
  { key: "vade_ay", label: "Vade (ay)" },
  { key: "tahsis_ucreti", label: "Tahsis Ücreti" },
];

function fmt(v: any): string {
  if (v == null) return "—";
  if (typeof v === "object") {
    if ("min" in v) return `%${v.min}–%${v.max}`;
    if ("value" in v) return `${v.value} ${v.currency ?? ""}`;
    if ("has_fee" in v) return v.has_fee ? `${v.amount ?? "?"} TL` : "masrafsız";
  }
  return String(v);
}

export default function Home() {
  const [field, setField] = useState("kar_payi_orani");
  const [rows, setRows] = useState<CompareRow[]>([]);
  const [q, setQ] = useState("");
  const [chat, setChat] = useState<ChatResp | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch(`/api/compare?field=${field}`)
      .then((r) => r.json())
      .then(setRows)
      .catch(() => setRows([]));
  }, [field]);

  async function ask() {
    if (!q.trim()) return;
    setLoading(true);
    try {
      const r = await fetch(`/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q }),
      });
      setChat(await r.json());
    } finally {
      setLoading(false);
    }
  }

  return (
    <main style={{ display: "grid", gap: 28 }}>
      {/* Dashboard: karşılaştırma */}
      <section style={card}>
        <h2 style={h2}>Karşılaştırma Paneli</h2>
        <div style={{ marginBottom: 12 }}>
          {FIELDS.map((f) => (
            <button
              key={f.key}
              onClick={() => setField(f.key)}
              style={{ ...chip, ...(field === f.key ? chipActive : {}) }}
            >
              {f.label}
            </button>
          ))}
        </div>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
          <thead>
            <tr style={{ textAlign: "left", color: "#94a3b8" }}>
              <th style={th}>Banka</th>
              <th style={th}>Değer</th>
              <th style={th}>Durum</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i} style={{ borderTop: "1px solid #1e293b" }}>
                <td style={td}>{r.bank_name || r.bank}</td>
                <td style={td}>
                  <strong>{fmt(r.value)}</strong>
                </td>
                <td style={{ ...td, color: r.comparable ? "#34d399" : "#fbbf24" }}>
                  {r.comparable ? "kıyaslanabilir" : r.note}
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td style={td} colSpan={3}>
                  Veri yok — API çalışıyor mu? (fixture demo)
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      {/* Chatbot */}
      <section style={card}>
        <h2 style={h2}>Chatbot</h2>
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && ask()}
            placeholder="ör. Hangi bankada en düşük kâr payı var?"
            style={input}
          />
          <button onClick={ask} disabled={loading} style={btn}>
            {loading ? "..." : "Sor"}
          </button>
        </div>
        {chat && (
          <div style={{ marginTop: 14 }}>
            <span style={badge}>{chat.handler === "structured" ? "yapısal sorgu" : "RAG"}</span>
            <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{chat.answer}</p>
            {chat.sources?.length > 0 && (
              <details style={{ color: "#94a3b8", fontSize: 13 }}>
                <summary>Kaynaklar ({chat.sources.length})</summary>
                <pre style={{ overflowX: "auto" }}>
                  {JSON.stringify(chat.sources, null, 2)}
                </pre>
              </details>
            )}
          </div>
        )}
      </section>
    </main>
  );
}

const card: React.CSSProperties = {
  background: "#1e293b",
  borderRadius: 12,
  padding: 20,
  border: "1px solid #334155",
};
const h2: React.CSSProperties = { marginTop: 0, fontSize: 18 };
const th: React.CSSProperties = { padding: "6px 8px", fontWeight: 600 };
const td: React.CSSProperties = { padding: "8px" };
const chip: React.CSSProperties = {
  background: "#334155",
  color: "#e2e8f0",
  border: "none",
  borderRadius: 999,
  padding: "6px 14px",
  marginRight: 8,
  cursor: "pointer",
  fontSize: 13,
};
const chipActive: React.CSSProperties = { background: "#3b82f6", color: "white" };
const input: React.CSSProperties = {
  flex: 1,
  padding: "10px 12px",
  borderRadius: 8,
  border: "1px solid #334155",
  background: "#0f172a",
  color: "#e2e8f0",
};
const btn: React.CSSProperties = {
  padding: "10px 18px",
  borderRadius: 8,
  border: "none",
  background: "#3b82f6",
  color: "white",
  cursor: "pointer",
};
const badge: React.CSSProperties = {
  display: "inline-block",
  background: "#0f172a",
  color: "#60a5fa",
  borderRadius: 6,
  padding: "2px 8px",
  fontSize: 12,
  marginBottom: 8,
};
