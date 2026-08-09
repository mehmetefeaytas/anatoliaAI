"use client";

/**
 * Karşılaştırma Paneli — bankalar arası tek alan kıyası.
 *
 * İlgili: src/api/main.py `/compare`, src/comparison/compare.py (adil kıyas),
 *         CLAUDE.md §17
 *
 * Eskiye göre ne değişti:
 *  - 3 sabit alan yerine 12 alanın tamamı (`GET /fields`).
 *  - Her satırda GÜVEN skoru + güven kaynağı + hangi KATMAN ürettiği görünür.
 *  - Değere tıklanınca kaynak metin açılır ve span vurgulanır (`SourceSpanView`).
 *  - `intent` (en düşük / en yüksek) artık gerçekten çalışır.
 *  - Çelişki taşıyan kampanyalar satırda işaretlenir.
 *  - Hata artık yutulmuyor; "veri yok" ile "API kapalı" ayrı gösteriliyor.
 *
 * GÜVEN SKORU burada JÜRİ MODUNA bağlıdır (bkz. ../lib/juryMode.tsx): bu tablo
 * ticari/bilgi arayan izleyicinin gördüğü tek yüzeydir ve kalibre edilmemiş bir
 * skoru orada kalite iddiası gibi göstermek yanıltıcıdır. Denetim yüzeyleri
 * (Audit / Canlı Çıkarım / Şeffaf Skorlama) skoru her hâlde gösterir.
 *
 * ## ÜRÜN AİLESİ KAPISI (2026-08-09)
 *
 * Bu tablo «elma ile armut kıyaslıyor» diye bildirildi ve şikâyet yerindeydi.
 * Tür süzmesi VARDI ama varsayılanı «Tümü» idi ve `comparable` bayrağı yalnız
 * BİRİM uyumunu doğruluyordu, ürün ailesini değil. Sonuç: `vade_ay` alanında
 * 120 aylık bir **konut finansmanı** 1. sırada, 36 aylık bir **ihtiyaç
 * finansmanı** 2. sırada listeleniyordu — hiçbir uyarı olmadan.
 *
 * Çözüm süzmeyi zorunlu kılmak DEĞİL (o, veriyi gizlemek olurdu): «Tümü»
 * seçiliyken satırlar ürün ailesine göre BÖLÜMLENİYOR ve sıralama yalnız
 * bölüm içinde yapılıyor. Farklı aileler hiçbir koşulda aynı sıralamaya
 * girmiyor. `compare.py:502-507` bu boşluğu kendi docstring'inde zaten
 * yazmıştı; burası onun kullanıcıya dönük karşılığı.
 */

import { Fragment, useState } from "react";
import { api } from "../lib/api";
import type { CompareRow, FieldMeta, PerBank } from "../lib/api";
import { extractorClass, extractorLabel, formatValue } from "../lib/format";
import { useJuryMode } from "../lib/juryMode";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";
import FieldChips from "./FieldChips";
import ScoringExplainer from "./ScoringExplainer";
import SourceSpanView from "./SourceSpanView";
import SummaryNotice from "./SummaryNotice";

type Intent = "" | "lowest" | "highest";

const INTENTS: { key: Intent; label: string }[] = [
  { key: "", label: "Alanın doğal yönü" },
  { key: "lowest", label: "En düşük önce" },
  { key: "highest", label: "En yüksek önce" },
];

type Props = {
  fields: FieldMeta[];
  campaignTypes: string[];
};

/** Türü boş gelen satırların bölüm başlığı. */
const TURSUZ = "Türü belirlenemedi";

/**
 * Satırları ürün ailesine böler ve her bölüm içinde SIRA NUMARASINI yeniden
 * verir.
 *
 * Sunucu `rank`'i tüm sonuç kümesi üzerinden hesaplar; tek tür seçiliyken bu
 * zaten bölüm-içi sıradır. «Tümü» seçiliyken ise bir bölümün başında «5»
 * yazması kafa karıştırıcı olurdu — ve daha kötüsü, türler arasında bir
 * sıralama varmış izlenimi verirdi. Sıra bölüm içinde yeniden numaralanır;
 * `rank === null` olan (kıyaslanamaz) satırlar numara ALMAZ.
 */
function aileleriBol(
  rows: CompareRow[],
): { tur: string; satirlar: { row: CompareRow; sira: number | null }[] }[] {
  const bolumler = new Map<string, { row: CompareRow; sira: number | null }[]>();
  for (const row of rows) {
    const tur = row.campaign_type || TURSUZ;
    const liste = bolumler.get(tur) ?? [];
    liste.push({ row, sira: null });
    bolumler.set(tur, liste);
  }
  return Array.from(bolumler, ([tur, satirlar]) => {
    let konum = 0;
    return {
      tur,
      satirlar: satirlar.map(({ row }) => ({
        row,
        sira: row.rank === null ? null : ++konum,
      })),
    };
  });
}

