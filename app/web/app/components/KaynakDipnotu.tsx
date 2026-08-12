"use client";

/**
 * Kaynak dipnotu — rakamın yanındaki rozete basınca belge yandan açılır.
 *
 * İlgili: ./SourceSpanView.tsx, ./SourceText.tsx, ../lib/api.ts (campaignText),
 *         ../lib/useAsync.ts, CLAUDE.md §18 (yenilikçilik hedefi #1)
 *
 * ## Neden tek bileşen
 *
 * «Neyi nereden aldın» bilgisi sistemde zaten vardı ama PASİFTİ: kıyas
 * tablosunda satır içi bir çekmece, sohbette bir bağlantı, en avantajlı
 * ekranında hiçbir şey — beş yüzeyde beş ayrı jest. Jüri profili banka
 * görevlisi ve en çok test edeceği şey bu; güvenilirlik algısının tamamı
 * buradan geliyor. Bu yüzden tek bir dipnot bileşeni her yerde AYNI jesti
 * veriyor: rozete bas, belge yandan açılsın, ilgili aralık vurgulu olsun.
 *
 * ## Neden yan panel, satır içi çekmece değil
 *
 * Satır içi çekmece tabloyu iterek açılıyor ve kullanıcı okumaya çalıştığı
 * satırı kaybediyor. Yan panel tabloyu yerinde bırakıyor: rakam solda,
 * kanıtı sağda — göz ikisini aynı anda görüyor. Kanıt gösteren bir üründe
 * iddianın kanıtla aynı ekranda kalması önemsiz bir ayrıntı değil.
 *
 * ## Yükleme gecikmesi
 *
 * Belge metni AÇILDIĞINDA çekilir, tabloyla birlikte değil. 1.774 belgenin
 * metnini önden yüklemek, kapatılan yükün (10,3 MB) aynısını geri getirirdi.
 *
 * ## Rozetin üstünde neden ARALIK yazıyor
 *
 * Eskiden `¶ #1284`, yani belge numarası yazıyordu — düğmenin açtığı şeyin
 * belge OLDUĞUNU söylüyor, ama nereye götürdüğünü söylemiyordu. Artık span
 * varsa `¶ 1284–1298`, yani KARAKTER ARALIĞI yazıyor: bu ürünün tezi «her
 * sayı bir aralığa bağlıdır» ve düğmenin yüzü de tam olarak onu basıyor.
 * Aralık yoksa belge numarasına düşülür; uydurulmuş bir aralık basılmaz.
 *
 * Panelin `aria-label`'ı ve başlığı BELGE NUMARASINI korur: rozetin yüzü
 * değişse de açılan şey hâlâ bir belgedir ve ekran okuyucuya «Belge
 * 1284–1298» demek yanlış olurdu.
 */

import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { SpanInfo } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { ErrorNotice, Loading } from "./ErrorNotice";
import SourceSpanView from "./SourceSpanView";

type Props = {
  campaignId: number;
  /** Vurgulanacak aralık. Yoksa belge başından açılır. */
  span?: SpanInfo | null;
  /** Rozette görünecek kısa etiket — varsayılan belge numarası. */
  etiket?: string;
  /** Ham ifade, panel başlığında gösterilir. */
  rawValue?: string | null;
};

const BOS_SPAN: SpanInfo = {
  span_start: null,
  span_end: null,
  span_scope: null,
  span_verified: false,
  span_ambiguous: false,
  window_start: null,
  window_end: null,
};

export default function KaynakDipnotu({
  campaignId,
  span,
  etiket,
  rawValue,
}: Props) {
  const [acik, setAcik] = useState(false);
  const dugmeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Panel yalnız açıkken istek atar; kapalıyken `useAsync` hiç koşmaz.
  const belge = useAsync(
    () => (acik ? api.campaignText(campaignId) : Promise.resolve(null)),
    [acik, campaignId],
  );

  // Esc ile kapanır ve odak rozete DÖNER: klavye kullanıcısı panel açılıp
  // kapandıktan sonra tablonun başına fırlatılmamalı.
  useEffect(() => {
    if (!acik) return;
    const tusa = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setAcik(false);
        dugmeRef.current?.focus();
      }
    };
    document.addEventListener("keydown", tusa);
    return () => document.removeEventListener("keydown", tusa);
  }, [acik]);

  // Açılınca odak panele taşınır — yoksa ekran okuyucu yeni içeriği duyurmaz.
  useEffect(() => {
    if (acik) panelRef.current?.focus();
  }, [acik]);

  /** Panelin ve ekran okuyucunun gördüğü ad — her zaman belge numarası. */
  const belgeAdi = `#${campaignId}`;
  /** Rozetin yüzü: dışarıdan verilen etiket → karakter aralığı → belge no. */
  const aralik =
    span && span.span_start !== null && span.span_end !== null
      ? `${span.span_start}–${span.span_end}`
      : null;
  const yuz = etiket ?? aralik ?? belgeAdi;

  return (
    <>
      <button
        ref={dugmeRef}
        type="button"
        className="kaynak-dipnot"
        aria-expanded={acik}
        title="Kaynak cümleyi ve karakter aralığını aç"
        onClick={() => setAcik((a) => !a)}
      >
        <span aria-hidden="true">¶</span>
        <span className="kaynak-dipnot-etiket">{yuz}</span>
        {/* Ekran okuyucu için düğmenin ne YAPTIĞI; gözle görünen yüz bir
            koordinat olduğu için tek başına eylemi anlatmıyor. */}
        <span className="gorunmez">
          {" "}
          — belge {belgeAdi} kaynak cümlesini göster
        </span>
      </button>

      {acik && (
        <div
          className="kaynak-panel"
          role="dialog"
          aria-label={`Belge ${belgeAdi} kaynak metni`}
          ref={panelRef}
          tabIndex={-1}
        >
          <div className="kaynak-panel-bas">
            <strong>Belge {belgeAdi}</strong>
            <button
              type="button"
              className="btn-ghost"
              onClick={() => {
                setAcik(false);
                dugmeRef.current?.focus();
              }}
            >
              Kapat
            </button>
          </div>

          {belge.loading && <Loading label="Kaynak metin getiriliyor…" />}
          {!!belge.error && <ErrorNotice error={belge.error} />}

          {belge.data && (
            <SourceSpanView
              text={belge.data.text}
              span={span ?? BOS_SPAN}
              rawValue={rawValue}
              blocks={belge.data.bloklar}
            />
          )}

          {belge.data?.source_url && (
            <p className="small">
              <a
                href={belge.data.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                banka sayfası ↗
              </a>
            </p>
          )}
        </div>
      )}
    </>
  );
}
