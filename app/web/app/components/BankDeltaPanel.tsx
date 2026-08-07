"use client";

/**
 * Banka İçi Delta — "bende ne eksik, rakipte ne var?"
 *
 * İlgili: src/api/main.py `/compare`, `/fields`, src/comparison/compare.py,
 *         CLAUDE.md §17 (adil kıyas garantisi)
 *
 * Diğer paneller müşterinin sorusunu ("hangi banka daha ucuz?") yanıtlar. Bu
 * panel BANKANIN sorusunu yanıtlar: *«bu ürün bizde yok; Türkiye Finans'ta var
 * ve %10 daha avantajlı»*. Aynı çıkarım verisi, tersinden okunmuş hâli.
 *
 * ÜÇ DELTA DURUMU (hepsi kaynak gösterimiyle):
 *   eksik ürün  — seçilen bankada bu alanda kayıt YOK, rakipte var.
 *   daha iyi    — iki taraf da kıyaslanabilir ve seçilen banka önde.
 *   daha kötü   — iki taraf da kıyaslanabilir ve rakip önde.
 *
 * HESAPLANMAYAN DURUM: taraflardan biri `comparable = false` ise (aralık,
 * zaman-koşullu oran, farklı para birimi) delta **boş bırakılır**. Yaklaşık bir
 * fark üretmek, tam da CLAUDE.md §17'nin yasakladığı uydurma sıralamadır.
 *
 * Veri kaynağı bilinçli olarak mevcut `/compare` ucudur; banka-özel yeni bir uç
 * beklenmeden çalışır. Fark hesabı istemcide yapılır ve API'nin `sort_key`
 * değerine dayanır — yani sıralama motoruyla AYNI sayıya.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { CampaignSummary, CompareRow, FieldMeta } from "../lib/api";
import { formatValue, trNum } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";

type Props = {
  fields: FieldMeta[];
  campaigns: CampaignSummary[];
  campaignTypes: string[];
  /** Belgeyi Jüri Audit Paneli'nde açar (page.tsx `inspect` deseni). */
  onInspect: (campaignId: number) => void;
};

type DeltaKind =
  | "eksik"
  | "daha-iyi"
  | "daha-kotu"
  | "esit"
  | "kiyaslanamaz"
  | "rakip-yok";

type DeltaRow = {
  meta: FieldMeta;
  kind: DeltaKind;
  /** Seçilen bankanın bu alandaki en iyi satırı. */
  mine: CompareRow | null;
  /** En iyi rakip satırı (sıralamada seçilen banka dışındaki ilk kayıt). */
  rival: CompareRow | null;
  /** Mutlak fark (sort_key farkı) — yalnız iki taraf da kıyaslanabilirse. */
  absDiff: number | null;
  /** Göreli fark (%) — rakibin değeri 0 ise hesaplanmaz. */
  relPct: number | null;
  /** Delta neden hesaplanamadı / durumun gerekçesi. */
  note: string | null;
};

/**
 * Farkın BİRİMİ değerin biriminden farklı olabilir: iki oranın farkı yüzde
 * değil YÜZDE PUANIDIR. `%1,89` ile `%2,49` arasındaki fark «%0,60» değil
 * «0,60 puan»dır; ikisini karıştırmak jüri önünde ölçü hatasıdır.
 */
const DELTA_UNITS: Record<string, string> = {
  kar_payi_orani: "puan",
  indirim_orani: "puan",
  vade_ay: "ay",
  taksit_sayisi: "taksit",
  finansman_tutari: "TL",
  odul_miktari: "TL",
  tahsis_ucreti: "TL",
  masraf_durumu: "TL",
  alisveris_puani: "TL",
};

function formatDelta(diff: number, field: string): string {
  const unit = DELTA_UNITS[field];
  const n = trNum(Math.abs(diff));
  return unit ? `${n} ${unit}` : n;
}

const KIND_LABEL: Record<DeltaKind, string> = {
  eksik: "eksik ürün",
  "daha-iyi": "daha iyi",
  "daha-kotu": "daha kötü",
  esit: "eşit",
  kiyaslanamaz: "kıyaslanamaz",
  "rakip-yok": "rakip kaydı yok",
};

const KIND_CLASS: Record<DeltaKind, string> = {
  eksik: "badge badge-bad",
  "daha-iyi": "badge badge-ok",
  "daha-kotu": "badge badge-warn",
  esit: "badge",
  kiyaslanamaz: "badge badge-warn",
  "rakip-yok": "badge",
};

