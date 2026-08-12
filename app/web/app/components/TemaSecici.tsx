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
 * Seçili hâl yalnız renkle anlatılmaz — ÜÇ sinyal taşır ve hiçbiri tek başına
 * renk değildir:
 *
 *   1. yüzey  — şerit `--bg-3` dolgusu içinde `--bg-2` pil (iki temada da
 *               lightness farkı, ton farkı değil; `.tema-dugmesi`,
 *               components.css)
 *   2. metin  — düğmenin kendi etiketi zaten yazılı («Sistem» / «Açık» / «Koyu»)
 *   3. ARIA   — `aria-pressed` + `aria-current`
 *
 * `aria-current` v2 tasarımının sekme şeridinden geliyor (aynı disiplin, aynı
 * nitelik): «bu, kümedeki GEÇERLİ olan». `aria-pressed` düğmenin BASILI
 * olduğunu söyler, `aria-current` seçimin kümedeki tekliğini söyler; ikisi
 * aynı bilgiyi iki farklı sözcükle taşır ve yardımcı teknolojiler hangisini
 * okuyorsa okur.
 *
 * ## Hidrasyon — bozulmaması gereken şey
 *
 * `hazir` gelmeden hiçbir düğme seçili GÖSTERİLMEZ. Sunucu render'ı seçimi
 * bilemez; ilk karede «Sistem»i seçili basmak, koyu temayı seçmiş kullanıcıya
 * bir an yanlış bilgi vermek olurdu.
 *
 * Bunun ikinci ve daha sert sonucu şudur: sunucu çıktısı HER HÂLDE aynıdır.
 * `hazir` sunucuda her zaman `false` (bkz. `lib/tema.tsx` — depo `useEffect`
 * içinde okunur), yani `secili` her düğmede `false`, `on` sınıfı hiç basılmaz
 * ve hiçbir nitelik kullanıcının seçimine göre değişmez. Bu dosyaya seçime
 * bağlı YENİ bir nitelik eklenirken de aynı kapı geçerli: nitelik `secili`
 * üzerinden türetilmeli, doğrudan `tema` üzerinden değil. `data-tema`
 * niteliğini bu bileşen hiç basmaz — onu yalnız `lib/tema.tsx` `uygula()`
 * mount sonrası belgeye yazar ve «sistem» hâlinde hiç yazmaz.
 */

import { TEMALAR, useTema } from "../lib/tema";

export default function TemaSecici() {
  const { tema, setTema, hazir } = useTema();

  return (
    <div className="tema-secici" role="group" aria-label="Panel görünümü">
      <span className="tema-etiket small muted">Görünüm</span>
      {TEMALAR.map((t) => {
        // `hazir` KAPISI: sunucuda her zaman false → sunucu çıktısı sabit.
        const secili = hazir && tema === t.deger;
        return (
          <button
            key={t.deger}
            type="button"
            className={`chip tema-dugmesi${secili ? " on" : ""}`}
            aria-pressed={secili}
            // Seçili olmayan düğmede nitelik hiç BASILMAZ: `aria-current="false"`
            // geçerli bir değer ama «bu geçerli değil» diye ayrıca konuşur ve
            // üç düğmeden ikisi boşuna okunur.
            aria-current={secili ? "true" : undefined}
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
