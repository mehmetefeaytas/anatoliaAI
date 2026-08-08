/**
 * Markdown alt kümesi render'ı — React elemanı üretir, HTML dizgesi ÜRETMEZ.
 *
 * İlgili: ../../lib/markdown.ts (ayrıştırıcı + testleri), ../ChatPanel.tsx
 *
 * Ayrıştırma ve render bilerek ayrıldı: ayrıştırıcı saf bir fonksiyondur ve
 * `web/tests/markdown.test.ts` içinde 21 testle doğrulanır; burası yalnız
 * token → eleman eşlemesi yapar.
 *
 * Güvenlik: ham HTML enjekte eden React kaçış kapısı hiç kullanılmaz, o yüzden
 * XSS yapı gereği imkânsızdır (ayrıntı: ../../lib/markdown.ts başlığı).
 */

import { Fragment } from "react";
import { markdownAyristir, type Inline } from "../../lib/markdown";

/** İç içe işaretleri özyinelemeli basar (kalın içinde italik ve tersi). */
function Parcalar({ parcalar }: { parcalar: Inline[] }) {
  return (
    <>
      {parcalar.map((p, i) => {
        if (p.tur === "strong") {
          return (
            <strong key={i}>
              <Parcalar parcalar={p.cocuklar} />
            </strong>
          );
        }
        if (p.tur === "em") {
          return (
            <em key={i}>
              <Parcalar parcalar={p.cocuklar} />
            </em>
          );
        }
        if (p.tur === "code") return <code key={i}>{p.icerik}</code>;
        return <Fragment key={i}>{p.icerik}</Fragment>;
      })}
    </>
  );
}

export default function Markdown({ metin }: { metin: string }) {
  const bloklar = markdownAyristir(metin);

  // Ayrıştırma hiçbir şey üretmediyse (yalnız boşluk) ham metne düşülür —
  // sessizce boş bir kutu göstermek, cevabın kaybolduğu izlenimi verirdi.
  if (bloklar.length === 0) {
    return <div className="md">{metin}</div>;
  }

  return (
    <div className="md">
      {bloklar.map((blok, bi) => {
        if (blok.tur === "ul") {
          return (
            <ul key={bi}>
              {blok.ogeler.map((oge, oi) => (
                <li key={oi}>
                  <Parcalar parcalar={oge} />
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={bi}>
            {blok.satirlar.map((satir, si) => (
              <Fragment key={si}>
                {/* Paragraf içi satır sonu korunur (eski `pre-wrap` davranışı). */}
                {si > 0 && <br />}
                <Parcalar parcalar={satir} />
              </Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
