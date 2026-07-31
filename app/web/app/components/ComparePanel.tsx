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
 */

import { useState } from "react";
import { api } from "../lib/api";
import type { CompareRow, FieldMeta } from "../lib/api";
import { extractorClass, extractorLabel, formatValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FieldChips from "./FieldChips";
import ScoringExplainer from "./ScoringExplainer";
import SourceSpanView from "./SourceSpanView";

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

export default function ComparePanel({ fields, campaignTypes }: Props) {
  const [field, setField] = useState(fields[0]?.field ?? "kar_payi_orani");
  const [intent, setIntent] = useState<Intent>("");
  const [type, setType] = useState("");
  const [openRow, setOpenRow] = useState<string | null>(null);

  const rows = useAsync(
    () => api.compare(field, intent || undefined, type || undefined),
    [field, intent, type],
  );
  const meta = fields.find((f) => f.field === field);

  return (
    <div className="stack">
      <section className="card">
        <h2>Karşılaştırma Paneli</h2>
        <p className="lede">
          Yalnızca aynı birime normalize edilmiş değerler kıyaslanır. Kıyaslanamayan
          değerler silinmez — gerekçesiyle listenin sonunda kalır (CLAUDE.md §17).
        </p>

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
          {meta && (
            <span className="badge" title="Kaynak: compare.py _LOWER_IS_BETTER / _HIGHER_IS_BETTER">
              {meta.direction_label}
            </span>
          )}
        </div>

        <div style={{ marginTop: 14 }}>
          {rows.loading && <Loading />}
          {!!rows.error && <ErrorNotice error={rows.error} />}
          {!rows.loading && !rows.error && rows.data?.length === 0 && (
            <EmptyNotice title="Bu alan için kayıt bulunamadı">
              API çalışıyor ve yanıt verdi, ancak seçilen alan
              {type ? ` ve «${type}» türü` : ""} için çıkarılmış değer yok. Bu bir
              hata değil: alan metinlerde geçmiyorsa sistem değer UYDURMAZ
              (CLAUDE.md §21).
            </EmptyNotice>
          )}
          {rows.data && rows.data.length > 0 && (
            <div className="table-wrap">
              <table className="data">
                <caption className="small muted" style={{ captionSide: "bottom", textAlign: "left", paddingTop: 8 }}>
                  Bir satırdaki «Kaynağı gör» bağlantısı, değerin kaynak metindeki
                  karakter aralığını vurgular.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Sıra</th>
                    <th scope="col">Banka</th>
                    <th scope="col">Değer</th>
                    <th scope="col">Güven</th>
                    <th scope="col">Katman</th>
                    <th scope="col">Durum</th>
                    <th scope="col">Kaynak</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.data.map((r, i) => {
                    const key = `${r.campaign_id}-${i}`;
                    const open = openRow === key;
                    return (
                      <RowPair
                        key={key}
                        row={r}
                        field={field}
                        open={open}
                        onToggle={() => setOpenRow(open ? null : key)}
                      />
                    );
                  })}
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
  field,
  open,
  onToggle,
}: {
  row: CompareRow;
  field: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <>
      <tr className={open ? "selected" : undefined}>
        <td className="num">
          <span className={`rank-pill${row.rank === 1 ? " first" : ""}`}>
            {row.rank ?? "—"}
          </span>
        </td>
        <td>
          {row.bank_name || row.bank}
          {row.campaign_type && (
            <div className="small faint">{row.campaign_type}</div>
          )}
        </td>
        <td className="num">
          <strong>{formatValue(row.value, field)}</strong>
          {row.raw_value && (
            <div className="small faint mono" title="Kaynak metindeki ham ifade">
              «{row.raw_value.trim()}»
            </div>
          )}
        </td>
        <td>
          <ConfidenceBadge value={row.confidence} source={row.confidence_source} />
          <div className="conf-src">{row.confidence_source ? `kaynak: ${labelOf(row.confidence_source)}` : "kaynak: kaydedilmedi"}</div>
        </td>
        <td>
          <span className={extractorClass(row.extractor)}>
            {extractorLabel(row.extractor)}
          </span>
        </td>
        <td>
          {row.comparable ? (
            <span className="badge badge-ok">kıyaslanabilir</span>
          ) : (
            <span className="badge badge-warn" title={row.note ?? ""}>
              {row.note ?? "kıyaslanamaz"}
            </span>
          )}
          {row.contradiction_count > 0 && (
            <div style={{ marginTop: 4 }}>
              <span className="badge badge-bad">
                {row.contradiction_count} çelişki
              </span>
            </div>
          )}
        </td>
        <td>
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
          <td colSpan={7}>
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
          <SourceSpanView text={doc.data.text} span={row} rawValue={row.raw_value} />
        </>
      )}
    </div>
  );
}
