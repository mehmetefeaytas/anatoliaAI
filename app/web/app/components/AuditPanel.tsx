"use client";

/**
 * Jüri Audit Paneli — bir belgenin tüm çıkarımları tek ekranda denetlenir.
 *
 * İlgili: src/api/main.py `GET /campaigns/{id}/text`
 *
 * Jürinin denetim ihtiyacı şu beş soruyu aynı anda sormaktır ve panel beşini de
 * tek satırda yanıtlar:
 *   1. Değer nereden geldi?        → kaynak URL + belge no
 *   2. Metinde tam olarak nerede?  → karakter offset'i + vurgulama
 *   3. Ne kadar eminiz?            → güven skoru + güven KAYNAĞI
 *   4. Hangi katman üretti?        → rule / ner / llm
 *   5. Çelişki var mı?             → belge düzeyinde çelişki listesi
 */

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { CampaignSummary } from "../lib/api";
import {
  confidenceSourceLabel,
  contradictionLabel,
  extractorClass,
  extractorLabel,
  formatValue,
} from "../lib/format";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import SourceSpanView from "./SourceSpanView";

type Props = {
  campaigns: CampaignSummary[];
  /** Dışarıdan (ör. çelişki listesinden) seçilen belge. */
  selectedId?: number | null;
};

export default function AuditPanel({ campaigns, selectedId }: Props) {
  const [id, setId] = useState<number | null>(selectedId ?? campaigns[0]?.id ?? null);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    if (selectedId != null) {
      setId(selectedId);
      setActive(null);
    }
  }, [selectedId]);

  const doc = useAsync(
    () => (id === null ? Promise.resolve(null) : api.campaignText(id)),
    [id],
  );

  if (campaigns.length === 0) {
    return (
      <section className="card">
        <h2>Jüri Audit Paneli</h2>
        <EmptyNotice title="Denetlenecek belge yok">
          Veritabanı boş görünüyor. Pipeline fixture modunda çalıştı mı?
        </EmptyNotice>
      </section>
    );
  }

  const activeField = doc.data?.fields.find((f) => f.field === active) ?? null;

  return (
    <div className="stack">
      <section className="card">
        <h2>Jüri Audit Paneli</h2>
        <p className="lede">
          Her değer için tek ekranda: kaynak URL, kaynak span, güven skoru ve
          kaynağı, hangi katmanın ürettiği ve çelişki durumu.
        </p>

        <div className="row-tight">
          <label className="small muted" htmlFor="audit-doc">
            Belge
          </label>
          <select
            id="audit-doc"
            className="select"
            value={id ?? ""}
            onChange={(e) => {
              setId(Number(e.target.value));
              setActive(null);
            }}
          >
            {campaigns.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} — {c.bank_name || c.bank}
                {c.campaign_type ? ` · ${c.campaign_type}` : ""}
              </option>
            ))}
          </select>
        </div>

        {doc.loading && <Loading />}
        {!!doc.error && (
          <div style={{ marginTop: 12 }}>
            <ErrorNotice error={doc.error} />
          </div>
        )}

        {doc.data && (
          <>
            <dl className="kv" style={{ marginTop: 16 }}>
              <dt>Banka</dt>
              <dd>{doc.data.bank_name || doc.data.bank}</dd>
              <dt>Kampanya türü</dt>
              <dd>{doc.data.campaign_type ?? "—"}</dd>
              <dt>Kaynak URL</dt>
              <dd className="mono">{doc.data.source_url ?? "—"}</dd>
              <dt>Toplanma zamanı</dt>
              <dd className="mono">{doc.data.scraped_at ?? "kaydedilmedi"}</dd>
              <dt>Belge uzunluğu</dt>
              <dd className="mono">{doc.data.text_length} karakter</dd>
              <dt>Çelişki</dt>
              <dd>
                {doc.data.contradictions.length === 0 ? (
                  <span className="badge badge-ok">yok</span>
                ) : (
                  <span className="badge badge-bad">
                    {doc.data.contradictions.length} bulgu
                  </span>
                )}
              </dd>
            </dl>

            {doc.data.contradictions.length > 0 && (
              <div style={{ marginTop: 14, display: "grid", gap: 8 }}>
                {doc.data.contradictions.map((c, i) => (
                  <div key={i} className="notice notice-error">
                    <strong>{contradictionLabel(c.kind)}</strong>
                    {c.detail}
                  </div>
                ))}
              </div>
            )}

            <h3>Çıkarılan alanlar ({doc.data.fields.length})</h3>
            {doc.data.fields.length === 0 ? (
              <EmptyNotice title="Bu belgeden hiçbir alan çıkarılamadı">
                Metin çıkarım kurallarının hiçbirine uymuyor. Değer uydurulmadı.
              </EmptyNotice>
            ) : (
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
                      <th scope="col">Kaynak span</th>
                    </tr>
                  </thead>
                  <tbody>
                    {doc.data.fields.map((f) => (
                      <tr
                        key={f.field}
                        className={active === f.field ? "selected" : undefined}
                      >
                        <td>{f.label}</td>
                        <td className="num">
                          <strong>{formatValue(f.canonical_value, f.field)}</strong>
                        </td>
                        <td className="mono">
                          {f.raw_value ? `«${f.raw_value.trim()}»` : "—"}
                        </td>
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
                            <span className="badge badge-warn">offset yok</span>
                          ) : (
                            <button
                              type="button"
                              className="btn-link mono"
                              aria-expanded={active === f.field}
                              onClick={() =>
                                setActive(active === f.field ? null : f.field)
                              }
                            >
                              [{f.span_start}, {f.span_end}){" "}
                              {f.span_verified ? "✓" : "?"}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      {doc.data && (
        <section className="card">
          <h2>
            Kaynak metin
            {activeField ? ` — ${activeField.label} vurgulanıyor` : ""}
          </h2>
          {!activeField && (
            <p className="lede">
              Yukarıdaki tabloda bir offset&apos;e tıklayın; ilgili karakter
              aralığı burada vurgulanır.
            </p>
          )}
          {activeField ? (
            <SourceSpanView
              text={doc.data.text}
              span={activeField}
              rawValue={activeField.raw_value}
              defaultFullText
            />
          ) : (
            <div className="source-text">{doc.data.text}</div>
          )}
        </section>
      )}
    </div>
  );
}
