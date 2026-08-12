"use client";

/**
 * Durum şeridi — API, depo, yerel model ve korpus tek satırda.
 *
 * İlgili: ../lib/saglik.tsx, ../lib/api.ts (`Stats`), ../styles/durum.css
 *         CLAUDE.md §2 (on-prem), §11 (demo stratejisi)
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
 * ## Renk tek sinyal değil
 *
 * Noktanın rengi durumu tekrar ediyor, TAŞIMIYOR: her çipte durum ayrıca
 * yazılı. Nokta `aria-hidden`.
 */

import { api } from "../lib/api";
import { useSaglik } from "../lib/saglik";
import { trNum } from "../lib/format";
import { useAsync } from "../lib/useAsync";

const DEPO_ADI: Record<string, string> = {
  sqlite: "SQLite",
  postgres: "PostgreSQL",
};

export default function DurumSeridi() {
  const { saglik, kapali, hazir } = useSaglik();
  const stats = useAsync(() => api.stats(), []);

  // İlk kare: sunucu ve istemci aynı şeyi basmalı (hidrasyon). Yoklama
  // bitmeden hiçbir iddia yazılmıyor.
  if (!hazir) return null;

  const korpus = stats.data?.korpus;

  return (
    <div className="durum-serit small" role="status">
      <span className={kapali ? "durum-cip durum-kapali" : "durum-cip"}>
        <span className="durum-nokta" aria-hidden="true" />
        {kapali ? "API'ye ulaşılamıyor" : "API açık"}
      </span>

      {!kapali && saglik && (
        <>
          <span className="durum-cip">
            {DEPO_ADI[saglik.backend] ?? saglik.backend}
          </span>
          <span className="durum-cip">
            {saglik.llm ? "yerel model açık" : "yerel model kapalı"}
          </span>
        </>
      )}

      {korpus && (
        <span className="durum-cip durum-korpus">
          {trNum(korpus.campaigns)} belge · {trNum(korpus.banks)} banka
        </span>
      )}
    </div>
  );
}

/**
 * API kapalıyken kabukta duran TEK bant.
 *
 * Paneller kendi hata kutularını bastırmıyor (bu, her panele dokunmayı
 * gerektirirdi); bunun yerine bant onların ÜSTÜNDE duruyor ve olayı bir kez
 * açıklıyor: beş kırmızı kutu görülse bile hepsinin tek sebebi burada yazılı.
 *
 * Önbellek tarihi uydurulmuyor: korpus tarihi `scraped_at` alanından gelir ve
 * o alan yoksa cümle de kurulmaz.
 */
export function ApiKapaliUyarisi() {
  const { kapali, hazir } = useSaglik();
  if (!hazir || !kapali) return null;

  return (
    <div className="notice notice-warn rail rail-dikkat" role="alert">
      <strong>API&apos;ye ulaşılamıyor</strong>
      <div className="notice-body">
        Aşağıdaki panellerin hepsi aynı sebeple boş — beş ayrı arıza değil, tek
        bir bağlantı sorunu. Sistemin kritik yolu çevrimdışıdır ve veri yereldeki
        korpustan okunur; sunucu yeniden başladığında ekran kendiliğinden dolar.
      </div>
    </div>
  );
}
