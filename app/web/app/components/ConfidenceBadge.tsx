/**
 * Alan bazlı güven göstergesi (CLAUDE.md §18 yenilikçilik hedefi #1).
 *
 * Erişilebilirlik: renk TEK sinyal DEĞİLDİR. Her göstergede üç bilgi birlikte
 * verilir → renkli çubuk + sayısal skor + sözel seviye ("yüksek/orta/düşük").
 * Renk körü bir jüri üyesi de sıralamayı okuyabilir.
 *
 * `confidence_source` ayrıca gösterilir: skorun sabit mi, kanıt tabanlı mı,
 * logprob mu olduğunu saklamak yerine söylemek dürüstlük sinyalidir
 * (bkz. src/extraction/rules/confidence.py — "kalibre edilmemiştir").
 */

import { confidenceLevel, confidenceSourceLabel } from "../lib/format";

type Props = {
  value: number | null;
  source?: string | null;
  /** Güven kaynağını satır içinde göster (tablo dışında kullanışlı). */
  showSource?: boolean;
};

export default function ConfidenceBadge({ value, source, showSource }: Props) {
  const { label, color } = confidenceLevel(value);
  const pct = value === null ? 0 : Math.max(0, Math.min(1, value)) * 100;
  const text = value === null ? "—" : value.toFixed(2).replace(".", ",");
  const srcText = confidenceSourceLabel(source ?? null);

  return (
    <span
      className="conf"
      title={`Güven ${text} (${label}) · kaynak: ${srcText}`}
    >
      <span className="conf-bar" aria-hidden="true">
        <span style={{ width: `${pct}%`, background: color }} />
      </span>
      <span className="conf-num" style={{ color }}>
        {text}
      </span>
      <span className="conf-level">{label}</span>
      {showSource && <span className="conf-src">· {srcText}</span>}
    </span>
  );
}
