"use client";

/**
 * Şeffaf skorlama — "en avantajlı" iddiasının FORMÜLÜ görünür.
 *
 * İlgili: src/api/main.py `/scoring`, src/comparison/compare.py, CLAUDE.md §17
 *
 * ÖNEMLİ (dürüstlük): Kod tabanında alanlar arası **ağırlıklı bileşik skor
 * YOKTUR**. `compare.py` sıralamayı tek alan üzerinden, iki adımda yapar:
 * (1) `_numeric_key()` ile sıralama anahtarı, (2) alanın yönü
 * (`_LOWER_IS_BETTER` / `_HIGHER_IS_BETTER`). Bu bileşen bu iki adımı ve her
 * bankanın aldığı ara değeri (`sort_key`) olduğu gibi gösterir; olmayan bir
 * ağırlık tablosu UYDURMAZ — API'nin `composite_note` alanı bunu açıkça söyler.
 */

import { api } from "../lib/api";
import { extractorClass, extractorLabel, formatValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { ErrorNotice, Loading } from "./ErrorNotice";

export default function ScoringExplainer({
  field,
  type,
}: {
  field: string;
  type?: string;
}) {
  const s = useAsync(() => api.scoring(field, type || undefined), [field, type]);

  return (
    <section className="card">
      <h2>Şeffaf Skorlama — «en avantajlı» nasıl hesaplandı?</h2>
      <p className="lede">
        Sıralamanın formülü ve her bankanın aldığı ara değer aşağıda. Formülün
        kaynağı: <span className="mono">{s.data?.formula_source ?? "src/comparison/compare.py"}</span>
      </p>

      {s.loading && <Loading />}
      {!!s.error && <ErrorNotice error={s.error} />}

      {s.data && (
        <>
          <ol className="steps">
            {s.data.steps.map((st) => (
              <li key={st.no}>
                <b>{st.name}</b> — <span>{st.detail}</span>
              </li>
            ))}
          </ol>

          <div className="notice notice-warn" style={{ marginTop: 16 }}>
            <strong>Bileşik (çok alanlı) puan yok — bilinçli bir karar</strong>
            {s.data.composite_note}
          </div>

          <h3>Bankaların aldığı ara değerler</h3>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th scope="col">Sıra</th>
                  <th scope="col">Banka</th>
                  <th scope="col">Kanonik değer</th>
                  <th scope="col">Sıralama anahtarı</th>
                  <th scope="col">Kıyas kapısı</th>
                  <th scope="col">Güven</th>
                  <th scope="col">Katman</th>
                </tr>
              </thead>
              <tbody>
                {s.data.rows.map((r, i) => (
                  <tr key={`${r.bank}-${i}`}>
                    <td className="num">
                      <span className={`rank-pill${r.rank === 1 ? " first" : ""}`}>
                        {r.rank ?? "—"}
                      </span>
                    </td>
                    <td>{r.bank_name || r.bank}</td>
                    <td className="num">{formatValue(r.value, s.data?.field)}</td>
                    <td className="num mono">
                      {r.sort_key === null ? "—" : r.sort_key}
                    </td>
                    <td>
                      {r.comparable ? (
                        <span className="badge badge-ok">geçti</span>
                      ) : (
                        <span className="badge badge-warn">
                          elendi — {r.note ?? "sebep yok"}
                        </span>
                      )}
                    </td>
                    <td>
                      <ConfidenceBadge value={r.confidence} />
                    </td>
                    <td>
                      <span className={extractorClass(r.extractor)}>
                        {extractorLabel(r.extractor)}
                      </span>
                    </td>
                  </tr>
                ))}
                {s.data.rows.length === 0 && (
                  <tr>
                    <td colSpan={7} className="muted">
                      Bu alan için sıralanacak kayıt yok.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
