"use client";

/**
 * Hibrit chatbot arayüzü (CLAUDE.md §5 — router'lı text-to-SQL + RAG).
 *
 * İlgili: src/api/main.py `POST /chat`, src/chatbot/router.py
 *
 * İki iyileştirme:
 *  1. HAZIR SORU BUTONLARI — 4 dakikalık sunumda soru yazmak zaman kaybı ve
 *     yazım hatası riski. Altı soru router'ın iki yolunu da (yapısal sorgu ve
 *     RAG) kapsayacak şekilde seçildi; demo sürtünmesi sıfırlanır.
 *  2. KAYNAKLAR artık ham JSON dökümü değil, okunur bir tablo. Kaynağı
 *     gösterebilmek açıklanabilirlik iddiasının kanıtıdır; `<pre>{JSON}</pre>`
 *     bunu kanıt olmaktan çıkarıp gürültüye çeviriyordu.
 */

import { useState } from "react";
import { api } from "../lib/api";
import type { ChatResp } from "../lib/api";
import { formatValue } from "../lib/format";
import { ErrorNotice } from "./ErrorNotice";

/**
 * Hazır sorular. İlk beşi `router.py` anahtar kelimeleriyle yapısal sorguya
 * (toplama/sıralama), sonuncusu RAG'e (koşul/açıklama) düşecek şekilde yazıldı.
 */
const PRESETS = [
  "Hangi bankada en düşük kâr payı oranı var?",
  "En yüksek vade veren banka hangisi?",
  "36 ay ve üzeri vade veren konut finansmanlarını listele",
  "En düşük tahsis ücreti hangi bankada?",
  "Masrafsız kampanya sunan bankalar hangileri?",
  "Konut finansmanı kampanyasının koşulları neler?",
];

const HANDLER_LABELS: Record<string, string> = {
  structured: "yapısal sorgu (text-to-SQL)",
  rag: "RAG (anlamsal arama)",
};

export default function ChatPanel() {
  const [q, setQ] = useState("");
  const [resp, setResp] = useState<ChatResp | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function ask(question: string) {
    const text = question.trim();
    if (!text) return;
    setQ(text);
    setBusy(true);
    setError(null);
    try {
      setResp(await api.chat(text));
    } catch (e) {
      setError(e);
      setResp(null);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="card">
      <h2>Chatbot</h2>
      <p className="lede">
        Sayısal/karşılaştırmalı sorular yapısal sorguya, koşul/açıklama soruları
        RAG&apos;e yönlendirilir. Hangi yolun kullanıldığı cevabın yanında yazar.
      </p>

      <div className="row" style={{ marginBottom: 12 }}>
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            className="chip"
            disabled={busy}
            onClick={() => ask(p)}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="row-tight">
        <input
          className="input grow"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") ask(q);
          }}
          placeholder="ör. Hangi bankada en düşük kâr payı var?"
          aria-label="Chatbot sorusu"
        />
        <button type="button" className="btn" onClick={() => ask(q)} disabled={busy}>
          {busy ? "…" : "Sor"}
        </button>
      </div>

      {!!error && (
        <div style={{ marginTop: 14 }}>
          <ErrorNotice error={error} />
        </div>
      )}

      {resp && (
        <div style={{ marginTop: 16 }}>
          <div className="row" style={{ marginBottom: 6 }}>
            <span className="badge">
              {HANDLER_LABELS[resp.handler] ?? resp.handler}
            </span>
            {resp.field && (
              <span className="badge" title="Router'ın çıkardığı alan">
                alan: <span className="mono">{resp.field}</span>
              </span>
            )}
          </div>
          <p style={{ whiteSpace: "pre-wrap", lineHeight: 1.6, margin: "8px 0 0" }}>
            {resp.answer}
          </p>

          {resp.sources?.length > 0 ? (
            <>
              <h3>Kaynaklar ({resp.sources.length})</h3>
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">Banka</th>
                      <th scope="col">Değer</th>
                      <th scope="col">Kaynak metin parçası</th>
                    </tr>
                  </thead>
                  <tbody>
                    {resp.sources.map((s, i) => (
                      <tr key={i}>
                        <td>{typeof s.bank === "string" ? s.bank : "—"}</td>
                        <td className="num">
                          {"value" in s ? formatValue(s.value, resp.field ?? undefined) : "—"}
                        </td>
                        <td className="small muted">
                          {typeof s.source_span === "string" && s.source_span
                            ? `…${s.source_span.trim()}…`
                            : summarize(s)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <p className="small muted" style={{ marginTop: 12 }}>
              Bu cevap için kaynak satırı döndürülmedi.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

/** RAG pasajları `bank/value/source_span` şeklinde gelmeyebilir. */
function summarize(s: Record<string, unknown>): string {
  for (const key of ["text", "chunk_text", "passage", "detail"]) {
    const v = s[key];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return JSON.stringify(s);
}