/** Bir alandaki kıyas satırlarından seçilen banka için delta üretir. */
function buildDelta(meta: FieldMeta, rows: CompareRow[], bank: string): DeltaRow {
  // `/compare` satırları zaten sıralı gelir; bir tarafın İLK kıyaslanabilir
  // satırı o tarafın EN İYİ kaydıdır.
  const mineAll = rows.filter((r) => r.bank === bank);
  const rivalAll = rows.filter((r) => r.bank !== bank);

  const mine =
    mineAll.find((r) => r.comparable && r.sort_key !== null) ?? mineAll[0] ?? null;
  const rival =
    rivalAll.find((r) => r.comparable && r.sort_key !== null) ?? rivalAll[0] ?? null;

  if (rival === null) {
    return {
      meta, kind: "rakip-yok", mine, rival: null, absDiff: null, relPct: null,
      note: "Başka hiçbir bankada bu alan için kayıt yok.",
    };
  }
  if (mineAll.length === 0) {
    return {
      meta, kind: "eksik", mine: null, rival, absDiff: null, relPct: null,
      note: "Bu bankada bu alan için çıkarılmış değer yok.",
    };
  }

  const mineKey = mine && mine.comparable ? mine.sort_key : null;
  const rivalKey = rival.comparable ? rival.sort_key : null;
  if (mineKey === null || rivalKey === null) {
    return {
      meta, kind: "kiyaslanamaz", mine, rival, absDiff: null, relPct: null,
      // Gerekçe API'den gelir ("aralık — doğrudan kıyaslanamaz" vb.); burada
      // yeniden yazılmaz ki arayüz ile motor aynı şeyi söylesin.
      note:
        (mineKey === null ? mine?.note : rival.note) ??
        "değerler aynı birime indirgenemiyor",
    };
  }

  const diff = mineKey - rivalKey;
  if (diff === 0) {
    return { meta, kind: "esit", mine, rival, absDiff: 0, relPct: 0, note: null };
  }

  const lowerIsBetter = meta.direction === "lower_is_better";
  const better = lowerIsBetter ? diff < 0 : diff > 0;
  // Göreli fark rakibin değerine oranlanır. Rakip 0 ise oran tanımsızdır
  // (0'a bölme) — ve 0 burada gerçek bir üründür, hata değil: yalnız mutlak
  // fark gösterilir.
  const relPct = rivalKey === 0 ? null : (Math.abs(diff) / Math.abs(rivalKey)) * 100;

  return {
    meta,
    kind: better ? "daha-iyi" : "daha-kotu",
    mine,
    rival,
    absDiff: Math.abs(diff),
    relPct,
    note: null,
  };
}

