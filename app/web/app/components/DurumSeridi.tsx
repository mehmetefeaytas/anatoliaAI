"use client";

/**
 * Durum şeridi — API, depo, yerel model ve korpus tek satırda.
 *
 * İlgili: ../lib/saglik.tsx, ../lib/api.ts (`Stats`), ../styles/durum.css
 *         ../components/ErrorNotice.tsx (bandın altındaki tek satır atıf)
 *
 * ## Neden kalıcı kabukta
 *
 * Bu dört bilgi bugüne kadar ancak bir şey BOZULUNCA öğreniliyordu: API'nin
 * kapalı olduğu bir panel çökünce, yerel modelin kapalı olduğu bir düğme
 * devre dışı kalınca, hangi veritabanına bakıldığı ise hiç.
 *
 * Üçü de sunumda söylenmesi gereken şeyler ve ikisi doğrudan puanlanan
 * ölçütlere bakıyor: «SQLite» ve «yerel model» satırı on-prem iddiasının
 * görsel kanıtı, korpus sayıları ise kapsamın.
 *
 * ## «LLM kapalı» bir kusur değil, bir güç
 *
 * Yerel model kapalıyken sistem cevap vermeye DEVAM ediyor — yalnız
 * sözelleştirme ve özet üretimi durur, kural katmanı çalışır. Şerit bunu
 * kusur gibi değil, durum gibi yazıyor; sunumda söylenecek cümle de bu:
 * «kapalıyken de cevap veriyor, uydurmuyor».
 *
 * ## Renk TEK sinyal değil — üç kat tekrar
 *
 * Her çip durumu üç yolla söyler: bir NOKTA (biçim), bir CÜMLE (metin) ve bir
 * mono İŞARET (`✓` / `—`). Renk yalnız dördüncü tekrardır. Nokta ve işaret
 * `aria-hidden`: durum çipte yazılı olduğu için ekran okuyucuya iki kez
 * düşmesi bilgi değil gürültü olurdu.
 *
 * Şerit MONO ve `--fs-xs`: bu satır verinin kendisi değil, verinin DURUMU.
 * Sağlıklı hâlde sakin (`--fg-dim`), bozukken `--warn` — ve hiçbir hâlde
 * kırmızı kutu yığınına dönüşmez.
 */

import { useEffect, useRef } from "react";
import { api } from "../lib/api";
import { useSaglik } from "../lib/saglik";
import { trNum } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const DEPO_ADI: Record<string, string> = {
  sqlite: "SQLite",
  postgres: "PostgreSQL",
};

/** `✓` = açık/okundu, `—` = yok/okunamadı. Renkten bağımsız ikinci sinyal. */
const VAR = "✓";
const YOK = "—";

export default function DurumSeridi() {
  const { saglik, kapali, hazir } = useSaglik();
  const stats = useAsync(() => api.stats(), []);

  // İlk kare: sunucu ve istemci aynı şeyi basmalı (hidrasyon). Yoklama
  // bitmeden hiçbir iddia yazılmıyor.
  if (!hazir) return null;

  const korpus = stats.data?.korpus;

  return (
    <div className="durum-serit" role="status">
      <span className={kapali ? "durum-cip durum-kapali" : "durum-cip"}>
        <span className="durum-nokta" aria-hidden="true" />
        {kapali ? "api yanıt vermiyor" : "api açık"}
        <span className="durum-isaret" aria-hidden="true">
          {kapali ? YOK : VAR}
        </span>
      </span>

      {/* Depo ve model YALNIZ API ayaktayken yazılır: ikisi de o uçtan
          okunuyor ve sunucu düşmüşken «✓» basmak, ölçülmemiş bir şeyi
          ölçülmüş göstermek olurdu. Son okunan durum bandın mono
          listesinde, açıkça «son okuma» olarak duruyor. */}
      {!kapali && saglik && (
        <>
          <span className="durum-cip">
            depo {DEPO_ADI[saglik.backend] ?? saglik.backend}
            <span className="durum-isaret" aria-hidden="true">
              {VAR}
            </span>
          </span>
          <span className="durum-cip">
            yerel model {saglik.llm ? "açık" : "kapalı"}
            <span className="durum-isaret" aria-hidden="true">
              {saglik.llm ? VAR : YOK}
            </span>
          </span>
        </>
      )}

      {korpus && (
        // `korpus.banks` BANKA değil KAYNAK sayar: içinde `tkbb` var, yani
        // bankaların birliği. Şerit «11 banka» yazarken kabuk künyesi «10 banka»
        // yazıyordu ve ikisi aynı ekranda görünüyordu. Gerekçenin tamamı
        // ../page.tsx `KorpusKunyesi` başlığında.
        <span className="durum-cip durum-korpus">
          {trNum(korpus.campaigns)} belge · {trNum(korpus.banks)} kaynak
        </span>
      )}
    </div>
  );
}

