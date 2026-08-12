/**
 * Alan bazlı güven göstergesi (CLAUDE.md §18 yenilikçilik hedefi #1).
 *
 * İlgili: ../lib/format.ts (`confidenceLevel`, `confidenceSourceLabel`),
 *         ../styles/components.css (`.conf*`), ./AuditPanel.tsx,
 *         src/extraction/rules/confidence.py
 *
 * Erişilebilirlik: renk TEK sinyal DEĞİLDİR. Her göstergede üç bilgi birlikte
 * verilir → renkli çubuk + sayısal skor + sözel seviye ("yüksek/orta/düşük").
 * Renk körü bir jüri üyesi de sıralamayı okuyabilir. Çubuk `aria-hidden`;
 * taşıdığı bilginin tamamı yanındaki metinde zaten yazılıdır.
 *
 * `confidence_source` ayrıca gösterilir: skorun sabit mi, kanıt tabanlı mı,
 * logprob mu olduğunu saklamak yerine söylemek dürüstlük sinyalidir
 * (bkz. src/extraction/rules/confidence.py — "kalibre edilmemiştir").
 *
 * ## `null` neden `0` değil
 *
 * Ölçülmemiş güven ile sıfır güven aynı şey değildir ve aynı çubuğa çizilmez:
 * `null` gelince dolgu HİÇ basılmaz, sayı yerine «—» ve sözel karşılık olarak
 * «bilinmiyor» yazılır. Boş bir çubuk «çok düşük güven» diye okunabilirdi;
 * metin o okumayı kapatır.
 *
 * ## Neden `title` yetmiyor da metin de yazılıyor
 *
 * `title` dokunmatik ekranda hiç açılmaz ve klavye kullanıcısında da güvenilmez.
 * Bu yüzden özet yine `title`'da durur (imleçle hızlı okuma için) ama hiçbir
 * bilgi YALNIZCA orada yaşamaz.
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
  const olculdu = value !== null && !Number.isNaN(value);
  const pct = olculdu ? Math.max(0, Math.min(1, value)) * 100 : 0;
  const text = olculdu ? value.toFixed(2).replace(".", ",") : "—";
  const srcText = confidenceSourceLabel(source ?? null);

  return (
    <span
      className="conf"
      /* Seviye CSS'e de açılıyor (`[data-seviye]`): biçim ayrımı gerektiğinde
         rengin yanına ikinci bir sinyal eklenebilsin. */
      data-seviye={olculdu ? label : "bilinmiyor"}
      title={`Güven ${text} (${label}) · kaynak: ${srcText}`}
    >
      <span className="conf-bar" aria-hidden="true">
        {/* Ölçülmediyse dolgu HİÇ basılmaz — genişliği 0 olan bir dolgu, sıfır
            güvenle karışırdı. */}
        {olculdu && <span style={{ width: `${pct}%`, background: color }} />}
      </span>
      <span className="conf-num" style={{ color }}>
        {text}
      </span>
      <span className="conf-level">{label}</span>
      {showSource && <span className="conf-src">· kaynak: {srcText}</span>}
    </span>
  );
}
