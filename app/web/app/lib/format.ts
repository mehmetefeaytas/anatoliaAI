/**
 * Görüntüleme yardımcıları — kanonik değer → Türkçe metin.
 *
 * İlgili: CLAUDE.md §10 (kanonik birimler), §19 (kullanıcıya dönük metinler Türkçe)
 * Sayı biçimi Türkçe kurala göre (binlik `.`, ondalık `,`) yazılır.
 */

import type { Extractor } from "./api";

const NF = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 });
/** Türkçe sayı biçimlendirici (binlik `.`, ondalık `,`). */
const trNum = NF.format.bind(NF);

function isRec(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

function num(v: unknown): string {
  return typeof v === "number" ? trNum(v) : String(v);
}

/** Kanonik değeri insan-okur Türkçe metne çevirir. */
export function formatValue(v: unknown, field?: string): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "var" : "yok";
  if (typeof v === "number") {
    if (field === "kar_payi_orani" || field === "indirim_orani") return `%${num(v)}`;
    if (field === "vade_ay") return `${num(v)} ay`;
    if (field === "taksit_sayisi") return `${num(v)} taksit`;
    return num(v);
  }
  if (Array.isArray(v)) return v.length ? v.map((x) => formatValue(x)).join(", ") : "—";
  if (isRec(v)) {
    if ("min" in v && "max" in v) {
      const pfx = field === "kar_payi_orani" || field === "indirim_orani" ? "%" : "";
      return `${pfx}${num(v.min)} – ${pfx}${num(v.max)}`;
    }
    if ("value" in v) {
      const cur = typeof v.currency === "string" ? v.currency : "";
      return `${num(v.value)} ${cur === "TRY" ? "TL" : cur}`.trim();
    }
    if ("has_fee" in v) {
      if (v.has_fee === false) return "masrafsız";
      const amt = v.amount;
      return amt === null || amt === undefined ? "masraf var" : `${num(amt)} TL`;
    }
    if ("segments" in v && Array.isArray(v.segments)) {
      return v.segments.length ? v.segments.join(", ") : "—";
    }
    if ("start" in v || "end" in v) {
      const s = v.start ? String(v.start) : "?";
      const e = v.end ? String(v.end) : "?";
      return `${s} → ${e}`;
    }
    return JSON.stringify(v);
  }
  return String(v);
}

/** Güven skorunun sözel seviyesi — renk TEK sinyal olmasın diye (erişilebilirlik). */
export function confidenceLevel(c: number | null): {
  label: string;
  color: string;
} {
  if (c === null || Number.isNaN(c)) {
    return { label: "bilinmiyor", color: "var(--fg-faint)" };
  }
  if (c >= 0.85) return { label: "yüksek", color: "var(--ok)" };
  if (c >= 0.6) return { label: "orta", color: "var(--warn)" };
  return { label: "düşük", color: "var(--bad)" };
}

/**
 * `confidence_source` → Türkçe etiket.
 *
 * Bu bir DÜRÜSTLÜK sinyalidir: skorun sabit mi, kanıttan mı, modelin
 * logprob'undan mı geldiğini jüriye açıkça söyler
 * (bkz. src/extraction/rules/confidence.py modül başlığı).
 */
export const CONFIDENCE_SOURCE_LABELS: Record<string, string> = {
  rule_heuristic: "kanıt tabanlı (kural sinyalleri)",
  constant: "sabit değer (kalibre edilmemiş)",
  logprob: "model logprob",
  self_reported: "modelin kendi beyanı",
};

export function confidenceSourceLabel(src: string | null): string {
  if (!src) return "kaydedilmedi";
  return CONFIDENCE_SOURCE_LABELS[src] ?? src;
}

/** Hangi katman üretti — jüri denetiminin çekirdek sorusu. */
export const EXTRACTOR_LABELS: Record<Extractor, string> = {
  rule: "kural",
  ner: "NER",
  llm: "LLM",
};

export function extractorLabel(e: Extractor | null): string {
  return e ? EXTRACTOR_LABELS[e] ?? e : "—";
}

export function extractorClass(e: Extractor | null): string {
  return e ? `badge badge-${e}` : "badge";
}

/** Çelişki türü → Türkçe başlık. */
export const CONTRADICTION_LABELS: Record<string, string> = {
  masrafsiz_ama_ucret: "«Masrafsız» denmiş ama tahsis ücreti var",
  masrafsiz_ama_tutar: "«Masrafsız» denmiş ama masraf tutarı var",
};

export function contradictionLabel(kind: string): string {
  return CONTRADICTION_LABELS[kind] ?? kind;
}