export default function ComparePanel({ fields, campaignTypes }: Props) {
  const [field, setField] = useState(fields[0]?.field ?? "kar_payi_orani");
  const [intent, setIntent] = useState<Intent>("");
  const [type, setType] = useState("");
  const [perBank, setPerBank] = useState<PerBank>("best");
  const [openRow, setOpenRow] = useState<string | null>(null);
  const { jury } = useJuryMode();

  const rows = useAsync(
    () => api.compare(field, intent || undefined, type || undefined, perBank),
    [field, intent, type, perBank],
  );
  const meta = fields.find((f) => f.field === field);
  const bolumler = aileleriBol(rows.data ?? []);
  // Sütun sayısı: Sıra, Banka, Ürün, Değer, [Güven], Katman, Durum, Kaynak.
  const sutunSayisi = jury ? 8 : 7;

  return (
    <div className="stack">
      <section className="card">
        <h2>Karşılaştırma Paneli</h2>
        <p className="lede">
          Yalnızca aynı birime normalize edilmiş değerler kıyaslanır. Kıyaslanamayan
          değerler silinmez — gerekçesiyle listenin sonunda kalır.
        </p>

        <FairnessNotice />

        <FieldChips fields={fields} value={field} onChange={setField} />

        <div className="row" style={{ marginTop: 12 }}>
          <div className="row-tight">
            <label className="small muted" htmlFor="cmp-intent">
              Sıralama
            </label>
            <select
              id="cmp-intent"
              className="select"
              style={{ width: "auto" }}
              value={intent}
              onChange={(e) => setIntent(e.target.value as Intent)}
            >
              {INTENTS.map((i) => (
                <option key={i.key} value={i.key}>
                  {i.label}
                </option>
              ))}
            </select>
          </div>
          <div className="row-tight">
            <label className="small muted" htmlFor="cmp-type">
              Kampanya türü
            </label>
            <select
              id="cmp-type"
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
          <div className="row-tight">
            <label className="small muted" htmlFor="cmp-perbank">
              Banka başına
            </label>
            <select
              id="cmp-perbank"
              className="select"
              style={{ width: "auto" }}
              value={perBank}
              onChange={(e) => setPerBank(e.target.value as PerBank)}
            >
              <option value="best">En iyi kampanya (tek satır)</option>
              <option value="all">Tüm kampanyaları göster</option>
            </select>
          </div>
          {meta && (
            <span className="badge" title="Kaynak: compare.py _LOWER_IS_BETTER / _HIGHER_IS_BETTER">
              {meta.direction_label}
            </span>
          )}
        </div>

        <div style={{ marginTop: "var(--sp-4)" }}>
          {rows.loading && <Loading />}
          {!!rows.error && <ErrorNotice error={rows.error} />}
          {!rows.loading && !rows.error && rows.data?.length === 0 && (
            <EmptyNotice title="Bu alan için kayıt bulunamadı">
              API çalışıyor ve yanıt verdi, ancak seçilen alan
              {type ? ` ve «${type}» türü` : ""} için çıkarılmış değer yok. Bu bir
              hata değil: alan metinlerde geçmiyorsa sistem değer UYDURMAZ.
            </EmptyNotice>
          )}
          {rows.data && rows.data.length > 0 && (
            <div className="table-wrap">
              <table className="data stackable">
                <caption
                  className="small muted"
                  style={{
                    captionSide: "bottom",
                    textAlign: "left",
                    paddingTop: "var(--sp-2)",
                  }}
                >
                  Bir satırdaki «Kaynağı gör» bağlantısı, değerin kaynak metindeki
                  karakter aralığını vurgular. Sıra numaraları <b>ürün ailesi
                  içinde</b> verilir; aileler arasında sıralama yapılmaz.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Sıra</th>
                    <th scope="col">Banka</th>
                    <th scope="col">Ürün</th>
                    <th scope="col">Değer</th>
                    {jury && <th scope="col">Güven</th>}
                    <th scope="col">Katman</th>
                    <th scope="col">Durum</th>
                    <th scope="col">Kaynak</th>
                  </tr>
                </thead>
                <tbody>
                  {bolumler.map((bolum) => (
                    <Fragment key={bolum.tur}>
                      {/* Bölüm başlığı yalnız birden fazla aile varsa gerekli;
                          tek tür seçiliyken gereksiz bir katman olurdu. */}
                      {bolumler.length > 1 && (
                        <tr className="group-head">
                          <td colSpan={sutunSayisi}>
                            {bolum.tur} · {bolum.satirlar.length} banka
                          </td>
                        </tr>
                      )}
                      {bolum.satirlar.map(({ row, sira }, i) => {
                        const key = `${row.campaign_id}-${bolum.tur}-${i}`;
                        const open = openRow === key;
                        return (
                          <RowPair
                            key={key}
                            row={row}
                            sira={sira}
                            field={field}
                            open={open}
                            jury={jury}
                            sutunSayisi={sutunSayisi}
                            onToggle={() => setOpenRow(open ? null : key)}
                          />
                        );
                      })}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <ScoringExplainer field={field} type={type} />
    </div>
  );
}

function RowPair({
  row,
  sira,
  field,
  open,
  jury,
  sutunSayisi,
  onToggle,
}: {
  row: CompareRow;
  /** Ürün ailesi İÇİNDEKİ sıra; kıyaslanamaz satırlarda null. */
  sira: number | null;
  field: string;
  open: boolean;
  /** Jüri modu — güven sütunu yalnız açıkken basılır. */
  jury: boolean;
  sutunSayisi: number;
  onToggle: () => void;
}) {
  return (
    <>
      <tr className={open ? "selected" : undefined}>
        <td data-label="Sıra" className="num">
          <span className={`rank-pill${sira === 1 ? " first" : ""}`}>
            {sira ?? "—"}
          </span>
        </td>
        <td data-label="Banka">
          {row.bank_name || row.bank}
          {/* Elenen kampanyalar gizlenmiyor, SAYILIYOR. Tamamı «Tüm
              kampanyaları göster» ile alınabilir. */}
          {row.other_count > 0 && (
            <div className="small faint">
              +{row.other_count} kampanya daha
            </div>
          )}
        </td>
        <td data-label="Ürün" className="small muted">
          {row.campaign_type || <span className="faint">belirlenemedi</span>}
        </td>
        <td data-label="Değer" className="num">
          <strong>{formatValue(row.value, field)}</strong>
          {row.raw_value && (
            <div className="small faint mono" title="Kaynak metindeki ham ifade">
              «{row.raw_value.trim()}»
            </div>
          )}
        </td>
        {jury && (
          <td data-label="Güven">
            <ConfidenceBadge value={row.confidence} source={row.confidence_source} />
            <div className="conf-src">{row.confidence_source ? `kaynak: ${labelOf(row.confidence_source)}` : "kaynak: kaydedilmedi"}</div>
          </td>
        )}
        <td data-label="Katman">
          <span className={extractorClass(row.extractor)}>
            {extractorLabel(row.extractor)}
          </span>
        </td>
        <td data-label="Durum">
          {row.comparable ? (
            <span className="badge badge-ok">kıyaslanabilir</span>
          ) : (
            <span className="badge badge-warn" title={row.note ?? ""}>
              {row.note ?? "kıyaslanamaz"}
            </span>
          )}
          {row.contradiction_count > 0 && (
            <div style={{ marginTop: "var(--sp-1)" }}>
              <span className="badge badge-bad">
                {row.contradiction_count} çelişki
              </span>
            </div>
          )}
        </td>
        <td data-label="Kaynak">
          <button
            type="button"
            className="btn-link"
            aria-expanded={open}
            onClick={onToggle}
          >
            {open ? "kapat" : "Kaynağı gör"}
          </button>
        </td>
      </tr>
      {open && (
        <tr className="selected">
          <td colSpan={sutunSayisi}>
            <SourceDrawer row={row} />
          </td>
        </tr>
      )}
    </>
  );
}

function labelOf(src: string): string {
  // format.ts'deki sözlüğün kısa hali; tabloda satır yüksekliği korunsun diye.
  const map: Record<string, string> = {
    rule_heuristic: "kanıt tabanlı",
    constant: "sabit (kalibre değil)",
    logprob: "logprob",
    self_reported: "model beyanı",
  };
  return map[src] ?? src;
}

/** Satır açıldığında kaynak metni çekip span'i vurgular. */
function SourceDrawer({ row }: { row: CompareRow }) {
  const doc = useAsync(() => api.campaignText(row.campaign_id), [row.campaign_id]);

  return (
    <div className="stack" style={{ gap: 10 }}>
      {doc.loading && <Loading label="Kaynak metin getiriliyor…" />}
      {!!doc.error && <ErrorNotice error={doc.error} />}
      {doc.data && (
        <>
          <dl className="kv">
            <dt>Kaynak URL</dt>
            <dd className="mono">{doc.data.source_url ?? "—"}</dd>
            <dt>Belge no</dt>
            <dd className="mono">#{doc.data.campaign_id}</dd>
            {doc.data.scraped_at && (
              <>
                <dt>Toplanma</dt>
                <dd className="mono">{doc.data.scraped_at}</dd>
              </>
            )}
          </dl>
          <SummaryNotice ozet={doc.data.ozet} ozetKaynak={doc.data.ozet_kaynak} />
          <SourceSpanView
            text={doc.data.text}
            span={row}
            rawValue={row.raw_value}
            blocks={doc.data.bloklar}
          />
        </>
      )}
    </div>
  );
}
