"use client";

/**
 * Canlı çıkarım (CLAUDE.md §11 — "tek bir örnek için canlı çıkarım butonu").
 *
 * İlgili: src/api/main.py `POST /extract`
 *
 * Demo stratejisi gereği panel önceden doldurulmuş DB'den okur; bu bileşen
 * sistemin GERÇEKTEN çalıştığını ispatlayan tek canlı yoldur: jüri kendi metnini
 * yapıştırır, 12 alanın tamamı + güven + katman + karakter offset'i + çelişki
 * anında döner.
 *
 * Bulunamayan alanlar da AYRICA gösterilir: halüsinasyon yasağının görünür hali
 * ("alan yoksa null, uydurma yok" — CLAUDE.md §21).
 */

import { useState } from "react";
import { api, toDisplayError } from "../lib/api";
import type { ExtractField, ExtractResult } from "../lib/api";
import {
  confidenceSourceLabel,
  contradictionLabel,
  extractorClass,
  extractorLabel,
  formatValue,
} from "../lib/format";
import ConfidenceBadge from "./ConfidenceBadge";
import { ErrorNotice } from "./ErrorNotice";
import SourceSpanView from "./SourceSpanView";

/** Hazır örnekler — demo sürtünmesini sıfıra indirir. */
const SAMPLES: { label: string; text: string }[] = [
  {
    label: "Konut finansmanı (temiz)",
    text:
      "Konut Finansmanı Kampanyası. Hayalinizdeki eve kavuşun: konut finansmanında " +
      "kâr payı oranı %1,89'dan başlayan oranlarla, 120 aya kadar vade imkânı. " +
      "Tahsis ücreti 750 TL. Kampanya 31.12.2026 tarihine kadar geçerlidir.",
  },
  {
    label: "Çelişkili örnek (masrafsız + ücret)",
    text:
      "Taşıt finansmanı kampanyası! Kâr payı oranı %2,49, 48 aya kadar vade. " +
      "Tamamen masrafsız başvuru. Tahsis ücreti 1.500,00 TL olarak tahsil edilir.",
  },
  {
    label: "Zor vaka (aralık + zaman-koşullu)",
    text:
      "İhtiyaç finansmanında kâr payı oranı %1,99 - %2,49 arasında, 36 aya kadar " +
      "vade. İlk 3 ay ödemesiz seçeneği ile 24 taksit. Yeni müşterilerimize " +
      "dosya masrafı yok.",
  },
  {
    label: "Alışveriş puanı / ödül",
    text:
      "Kredi kartınızla market alışverişlerinizde 750 TL'ye kadar alışveriş puanı " +
      "kazanın. Kampanyaya yeni müşteriler katılabilir, %20 indirim fırsatı " +
      "01.08.2026 - 30.09.2026 tarihleri arasında geçerlidir.",
  },
];