/** `2026-08-10 04:12` — mono, yerel saat, saniye yok. */
function saatDamgasi(ms: number): string {
  const d = new Date(ms);
  const iki = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getFullYear()}-${iki(d.getMonth() + 1)}-${iki(d.getDate())} ` +
    `${iki(d.getHours())}:${iki(d.getMinutes())}`
  );
}

/**
 * API kapalıyken kabukta duran TEK SAKİN BANT.
 *
 * Paneller kendi hata kutularını bastırmıyor (bu, her panele dokunmayı
 * gerektirirdi); bunun yerine bant onların ÜSTÜNDE duruyor ve olayı bir kez
 * açıklıyor. `ErrorNotice` da aynı anda susuyor ve kendini bu banda bağlıyor:
 * beş panel, beş kırmızı kutu değil, bir bant.
 *
 * ## Neden `--warn`, neden `--bad` değil
 *
 * Bu bir çökme değil, dereceli bir bozulmadır: yeni sorgu çalışmıyor ama
 * panel son okunan veriyi göstermeye, kaynak metinler ve dipnotlar açılmaya
 * devam ediyor. Kırmızı paniktir, turuncu durumdur.
 *
 * ## Okuma zamanı UYDURULMUYOR
 *
 * Damga, sağlık yoklamasının en son BAŞARILI olduğu andan gelir ve `ref`te
 * tutulur — durum olarak tutulsaydı ayakta olan bir sistemde 15 saniyede bir
 * gereksiz render tetiklerdi. Hiç başarılı okuma olmadıysa (panel kapalı bir
 * sunucuya açıldıysa) tarih cümlesi hiç kurulmaz: olmayan bir okumaya saat
 * yazmak, tam olarak bu panelin yapmamaya söz verdiği şeydir.
 *
 * `role="status"` + `aria-live="polite"`: jüri ekranında sesli okuyucuya da
 * düşsün, ama okumayı kesmeden.
 */
export function ApiKapaliUyarisi() {
  const { saglik, kapali, hazir } = useSaglik();
  const sonOkuma = useRef<number | null>(null);

  useEffect(() => {
    // `saglik` her başarılı yoklamada yeni bir nesnedir; etki o yüzden her
    // turda yeniden koşar ve damga tazelenir.
    if (hazir && !kapali) sonOkuma.current = Date.now();
  }, [hazir, kapali, saglik]);

  if (!hazir || !kapali) return null;

  const okundu = sonOkuma.current;

  // Mono durum listesi — üçüncü sinyal. `api` işaretsiz değil, açıkça `—`.
  const parcalar = [`api ${YOK}`];
  if (saglik) {
    parcalar.push(
      `depo ${DEPO_ADI[saglik.backend] ?? saglik.backend} ${VAR}`,
      `yerel model ${saglik.llm ? VAR : YOK}`,
    );
  }

  return (
    <div className="durum-bant" role="status" aria-live="polite">
      <span className="durum-bant-nokta" aria-hidden="true" />

      <div className="durum-bant-govde">
        <div className="durum-bant-baslik">
          API yanıt vermiyor — panel son okunan veriyi gösteriyor
        </div>
        <div className="durum-bant-aciklama">
          {okundu === null ? (
            <>
              Panel bu oturumda sunucudan hiç veri okuyamadı; bu yüzden bir
              okuma zamanı yazılmıyor. Bağlantı kurulduğunda ekran kendiliğinden
              dolar.
            </>
          ) : (
            <>
              Ekrandaki sayılar son başarılı okumadan geliyor (
              <span className="durum-bant-saat">{saatDamgasi(okundu)}</span>).
              Yeni sorgu çalışmıyor; kaynak metinler ve dipnotlar açılmaya devam
              ediyor.
            </>
          )}
        </div>
      </div>

      <span
        className="durum-bant-liste"
        title={
          saglik
            ? "depo ve yerel model durumu son başarılı okumadan geliyor"
            : "sunucudan henüz durum okunmadı"
        }
      >
        {parcalar.join(" · ")}
      </span>
    </div>
  );
}
