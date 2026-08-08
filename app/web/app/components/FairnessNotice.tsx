"use client";

/**
 * Adil kıyas şeridi — kıyas tablosunun ve delta ekranının KALICI notu.
 *
 * İlgili: CLAUDE.md §17 (adil kıyas garantisi), §12 (faizsiz finans terminolojisi),
 *         src/comparison/compare.py `_numeric_key` / `_LOWER_IS_BETTER`
 *
 * İki alan hatası burada önleniyor:
 *
 * 1. **«0» bir ceza değildir.** Katılım bankacılığında `kar_payi_orani = 0`
 *    "kâr payı alınmıyor" demektir — eksik veri değil, ürünün kendisi. Sıfırı
 *    "en kötü" gibi göstermek ya da boş hücreyle karıştırmak, faizsiz finansın
 *    en ayırt edici ürününü sıralamanın dibine iter.
 * 2. **Koşulu farklı olan kıyaslanmaz.** Aralık (`%1,99–%2,49`) ya da
 *    zaman-koşullu oran («ilk 6 ay %0») aynı birime indirgenemez; sistem
 *    bunları sıralamaya SOKMAZ, «doğrudan kıyaslanamaz» işaretiyle listede
 *    bırakır. Uydurma sıralama yapılmaz.
 * 3. **Farklı ürün aileleri kıyaslanmaz** (2026-08-09'da eklendi). Bu madde
 *    bir ŞİKÂYETTEN doğdu: `vade_ay` ekranında 120 aylık bir konut finansmanı
 *    ile 36 aylık bir ihtiyaç finansmanı yan yana sıralanıyordu. Kural §17'de
 *    zaten vardı ama yalnız BİRİM düzeyinde uygulanmıştı; ürün ailesi
 *    düzeyinde uygulanmıyordu. Artık tablo aileye göre bölümleniyor ve sıra
 *    numaraları bölüm içinde veriliyor.
 *
 * Kapatılabilir DEĞİLDİR (dismiss düğmesi yoktur): jüri ekranı ilk açtığında
 * görüp kapattıysa, demonun geri kalanında bu bilgi ekranda kalmalıdır.
 */

export default function FairnessNotice() {
  return (
    <div className="fairness" role="note" aria-label="Adil kıyas kuralları">
      <div className="fairness-item">
        <strong>0 = ürün yok, ceza değil</strong>
        <p>
          Bir hücrede <span className="mono">%0</span> ya da{" "}
          <span className="mono">masrafsız</span> yazıyorsa bu <b>eksik bilgi
          değildir</b>: katılım bankacılığında kâr payı ya da masraf
          alınmayan gerçek bir üründür. Sıralamada 0, o alanın en avantajlı
          ucudur; hiçbir yerde ceza olarak işlenmez. Bilgi gerçekten yoksa hücre{" "}
          <span className="mono">—</span> gösterir ve satır{" "}
          <span className="badge badge-warn">kıyaslanamaz</span> işaretlenir —
          ikisi karıştırılmamalıdır.
        </p>
      </div>
      <div className="fairness-item">
        <strong>Adil kıyas garantisi</strong>
        <p>
          Yalnızca <b>aynı birime normalize edilmiş</b> değerler kıyaslanır.
          Koşulları farklı olanlar — aralık (<span className="mono">%1,99–%2,49</span>),
          zaman-koşullu oran («ilk 6 ay %0»), farklı para birimi — sıralamaya
          alınmaz; <span className="badge badge-warn">doğrudan kıyaslanamaz</span>{" "}
          gerekçesiyle listede kalır. Silinmez, uydurma sıra da verilmez
          (CLAUDE.md §17).
        </p>
      </div>
      <div className="fairness-item">
        <strong>Farklı ürünler yan yana sıralanmaz</strong>
        <p>
          Bir <b>konut finansmanı</b> ile bir <b>ihtiyaç finansmanı</b>{" "}
          birbirinin alternatifi değildir; «hangisi daha avantajlı» sorusu bu
          ikisi arasında iyi tanımlı değildir. Tablo <b>ürün ailesine göre
          bölümlenir</b> ve sıra numaraları yalnız bölüm içinde verilir.
          Aileler arası hiçbir sıralama üretilmez — 120 aylık bir konut
          finansmanının 36 aylık bir ihtiyaç finansmanını «yenmesi» bir bilgi
          değil, bir ölçüm hatasıdır.
        </p>
      </div>
    </div>
  );
}