export default function ExtractLive() {
  const [text, setText] = useState(SAMPLES[0].text);
  const [bank, setBank] = useState("canli-demo");
  const [result, setResult] = useState<ExtractResult | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [active, setActive] = useState<string | null>(null);

  async function run() {
    if (!text.trim()) {
      setError(new Error("Çıkarım için bir metin girin."));
      return;
    }
    setBusy(true);
    setError(null);
    setActive(null);
    try {
      setResult(await api.extract(text, bank.trim() || "bilinmeyen"));
    } catch (e) {
      setError(e);
      setResult(null);
    } finally {
      setBusy(false);
    }
  }

  const activeField: ExtractField | null =
    result?.fields.find((f) => f.field === active) ?? null;

  return (
    <div className="stack">
      <section className="card">
        <h2>Canlı Çıkarım</h2>
        <p className="lede">
          Panelin geri kalanı önceden doldurulmuş veritabanından okur (demo
          güvenliği). Burası canlı yol: metni yapıştırın, çıkarım o anda koşar.
        </p>

        <div className="row" style={{ marginBottom: 10 }}>
          {SAMPLES.map((s) => (
            <button
              key={s.label}
              type="button"
              className="chip"
              onClick={() => {
                setText(s.text);
                setResult(null);
                setError(null);
              }}
            >
              {s.label}
            </button>
          ))}
        </div>

        <label className="small muted" htmlFor="extract-text">
          Kampanya metni
        </label>
        <textarea
          id="extract-text"
          className="textarea"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Bir katılım bankası kampanya metnini buraya yapıştırın…"
        />

        <div className="row" style={{ marginTop: 10 }}>
          <div className="row-tight">
            <label className="small muted" htmlFor="extract-bank">
              Banka etiketi
            </label>
            <input
              id="extract-bank"
              className="input"
              style={{ width: 180 }}
              value={bank}
              onChange={(e) => setBank(e.target.value)}
            />
          </div>
          <button type="button" className="btn" onClick={run} disabled={busy}>
            {busy ? "Çıkarım koşuyor…" : "Çıkarımı çalıştır"}
          </button>
          <span className="small faint">{text.length} karakter</span>
        </div>

        {!!error && (
          <div style={{ marginTop: 12 }}>
            <ErrorNotice error={error} />
            <p className="small muted">{toDisplayError(error).hint}</p>
          </div>
        )}
      </section>

      {result && (
        <>
          <section className="card">
            <h2>Sonuç</h2>
            <div className="stats" style={{ marginBottom: 14 }}>
              <div className="stat">
                <div className="k">Kampanya türü</div>
                <div className="v" style={{ fontSize: 16 }}>
                  {result.campaign_type ?? "—"}
                </div>
              </div>
              <div className="stat">
                <div className="k">Tür güveni</div>
                <div className="v" style={{ fontSize: 16 }}>
                  {result.campaign_type_confidence === null
                    ? "—"
                    : result.campaign_type_confidence.toFixed(2).replace(".", ",")}
                </div>
              </div>
              <div className="stat">
                <div className="k">Bulunan alan</div>
                <div className="v">
                  {result.fields.length}
                  <span className="small muted">
                    {" "}
                    / {result.fields.length + result.missing_fields.length}
                  </span>
                </div>
              </div>
              <div className="stat">
                <div className="k">Çelişki</div>
                <div
                  className="v"
                  style={{ color: result.contradictions.length ? "var(--bad)" : "var(--ok)" }}
                >
                  {result.contradictions.length}
                </div>
              </div>
              <div className="stat">
                <div className="k">Yerel LLM</div>
                <div className="v" style={{ fontSize: 16 }}>
                  {result.llm_available ? "açık" : "kapalı"}
                </div>
              </div>
            </div>

            {!result.llm_available && (
              <div className="notice notice-info" style={{ marginBottom: 14 }}>
                <strong>Yerel LLM kapalı — sonuçlar yalnızca kural katmanından</strong>
                Hibrit mimaride kurallar birincildir (CLAUDE.md §3); LLM yalnızca
                kuralların kaçırdığı örtük ifadeler için devreye girer. LLM
                servisi ayakta değilken sistem çalışmaya devam eder.
              </div>
            )}

            {result.contradictions.length > 0 && (
              <div style={{ marginBottom: 14, display: "grid", gap: 8 }}>
                {result.contradictions.map((c, i) => (
                  <div key={i} className="notice notice-error">
                    <strong>{contradictionLabel(c.kind)}</strong>
                    {c.detail}
                    <div className="small mono" style={{ marginTop: 4 }}>
                      {c.fields.join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th scope="col">Alan</th>
                    <th scope="col">Değer</th>
                    <th scope="col">Ham ifade</th>
                    <th scope="col">Güven</th>
                    <th scope="col">Güven kaynağı</th>
                    <th scope="col">Katman</th>
                    <th scope="col">Offset</th>
                  </tr>
                </thead>
                <tbody>
                  {result.fields.map((f) => (
                    <tr
                      key={f.field}
                      className={active === f.field ? "selected" : undefined}
                    >
                      <td>{f.label}</td>
                      <td className="num">
                        <strong>{formatValue(f.value, f.field)}</strong>
                      </td>
                      <td className="mono">{f.raw_value ? `«${f.raw_value.trim()}»` : "—"}</td>
                      <td>
                        <ConfidenceBadge value={f.confidence} source={f.confidence_source} />
                      </td>
                      <td className="small muted">
                        {confidenceSourceLabel(f.confidence_source)}
                      </td>
                      <td>
                        <span className={extractorClass(f.extractor)}>
                          {extractorLabel(f.extractor)}
                        </span>
                      </td>
                      <td>
                        {f.span_start === null ? (
                          <span className="badge badge-warn">yok</span>
                        ) : (
                          <button
                            type="button"
                            className="btn-link mono"
                            onClick={() =>
                              setActive(active === f.field ? null : f.field)
                            }
                          >
                            [{f.span_start}, {f.span_end})
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {result.missing_fields.length > 0 && (
              <>
                <h3>Bulunamayan alanlar ({result.missing_fields.length})</h3>
                <p className="small muted" style={{ marginTop: 0 }}>
                  Bu alanlar metinde geçmiyor. Sistem boş bırakır —{" "}
                  <b>değer uydurmaz</b>.
                </p>
                <div className="field-list">
                  {result.missing_fields.map((m) => (
                    <span key={m.field} className="pill">
                      {m.label}
                    </span>
                  ))}
                </div>
              </>
            )}
          </section>

          {activeField && (
            <section className="card">
              <h2>Kaynak vurgulaması — {activeField.label}</h2>
              <SourceSpanView
                text={result.text}
                span={activeField}
                rawValue={activeField.raw_value}
                defaultFullText
              />
            </section>
          )}
        </>
      )}
    </div>
  );
}
