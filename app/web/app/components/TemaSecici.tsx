"use client";

/**
 * Tema seçici — sistem / açık / koyu.
 *
 * İlgili: ../lib/tema.tsx, ../styles/tema.css
 *
 * Üç düğme tek bir grup: seçenekler AYNI ANDA görünür, çünkü dönüşümlü tek
 * düğme («tıkla, sıradakine geç») kullanıcıya kaç hâl olduğunu ve şu an
 * hangisinde bulunduğunu ancak deneyerek öğretirdi.
 *
 * Seçili hâl yalnız renkle anlatılmaz: `aria-pressed` aynı bilgiyi ekran
 * okuyucuya taşır ve grup `aria-label` ile adlandırılır.
 *
 * `hazir` gelmeden hiçbir düğme seçili GÖSTERİLMEZ. Sunucu render'ı seçimi
 * bilemez; ilk karede «Sistem»i seçili basmak, koyu temayı seçmiş kullanıcıya
 * bir an yanlış bilgi vermek olurdu.
 */

import { TEMALAR, useTema } from "../lib/tema";

export default function TemaSecici() {
  const { tema, setTema, hazir } = useTema();

  return (
    <div className="tema-secici" role="group" aria-label="Panel görünümü">
      <span className="tema-etiket small muted">Görünüm</span>
      {TEMALAR.map((t) => {
        const secili = hazir && tema === t.deger;
        return (
          <button
            key={t.deger}
            type="button"
            className={`chip tema-dugmesi${secili ? " on" : ""}`}
            aria-pressed={secili}
            onClick={() => setTema(t.deger)}
            title={t.ipucu}
          >
            {t.etiket}
          </button>
        );
      })}
    </div>
  );
}
