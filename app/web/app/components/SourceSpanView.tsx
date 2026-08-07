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
 *
 * Çerçeve katlaması `SourceText`e devredilmiştir. Bu bileşenin sözleşmesi
 * DEĞİŞMEDİ: tüm offsetler hâlâ HAM metne göredir; katlama yalnız hangi
 * karakterlerin ekrana basıldığını etkiler, hesabı değil.
 */

import { useMemo, useState } from "react";
import type { SpanInfo, TextBlock } from "../lib/api";
import SourceText from "./SourceText";

type Props = {
  text: string;
  span: SpanInfo;
  /** Vurgulanan ham ifade — başlıkta gösterilir. */
  rawValue?: string | null;
  /** Varsayılan olarak yalnız span çevresi gösterilir; tam metne geçilebilir. */
  defaultFullText?: boolean;
  /** API'den gelen çerçeve blokları (opsiyonel — yoksa düz metin). */
  blocks?: TextBlock[] | null;
};

/** Kısaltılmış görünümde span'in çevresinde bırakılan karakter sayısı. */
const CONTEXT_PAD = 320;

export default function SourceSpanView({
  text,
  span,
  rawValue,
  defaultFullText = false,
  blocks,
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

      <SourceText
        text={text}
        blocks={blocks}
        from={sliceFrom}
        to={sliceTo}
        hitStart={start}
        hitEnd={end}
        ctxStart={ctxStart}
        ctxEnd={ctxEnd}
        leadingEllipsis={sliceFrom > 0}
        trailingEllipsis={sliceTo < text.length}
      />

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

