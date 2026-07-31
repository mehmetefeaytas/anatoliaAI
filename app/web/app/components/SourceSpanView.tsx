"use client";

/**
 * Kaynak-span vurgulama (CLAUDE.md §18 yenilikçilik hedefi #1) — demonun kalbi.
 *
 * Anlatı: "Her sayı bir karakter aralığına bağlıdır. Halüsinasyon yapamayız,
 * çünkü yapmadığımızı ispatlayabiliyoruz." Bir değer tıklandığında kaynak metin
 * açılır ve `span_start..span_end` aralığı vurgulanır.
 *
 * Dürüstlük kuralları:
 *  - Offset yoksa/doğrulanamadıysa vurgulama UYDURULMAZ; açık bir uyarı gösterilir.
 *  - `span_scope === "window"` ise yalnız değerin ÇEVRESİ vurgulanır ve bu söylenir.
 *  - `span_ambiguous` (aynı pencere metni belgede birden çok kez geçiyor) işaretlenir.
 *  - Doğrulama `src/schemas.py:verify_span()` mantığının API karşılığıdır
 *    (`span_verified`).
 */

import { useMemo, useState } from "react";
import type { SpanInfo } from "../lib/api";

type Props = {
  text: string;
  span: SpanInfo;
  /** Vurgulanan ham ifade — başlıkta gösterilir. */
  rawValue?: string | null;
  /** Varsayılan olarak yalnız span çevresi gösterilir; tam metne geçilebilir. */
  defaultFullText?: boolean;
};

/** Kısaltılmış görünümde span'in çevresinde bırakılan karakter sayısı. */
const CONTEXT_PAD = 320;

export default function SourceSpanView({
  text,
  span,
  rawValue,
  defaultFullText = false,
}: Props) {
  const [full, setFull] = useState(defaultFullText);

  const { start, end, ctxStart, ctxEnd, sliceFrom, sliceTo } = useMemo(() => {
    const s = span.span_start;
    const e = span.span_end;
    const ws = span.window_start ?? s;
    const we = span.window_end ?? e;
    if (s === null || e === null) {
      return {
        start: null, end: null, ctxStart: null, ctxEnd: null,
        sliceFrom: 0, sliceTo: full ? text.length : Math.min(text.length, 900),
      };
    }
    return {
      start: s,
      end: e,
      ctxStart: ws,
      ctxEnd: we,
      sliceFrom: full ? 0 : Math.max(0, (ws ?? s) - CONTEXT_PAD),
      sliceTo: full ? text.length : Math.min(text.length, (we ?? e) + CONTEXT_PAD),
    };
  }, [span, text.length, full]);

  if (!text) {
    return (
      <div className="notice notice-warn">
        <strong>Kaynak metin yok</strong>
        Bu kampanya için saklanmış ham metin bulunamadı; vurgulama yapılamaz.
      </div>
    );
  }

  const truncated = sliceFrom > 0 || sliceTo < text.length;

  return (
    <div>
      {start === null || end === null ? (
        <div className="notice notice-warn" style={{ marginBottom: 10 }}>
          <strong>Bu değer için karakter offset&apos;i doğrulanamadı</strong>
          Kaynak metin aşağıda ama vurgulama yapılmıyor — yanlış yeri boyamak,
          boyamamaktan kötüdür. (Değer yine de kaynağa dayanıyor:{" "}
          <span className="mono">source_span</span> metni saklı.)
        </div>
      ) : (
        <p className="offset-note">
          Vurgulanan aralık:{" "}
          <span className="mono">
            [{start}, {end})
          </span>{" "}
          · {end - start} karakter
          {rawValue ? (
            <>
              {" "}
              · ham ifade: <span className="mono">«{rawValue}»</span>
            </>
          ) : null}{" "}
          ·{" "}
          <span className={span.span_verified ? "badge badge-ok" : "badge badge-warn"}>
            {span.span_verified ? "offset doğrulandı" : "offset doğrulanamadı"}
          </span>
          {span.span_scope === "window" && (
            <>
              {" "}
              <span className="badge badge-warn" title="Ham değer tam olarak konumlandırılamadı">
                yalnızca çevre vurgulandı
              </span>
            </>
          )}
          {span.span_ambiguous && (
            <>
              {" "}
              <span className="badge badge-warn" title="Aynı pencere metni belgede birden çok kez geçiyor">
                birden çok eşleşme
              </span>
            </>
          )}
        </p>
      )}

      <div className="source-text">
        {sliceFrom > 0 && <span className="dim">…</span>}
        {renderSegments(text, sliceFrom, sliceTo, start, end, ctxStart, ctxEnd)}
        {sliceTo < text.length && <span className="dim">…</span>}
      </div>

      <p className="offset-note">
        Belge uzunluğu: <span className="mono">{text.length}</span> karakter
        {truncated && (
          <>
            {" · "}
            <button type="button" className="btn-link" onClick={() => setFull((v) => !v)}>
              {full ? "yalnızca çevresini göster" : "tam metni göster"}
            </button>
          </>
        )}
      </p>
    </div>
  );
}

/**
 * Metni [dilim başı .. dilim sonu] aralığında parçalara ayırıp vurgular.
 * Katmanlar: düz metin → bağlam penceresi (.ctx) → tam isabet (mark.hit).
 */
function renderSegments(
  text: string,
  from: number,
  to: number,
  start: number | null,
  end: number | null,
  ctxStart: number | null,
  ctxEnd: number | null,
) {
  if (start === null || end === null) {
    return <span>{text.slice(from, to)}</span>;
  }
  const cs = ctxStart === null ? start : Math.max(from, Math.min(ctxStart, start));
  const ce = ctxEnd === null ? end : Math.min(to, Math.max(ctxEnd, end));

  const parts: { key: string; cls: string; body: string }[] = [
    { key: "pre", cls: "", body: text.slice(from, cs) },
    { key: "ctx-a", cls: "ctx", body: text.slice(cs, start) },
    { key: "hit", cls: "hit", body: text.slice(start, end) },
    { key: "ctx-b", cls: "ctx", body: text.slice(end, ce) },
    { key: "post", cls: "", body: text.slice(ce, to) },
  ];

  return (
    <>
      {parts.map((p) => {
        if (!p.body) return null;
        if (p.cls === "hit") {
          return (
            <mark key={p.key} className="hit">
              {p.body}
            </mark>
          );
        }
        return (
          <span key={p.key} className={p.cls}>
            {p.body}
          </span>
        );
      })}
    </>
  );
}
