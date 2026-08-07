"use client";

/**
 * Ham metin gösterici — çerçeve bloklarını KATLAR, offsetleri bozmaz.
 *
 * İlgili: ../lib/api.ts (`TextBlock`), ./SourceSpanView.tsx, ./AuditPanel.tsx,
 *         src/api/main.py `GET /campaigns/{id}/text` (`bloklar`)
 *
 * SÖZLEŞME (bozulursa vurgular kayar):
 *  - `bloklar` ham metni **bitişik ve eksiksiz** kaplar: ilk blok 0'dan başlar,
 *    her bloğun `start`'ı bir öncekinin `end`'i, son bloğun `end`'i metin
 *    uzunluğudur. Bu doğrulanmazsa katlama TAMAMEN devre dışı kalır ve metin
 *    eskisi gibi düz gösterilir — yanlış yeri katlamak, katlamamaktan kötüdür.
 *  - Vurgu offset'leri (`hitStart/hitEnd`, `ctxStart/ctxEnd`) HAM METNE göredir.
 *    Katlama yalnız hangi karakter aralıklarının EKRANA basılacağını değiştirir;
 *    hiçbir yerde metin yeniden numaralandırılmaz.
 *  - **Kanıt gizlenemez:** vurgulanan aralığa dokunan bir blok `gizle: true`
 *    olsa bile otomatik açılır ve neden açıldığı yazılır.
 *  - Katlanan blok SİLİNMEZ; kaç blok, hangi gerekçeyle katlandığı yazılır ve
 *    tek tıkla açılır.
 */

import { useMemo, useState, type ReactNode } from "react";
import type { TextBlock } from "../lib/api";
import { blockReasonLabel } from "../lib/format";

type Props = {
  /** Ham metin — tüm offsetlerin ölçüldüğü metin. */
  text: string;
  /** API'den gelen çerçeve blokları. Yoksa/geçersizse düz metne düşülür. */
  blocks?: TextBlock[] | null;
  /** Gösterilecek dilim (ham metin offset'i). Verilmezse tüm metin. */
  from?: number;
  to?: number;
  /** Tam isabet aralığı (ham metin offset'i). */
  hitStart?: number | null;
  hitEnd?: number | null;
  /** Bağlam penceresi aralığı (ham metin offset'i). */
  ctxStart?: number | null;
  ctxEnd?: number | null;
  /** Dilim metnin başından/sonundan kırpıldıysa üç nokta göster. */
  leadingEllipsis?: boolean;
  trailingEllipsis?: boolean;
};

/**
 * Blokların ham metni bitişik ve eksiksiz kapladığını doğrular.
 * Doğrulanamazsa `null` döner → çağıran düz metne düşer.
 */
export function normalizeBlocks(
  text: string,
  blocks: TextBlock[] | null | undefined,
): TextBlock[] | null {
  if (!Array.isArray(blocks) || blocks.length === 0) return null;
  let cursor = 0;
  for (const b of blocks) {
    if (
      typeof b?.start !== "number" ||
      typeof b?.end !== "number" ||
      b.start !== cursor ||
      b.end <= b.start
    ) {
      return null;
    }
    cursor = b.end;
  }
  if (cursor !== text.length) return null;
  return blocks;
}

/** Katlanan blokların gerekçelerini tekilleştirip «çerez/KVKK» hâline getirir. */
function reasonSummary(blocks: TextBlock[]): string {
  const seen: string[] = [];
  for (const b of blocks) {
    const label = blockReasonLabel(b.gerekce);
    if (!seen.includes(label)) seen.push(label);
  }
  return seen.join("/");
}

export default function SourceText({
  text,
  blocks,
  from = 0,
  to,
  hitStart = null,
  hitEnd = null,
  ctxStart = null,
  ctxEnd = null,
  leadingEllipsis = false,
  trailingEllipsis = false,
}: Props) {
  const sliceTo = to ?? text.length;
  const [opened, setOpened] = useState<ReadonlyArray<number>>([]);

  const valid = useMemo(() => normalizeBlocks(text, blocks), [text, blocks]);

  // Kanıt aralığı: vurgu + bağlam penceresinin birleşimi.
  const evidence = useMemo(() => {
    const starts = [hitStart, ctxStart].filter((v): v is number => v !== null);
    const ends = [hitEnd, ctxEnd].filter((v): v is number => v !== null);
    if (starts.length === 0 || ends.length === 0) return null;
    return { start: Math.min(...starts), end: Math.max(...ends) };
  }, [hitStart, hitEnd, ctxStart, ctxEnd]);

  const body: ReactNode = useMemo(() => {
    if (!valid) {
      return renderRange(text, from, sliceTo, hitStart, hitEnd, ctxStart, ctxEnd);
    }
    return renderBlocks({
      text,
      blocks: valid,
      from,
      to: sliceTo,
      hitStart,
      hitEnd,
      ctxStart,
      ctxEnd,
      evidence,
      opened,
      onOpen: (indexes) =>
        setOpened((prev) => [...prev, ...indexes.filter((i) => !prev.includes(i))]),
      onClose: (indexes) =>
        setOpened((prev) => prev.filter((i) => !indexes.includes(i))),
    });
  }, [
    valid, text, from, sliceTo, hitStart, hitEnd, ctxStart, ctxEnd, evidence, opened,
  ]);

  return (
    <div className="source-text">
      {leadingEllipsis && <span className="dim">…</span>}
      {body}
      {trailingEllipsis && <span className="dim">…</span>}
    </div>
  );
}

