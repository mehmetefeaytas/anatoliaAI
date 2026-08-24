"use client";

import type { ReactNode } from "react";

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
 * 3. **Farklı kampanya türleri kıyaslanmaz** (2026-08-09'da eklendi). Bu madde
 *    bir ŞİKÂYETTEN doğdu: `vade_ay` ekranında 120 aylık bir konut finansmanı
 *    ile 36 aylık bir ihtiyaç finansmanı yan yana sıralanıyordu. Kural §17'de
 *    zaten vardı ama yalnız BİRİM düzeyinde uygulanmıştı; kampanya türü
 *    düzeyinde uygulanmıyordu. Artık tablo türe göre bölümleniyor ve sıra
 *    numaraları bölüm içinde veriliyor.
 *
 * ## Kavramın TEK ADI burada tanımlanır (2026-08-09)
 *
 * Aynı kavram — `campaign_type` alanı, §12'deki 8 sınıf — arayüzde iki ayrı
 * adla dolaşıyordu: kimi yerde «ürün ailesi», kimi yerde «kampanya türü».
 * Kullanıcı bunları iki FARKLI süzgeç sandığını bildirdi ve haklıydı: kıyas
 * ekranında açılır süzgeç «Kampanya türü» derken hemen altındaki tablo notu
 * «ürün ailesi içinde sıralanır» diyordu. Tek ad seçildi: **kampanya türü**
 * (§12'nin resmî sınıf adı; «ürün ailesi» iç jargondu). Bu blok, kavramın NE
 * OLDUĞUNU kullanıcıya bir kez açıkça yazan tek yerdir — 8 sınıf sayılır ve
 * «neden yalnız tür içinde sıralanır» gerekçesi verilir.
 *
 * ## İki varyant — neden katlandı (2026-08-11)
 *
 * ÖLÇÜLDÜ: varsayılan ekranda ilk veri satırından ÖNCE ~400 kelime basılıyordu
 * ve bunun en büyük tek parçası bu bileşendi — dört yoğun blok, ~250 kelime,
 * 1120px kabuğun tamamını kullandığı için satır başına ~150 karakter. İlk
 * ekranın kabaca %60'ını kaplıyor, kıyas tablosunu katlamanın altına itiyordu.
 * Üstelik bileşen ÜÇ yüzeyde birden basılıyordu (kıyas paneli, banka içi delta,
 * en avantajlı) — yani kullanıcı aynı 250 kelimeyi sekme değiştirdikçe yeniden
 * görüyordu.
 *
 * Çözüm metni KISALTMAK değil KATLAMAK: `varyant="serit"` tek satırlık bir özet
 * basar, kuralların tamamı aynı yerde açılır (`<details>`), gezinme yok. Bu
 * kademeli açığa çıkarma (progressive disclosure) kuralı ekranda DAHA
 * güvenilir tutar: kimsenin okumadığı bir duvar, okunan bir satırdan az bilgi
 * taşır.
 *
 * Kapatılabilir DEĞİLDİR (dismiss düğmesi yoktur) — bu kural sürüyor. Katlama
 * kapatma DEĞİLDİR: `<summary>` satırı her hâlde ekranda kalır, `[open]`
 * durumundan bağımsız olarak. Jüri ekranı ilk açtığında görüp «×» ile
 * kapatabildiği bir uyarı, demonun geri kalanında yok sayılırdı; katlanmış bir
 * kural ise tek tıkla geri gelir ve özeti hiç kaybolmaz.
 */

type Varyant = "tam" | "serit";

type Props = {
  /**
   * `"tam"` — dört blok açıkta (varsayılan; kavramın tanımının yaşadığı hâl).
   * `"serit"` — tek satır özet + yerinde açılan tam metin. Kıyas tablosu basan
   * her yüzeyde bu kullanılır.
   */
  varyant?: Varyant;
  /**
   * Yüzeye ÖZEL ek kural (ör. `/advantageous` ucunun `fairness_note` alanı).
   * Genel kuralların yanına, açıldığında görünen bloğun sonuna eklenir.
   * Sunucudan gelen bu metin eskiden panelin kendi kutusunda ayrıca
   * basılıyordu; aynı kuralın iki ayrı kutuda görünmesi ekranın üstünü
   * şişiren tekrarın ta kendisiydi.
   */
  ek?: ReactNode;
};

export default function FairnessNotice({ varyant = "tam", ek }: Props) {
  const bloklar = <TamBloklar ek={ek} />;

  if (varyant === "tam") return bloklar;

  return (
    <details className="fairness-serit">
      <summary className="fairness-ozet">
        <span>
          <b>Adil kıyas:</b> Yalnız aynı birime normalize edilmiş,{" "}
          <b>aynı kampanya türü</b> içindeki değerler kıyaslanır ·{" "}
          <span className="mono">0</span> bir ceza değil, üründür · süresi
          dolmuş kampanya sıralamaya girmez
        </span>
        <span className="fairness-ac">kuralların tamamı</span>
      </summary>
      {bloklar}
    </details>
  );
}

/** Kuralların tam metni. İki varyant da AYNI bloğu basar; ayrım yalnız
 *  görünürlüktedir — «serit»te katlanmış, «tam»da açık. */
function TamBloklar({ ek }: { ek?: ReactNode }) {
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
          gerekçesiyle listede kalır. Silinmez, uydurma sıra da verilmez.
        </p>
      </div>
      <div className="fairness-item">
        <strong>Kampanya türü nedir, neden yalnız tür içinde sıralanır?</strong>
        <p>
          <b>Kampanya türü</b>, bir belgenin ait olduğu ürün sınıfıdır ve sekiz
          değerden birini alır:{" "}
          <span className="tur-listesi">
            Finansman · İhtiyaç Finansmanı · Konut Finansmanı · Taşıt Finansmanı ·
            Kart · Alışveriş Puanı · Yeni Müşteri · Yatırım Ürünü
          </span>
          . Farklı türler <b>birbirinin alternatifi değildir</b>: bir konut
          finansmanı ile bir ihtiyaç finansmanı arasında «hangisi daha
          avantajlı» sorusu iyi tanımlı değildir. Bu yüzden tablolar{" "}
          <b>kampanya türüne göre bölümlenir</b> ve sıra numaraları yalnız tür
          içinde verilir. Türler arası hiçbir sıralama üretilmez — 120 aylık bir
          konut finansmanının 36 aylık bir ihtiyaç finansmanını «yenmesi» bir
          bilgi değil, bir ölçüm hatasıdır.
        </p>
      </div>
      <div className="fairness-item">
        <strong>Tablo neden seyrek? — az ama doğru</strong>
        <p>
          Bu tablo, metinde geçen her sayıyı göstermez. Üç kapı satırları
          eler ve <b>hiçbiri satırı silmez</b>: elenen değer gerekçesiyle
          birlikte listede kalır.{" "}
          <b>Belge türü</b> — sözleşme, tarife ve bilgi formu metinleri kıyasa
          girmez; bir akitteki oran bir kampanya teklifi değildir.{" "}
          <b>Çıkarım güveni</b> — çerez metninden ya da işlem ücreti
          tarifesinden toplanmış bir sayı{" "}
          <span className="badge badge-warn">doğrudan kıyaslanamaz</span>{" "}
          işaretlenir.{" "}
          <b>Kampanya süresi</b> — sayfası kendi bitişini ilan eden ya da
          arşive düşmüş kampanya{" "}
          <span className="badge badge-expired">süresi dolmuş</span> rozetiyle
          sıralama dışında kalır; bugün başvurulamayan bir teklif, bugünkü
          tekliflerin üstünde görünemez. Sonuç daha az satırdır ve bu bir
          kayıp değildir: <b>kaynağına bağlanabilen az sayıda kayıt, sayısı
          şişirilmiş bir tablodan iyidir.</b>
        </p>
      </div>
      {ek && (
        <div className="fairness-item">
          <strong>Bu ekranın ek kuralı</strong>
          <p>{ek}</p>
        </div>
      )}
    </div>
  );
}
