"use client";

/**
 * Çelişki tespiti (CLAUDE.md §18 yenilikçilik hedefi #2).
 *
 * İlgili: src/api/main.py `/contradictions`, `/contradictions/summary`,
 *         src/comparison/contradiction.py
 *
 * Anlatı: "Bu çelişkileri biz aramadık — sistem taradığı belgelerde kendi
 * kendine avladı." Bu yüzden önce TARAMA KAPSAMI (kaç belge, kaç banka)
 * gösterilir; bulgu sayısı tek başına anlamsızdır. Bulgu yoksa bu da açıkça
 * söylenir: sıfır bulgu "tarama çalışmadı" ile karıştırılmaz.
 */

import { api } from "../lib/api";
import { contradictionLabel } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";

export default function ContradictionAlert({
  onInspect,
}: {
  onInspect?: (campaignId: number) => void;
}) {
  const list = useAsync(() => api.contradictions(), []);
  const sum = useAsync(() => api.contradictionSummary(), []);

  return (
    <section className="card">
      <h2>Çelişki Tespiti</h2>
      <p className="lede">
        Bir kampanya metni kendi içinde tutarsızsa yakalanır — en güçlü örnek
        «masrafsız» denip aynı metinde tahsis ücreti belirtilmesi. Tarama otomatiktir;
        aşağıdaki bulgular elle seçilmedi.
      </p>

      {sum.loading && <Loading label="Tarama kapsamı hesaplanıyor…" />}
      {!!sum.error && <ErrorNotice error={sum.error} />}
      {sum.data && (
        <div className="stats">
          <div className="stat">
            <div className="k">Taranan belge</div>
            <div className="v">{sum.data.scanned_campaigns}</div>
          </div>
          <div className="stat">
            <div className="k">Taranan banka</div>
            <div className="v">{sum.data.scanned_banks}</div>
          </div>
          <div className="stat">
            <div className="k">Bulunan çelişki</div>
            <div className="v" style={{ color: sum.data.contradiction_count > 0 ? "var(--bad)" : "var(--ok)" }}>
              {sum.data.contradiction_count}
            </div>
          </div>
          <div className="stat">
            <div className="k">Etkilenen belge</div>
            <div className="v">{sum.data.affected_campaigns}</div>
          </div>
        </div>
      )}

      <div style={{ marginTop: 16 }}>
        {list.loading && <Loading />}
        {!!list.error && <ErrorNotice error={list.error} />}
        {list.data?.length === 0 && !list.loading && (
          <EmptyNotice title="Bu külliyatta iç çelişki bulunamadı">
            Tarama koştu ve temiz döndü — «bulgu yok» ile «tarama çalışmadı» aynı
            şey değildir; yukarıdaki kapsam sayaçları taramanın gerçekten
            yürüdüğünü gösterir. Denetleyicinin kuralı canlı görmek için{" "}
            <b>Canlı Çıkarım</b> sekmesindeki «çelişkili örnek» metnini deneyin.
          </EmptyNotice>
        )}
        {list.data && list.data.length > 0 && (
          <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: 10 }}>
            {list.data.map((c, i) => (
              <li key={`${c.campaign_id}-${c.kind}-${i}`} className="notice notice-error">
                <strong>{contradictionLabel(c.kind)}</strong>
                <div>{c.detail}</div>
                <div className="small" style={{ marginTop: 6 }}>
                  <b>{c.bank_name || c.bank}</b>
                  {c.campaign_type ? ` · ${c.campaign_type}` : ""} · belge #
                  {c.campaign_id} · ilgili alanlar:{" "}
                  <span className="mono">{c.fields.join(", ")}</span>
                  {onInspect && (
                    <>
                      {" · "}
                      <button
                        type="button"
                        className="btn-link"
                        onClick={() => onInspect(c.campaign_id)}
                      >
                        denetim panelinde aç
                      </button>
                    </>
                  )}
                </div>
                {c.source_url && (
                  <div className="small mono faint" style={{ marginTop: 4 }}>
                    {c.source_url}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