/** Bir blok kümesini görünür / katlanmış gruplara ayırıp basar. */
function renderBlocks(args: {
  text: string;
  blocks: TextBlock[];
  from: number;
  to: number;
  hitStart: number | null;
  hitEnd: number | null;
  ctxStart: number | null;
  ctxEnd: number | null;
  evidence: { start: number; end: number } | null;
  opened: ReadonlyArray<number>;
  onOpen: (indexes: number[]) => void;
  onClose: (indexes: number[]) => void;
}): ReactNode {
  const {
    text, blocks, from, to, hitStart, hitEnd, ctxStart, ctxEnd, evidence,
    opened, onOpen, onClose,
  } = args;

  const out: ReactNode[] = [];
  /** Ardışık katlanacak bloklar — tek bir «N blok gizlendi» şeridi olurlar. */
  let pending: { index: number; block: TextBlock; a: number; b: number }[] = [];

  function flush() {
    if (pending.length === 0) return;
    const group = pending;
    pending = [];
    const indexes = group.map((g) => g.index);
    const key = `fold-${indexes[0]}`;
    const isOpen = indexes.every((i) => opened.includes(i));
    const summary = reasonSummary(group.map((g) => g.block));

    if (!isOpen) {
      out.push(
        <button
          key={key}
          type="button"
          className="fold"
          onClick={() => onOpen(indexes)}
        >
          {group.length} blok çerçeve gizlendi ({summary}) — göster
        </button>,
      );
      return;
    }
    out.push(
      <button
        key={`${key}-close`}
        type="button"
        className="fold fold-open"
        onClick={() => onClose(indexes)}
      >
        {group.length} blok çerçeve açık ({summary}) — gizle
      </button>,
    );
    for (const g of group) {
      out.push(
        <span key={`b-${g.index}`} className="folded-body">
          {renderRange(text, g.a, g.b, hitStart, hitEnd, ctxStart, ctxEnd)}
        </span>,
      );
    }
  }

  blocks.forEach((block, index) => {
    const a = Math.max(from, block.start);
    const b = Math.min(to, block.end);
    if (b <= a) return; // dilimin dışında

    const touchesEvidence =
      evidence !== null && block.start < evidence.end && block.end > evidence.start;

    if (block.gizle && !touchesEvidence) {
      pending.push({ index, block, a, b });
      return;
    }

    flush();

    if (block.gizle && touchesEvidence) {
      // Kanıt gizlenemez: blok `gizle: true` olsa da açık basılır ve NEDEN
      // açık olduğu yazılır — sessizce açmak, katlamayı güvenilmez kılardı.
      out.push(
        <span key={`why-${index}`} className="fold-note">
          çerçeve bloğu ({blockReasonLabel(block.gerekce)}) — vurgulanan kanıtı
          içerdiği için açık bırakıldı
        </span>,
      );
    }
    out.push(
      <span key={`v-${index}`}>
        {renderRange(text, a, b, hitStart, hitEnd, ctxStart, ctxEnd)}
      </span>,
    );
  });

  flush();
  return <>{out}</>;
}

/**
 * `[a, b)` aralığını vurgu katmanlarına bölerek basar.
 * Katmanlar: düz metin → bağlam penceresi (.ctx) → tam isabet (mark.hit).
 */
function renderRange(
  text: string,
  a: number,
  b: number,
  hitStart: number | null,
  hitEnd: number | null,
  ctxStart: number | null,
  ctxEnd: number | null,
): ReactNode {
  if (b <= a) return null;

  const inHit = (pos: number) =>
    hitStart !== null && hitEnd !== null && pos >= hitStart && pos < hitEnd;
  const inCtx = (pos: number) =>
    ctxStart !== null && ctxEnd !== null && pos >= ctxStart && pos < ctxEnd;

  // Sınır noktaları: aralığı vurgu kenarlarından böleriz. Sıralı ve tekil.
  const bounds = Array.from(
    new Set(
      [a, b, hitStart, hitEnd, ctxStart, ctxEnd]
        .filter((v): v is number => v !== null)
        .filter((v) => v >= a && v <= b),
    ),
  ).sort((x, y) => x - y);

  const parts: ReactNode[] = [];
  for (let i = 0; i < bounds.length - 1; i += 1) {
    const s = bounds[i];
    const e = bounds[i + 1];
    if (e <= s) continue;
    const body = text.slice(s, e);
    if (!body) continue;
    if (inHit(s)) {
      parts.push(
        <mark key={`h-${s}`} className="hit">
          {body}
        </mark>,
      );
    } else if (inCtx(s)) {
      parts.push(
        <span key={`c-${s}`} className="ctx">
          {body}
        </span>,
      );
    } else {
      parts.push(<span key={`p-${s}`}>{body}</span>);
    }
  }
  return <>{parts}</>;
}