export default function BankDeltaPanel({
  fields,
  campaigns,
  campaignTypes,
  onInspect,
}: Props) {
  const banks = useMemo(() => {
    const seen = new Map<string, string>();
    for (const c of campaigns) {
      if (c.bank && !seen.has(c.bank)) seen.set(c.bank, c.bank_name || c.bank);
    }
    return Array.from(seen, ([slug, name]) => ({ slug, name }));
  }, [campaigns]);

  const [bank, setBank] = useState(banks[0]?.slug ?? "");
  const [type, setType] = useState("");

  // Banka listesi kampanya isteğiyle birlikte SONRADAN dolabilir; seçim boş
  // kalırsa panel hiçbir şey göstermez. İlk bankaya düş.
  useEffect(() => {
    if (banks.length === 0) return;
    if (!bank || !banks.some((b) => b.slug === bank)) setBank(banks[0].slug);
  }, [banks, bank]);

  const comparableFields = useMemo(
    () => fields.filter((f) => f.comparable_field),
    [fields],
  );

  // Alan başına bir `/compare` isteği. Banka seçimi değişince YENİDEN
  // çekilmez; fark hesabı istemcide yapılır (demoda her tıklamada onlarca
  // istek atmamak için bilinçli).
  const data = useAsync(async () => {
    const results = await Promise.all(
      comparableFields.map((f) => api.compare(f.field, undefined, type || undefined)),
    );
    return comparableFields.map((meta, i) => ({ meta, rows: results[i] }));
  }, [comparableFields, type]);

  const deltas: DeltaRow[] = useMemo(() => {
    if (!data.data || !bank) return [];
    return data.data.map((d) => buildDelta(d.meta, d.rows, bank));
  }, [data.data, bank]);

  const bankName = banks.find((b) => b.slug === bank)?.name ?? bank;
  const ownCampaigns = campaigns.filter(
    (c) => c.bank === bank && (!type || c.campaign_type === type),
  );

  const counts = useMemo(() => {
    const c: Record<DeltaKind, number> = {
      eksik: 0, "daha-iyi": 0, "daha-kotu": 0, esit: 0,
      kiyaslanamaz: 0, "rakip-yok": 0,
    };
    for (const d of deltas) c[d.kind] += 1;
    return c;
  }, [deltas]);

  const missing = deltas.filter((d) => d.kind === "eksik");
  const worse = deltas.filter((d) => d.kind === "daha-kotu");

  if (banks.length === 0) {
    return (
      <section className="card">
        <h2>Banka İçi Delta</h2>
        <EmptyNotice title="Kıyaslanacak banka yok">
          <span className="mono">/campaigns</span> ucundan hiçbir kampanya
          dönmedi; delta hesaplanamaz.
        </EmptyNotice>
      </section>
    );
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>Banka İçi Delta — bende ne eksik, rakipte ne var?</h2>
        <p className="lede">
          Bir banka seçin: her alanda o bankanın kendi en iyi kaydı ile en iyi
          rakip kayıt yan yana konur. Eksik ürünler, geride kalınan alanlar ve
          önde olunan alanlar kaynağıyla listelenir.
        </p>

        <div className="row">
          <div className="row-tight">
            <label className="small muted" htmlFor="delta-bank">
              Banka
            </label>
            <select
              id="delta-bank"
              className="select"
              style={{ width: "auto" }}
              value={bank}
              onChange={(e) => setBank(e.target.value)}
            >
              {banks.map((b) => (
                <option key={b.slug} value={b.slug}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
          <div className="row-tight">
            <label className="small muted" htmlFor="delta-type">
              Kampanya türü
            </label>
            <select
              id="delta-type"
              className="select"
              style={{ width: "auto" }}
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="">Tümü</option>
              {campaignTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <span className="small faint">
            {ownCampaigns.length} belge · {comparableFields.length} kıyaslanabilir alan
          </span>
        </div>

        <FairnessNotice />

        {data.loading && <Loading label="Alanlar karşılaştırılıyor…" />}
        {!!data.error && <ErrorNotice error={data.error} />}

        {!data.loading && !data.error && ownCampaigns.length === 0 && (
          <EmptyNotice title={`${bankName} için bu filtrede belge yok`}>
            Seçilen kampanya türünde bu bankaya ait hiçbir belge toplanmamış.
            Aşağıdaki «eksik ürün» satırları bundan kaynaklanıyor olabilir — veri
            eksikliği ile ürün eksikliği aynı şey değildir, ayrımı bu not verir.
          </EmptyNotice>
        )}

        {!data.loading && !data.error && deltas.length > 0 && (
          <>
            <div className="stats" style={{ marginTop: 14 }}>
              <div className="stat">
                <div className="k">Eksik ürün</div>
                <div
                  className="v"
                  style={{ color: counts.eksik ? "var(--bad)" : "var(--ok)" }}
                >
                  {counts.eksik}
                </div>
              </div>
              <div className="stat">
                <div className="k">Geride</div>
                <div
                  className="v"
                  style={{ color: counts["daha-kotu"] ? "var(--warn)" : "var(--fg)" }}
                >
                  {counts["daha-kotu"]}
                </div>
              </div>
              <div className="stat">
                <div className="k">Önde</div>
                <div className="v" style={{ color: "var(--ok)" }}>
                  {counts["daha-iyi"]}
                </div>
              </div>
              <div className="stat">
                <div className="k">Eşit</div>
                <div className="v">{counts.esit}</div>
              </div>
              <div className="stat">
                <div className="k">Kıyaslanamaz</div>
                <div className="v">{counts.kiyaslanamaz}</div>
              </div>
            </div>

            {(missing.length > 0 || worse.length > 0) && (
              <div className="headlines">
                {missing.map((d) => (
                  <p key={`m-${d.meta.field}`} className="headline headline-bad">
                    <b>{d.meta.label}</b> — {bankName} tarafında kayıt yok;{" "}
                    <b>{d.rival?.bank_name || d.rival?.bank}</b> tarafında var:{" "}
                    <span className="mono">
                      {formatValue(d.rival?.value, d.meta.field)}
                    </span>
                  </p>
                ))}
                {worse.map((d) => (
                  <p key={`w-${d.meta.field}`} className="headline headline-warn">
                    <b>{d.meta.label}</b> —{" "}
                    <b>{d.rival?.bank_name || d.rival?.bank}</b> daha avantajlı:{" "}
                    {d.absDiff !== null ? formatDelta(d.absDiff, d.meta.field) : "—"}{" "}
                    fark
                    {d.relPct !== null ? ` (göreli %${trNum(d.relPct)})` : ""}
                  </p>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      {!data.loading && !data.error && deltas.length > 0 && (
        <section className="card">
          <h2>Alan alan delta</h2>
          <div className="table-wrap">
            <table className="data">
              <caption
                className="small muted"
                style={{ captionSide: "bottom", textAlign: "left", paddingTop: 8 }}
              >
                Fark yalnız iki tarafın da kıyaslanabilir olduğu satırlarda
                hesaplanır; aksi hâlde hücre boş bırakılır (uydurma delta yok).
                Oran alanlarında fark yüzde değil <b>yüzde puanıdır</b>.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Alan</th>
                  <th scope="col">{bankName}</th>
                  <th scope="col">En iyi rakip</th>
                  <th scope="col">Fark</th>
                  <th scope="col">Durum</th>
                  <th scope="col">Kaynak</th>
                </tr>
              </thead>
              <tbody>
                {deltas.map((d) => (
                  <tr key={d.meta.field}>
                    <td>
                      {d.meta.label}
                      <div className="small faint">{d.meta.direction_label}</div>
                    </td>
                    <td className="num">
                      {d.mine ? (
                        <>
                          <strong>{formatValue(d.mine.value, d.meta.field)}</strong>
                          {d.mine.raw_value && (
                            <div className="small faint mono">
                              «{d.mine.raw_value.trim()}»
                            </div>
                          )}
                        </>
                      ) : (
                        <span className="faint">—</span>
                      )}
                    </td>
                    <td className="num">
                      {d.rival ? (
                        <>
                          <strong>{formatValue(d.rival.value, d.meta.field)}</strong>
                          <div className="small faint">
                            {d.rival.bank_name || d.rival.bank}
                          </div>
                        </>
                      ) : (
                        <span className="faint">—</span>
                      )}
                    </td>
                    <td className="num">
                      {d.absDiff === null ? (
                        <span className="faint" title={d.note ?? ""}>
                          —
                        </span>
                      ) : (
                        <>
                          <strong>{formatDelta(d.absDiff, d.meta.field)}</strong>
                          {d.relPct !== null && (
                            <div className="small faint">
                              göreli %{trNum(d.relPct)}
                            </div>
                          )}
                        </>
                      )}
                    </td>
                    <td>
                      <span className={KIND_CLASS[d.kind]}>{KIND_LABEL[d.kind]}</span>
                      {d.note && <div className="small faint">{d.note}</div>}
                    </td>
                    <td>
                      <DeltaSources row={d} onInspect={onInspect} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}

/** Her delta satırının iki tarafı da kaynağına bağlanır. */
function DeltaSources({
  row,
  onInspect,
}: {
  row: DeltaRow;
  onInspect: (campaignId: number) => void;
}) {
  const entries: { etiket: string; r: CompareRow }[] = [];
  if (row.mine) entries.push({ etiket: "bu banka", r: row.mine });
  if (row.rival) entries.push({ etiket: "rakip", r: row.rival });

  if (entries.length === 0) return <span className="faint">—</span>;

  return (
    <div className="stack" style={{ gap: 4 }}>
      {entries.map((e) => (
        <div
          key={`${e.etiket}-${e.r.campaign_id}`}
          className="row-tight"
          style={{ gap: 8 }}
        >
          <span className="small faint">{e.etiket}</span>
          <button
            type="button"
            className="btn-link"
            onClick={() => onInspect(e.r.campaign_id)}
          >
            belgeye git (#{e.r.campaign_id})
          </button>
          {e.r.source_url && (
            <a
              className="btn-link"
              href={e.r.source_url}
              target="_blank"
              rel="noreferrer noopener"
              title={e.r.source_url}
            >
              banka sayfası ↗
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
