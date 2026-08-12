"use client";

/**
 * Yıldızlı puan — TÜR İÇİNDE, ve yanında KAPSAMA olmadan asla.
 *
 * İlgili: ./BankaSayfasi.tsx, ../styles/banka.css, ../lib/api.ts (CompositeScore),
 *         src/comparison/compare.py (CompositeScore, MIN_GROUP_SIZE=3,
 *         MIN_COVERAGE=0.5), CLAUDE.md §17 (adil kıyas garantisi)
 *
 * ## Bileşenin tek işi: yıldızı ölçüme bağlamak
 *
 * Yıldız istendi ve yapıldı. Ama beş yıldızlı bir rozet, taşımadığı bir
 * kesinlik izlenimi verir ve bu proje tam olarak o izlenime karşı kurulmuştur.
 * Bileşen bu yüzden üç sert kural ZORLAR — çağıran tarafın iyi niyetine
 * bırakılmaz, çünkü bırakıldığında bir gün unutulur:
 *
 * 1. **Türsüz yıldız basılmaz.** `tur` zorunlu bir alandır. `/advantageous`
 *    bileşik skoru kampanya başına ve KAMPANYA TÜRÜ İÇİNDE üretir;
 *    normalizasyon grup içi rank tabanlıdır, yani farklı türlerden gelen
 *    skorların ortalaması matematiksel olarak tanımsızdır (§17). Türü
 *    yazılmayan bir yıldız, neyin içinde ölçüldüğü bilinmeyen bir yargıdır.
 *
 * 2. **Kapsamasız yıldız basılmaz.** `belge` bilinmiyorsa (`null`) ya da 0 ise
 *    yıldız DÖNDÜRÜLMEZ. Az veri, kötü ürün demek değildir: bir bankanın
 *    kampanyalarını ortalamak, kazıma kapsamasını sessizce kaliteye çevirir —
 *    az belge toplanabilmiş banka, ürünü kötü olduğu için değil verisi az
 *    olduğu için az yıldız alır. Kapsama, yıldızı bir yargıdan bir ölçüme
 *    çeviren tek şeydir; o yüzden aynı satırda ve KALIN basılır.
 *
 * 3. **BOŞ YILDIZ BASILMAZ.** Skor yoksa `☆☆☆☆☆` çizmek "çok kötü" demektir.
 *    Söylenen ise "ölçemedik". İkisi aynı ekranda birbirine benzemesin diye
 *    ölçülemeyen tür yıldız yerine kesikli çerçeveli mono `ölçülemedi`
 *    etiketini alır (bkz. ../styles/banka.css `.tur-olculemedi`).
 *
 * `ComparePanel.tsx` aynı hatayı zaten adıyla anıyor: «kalibre edilmemiş bir
 * skoru kalite iddiası gibi göstermek yanıltıcıdır.»
 *
 * ## Erişilebilirlik
 *
 * Yıldız dizisi tek bir `aria-hidden` düğümdür; ekran okuyucu onu hiç görmez.
 * Gerçek değer ÜÇÜNCÜ SÜTUNDAKİ metinde okunur (`3 / 5 · 12 belge.`), yani
 * bilgi renkten ve şekilden bağımsız olarak yazıyla mevcuttur. Bu, "renk tek
 * sinyal değil" kuralının bu bileşendeki karşılığıdır.
 */

import type { ReactNode } from "react";
import type { CompositeScore } from "../lib/api";

/** Yıldız ölçeği. Yarım yıldız YOK — gerekçesi `yildizSayisi()` içinde. */
const AZAMI_YILDIZ = 5;

type Props = {
  skor: CompositeScore;
  /**
   * Kıyasın yapıldığı kampanya türü. ZORUNLU — türsüz yıldız tanımsızdır.
   * Ölçülemeyen türler tek satırda toplandığında birleşik ad taşır
   * («İhtiyaç Fin. · Finansman · …»).
   */
  tur: string;
  /**
   * Bu bankada BU TÜRDE kaç belge toplandı — yıldızın paydası.
   * `null` = henüz bilinmiyor (belge listesi gelmedi). `0` = ölçülemedi.
   * İkisi de yıldızı engeller ama farklı cümle yazdırır: "bilmiyoruz" ile
   * "ölçtük, yok" aynı şey değildir.
   */
  belge: number | null;
  /** Grup içi sıra ve grup büyüklüğü — «tür içinde 2/7» olarak yazılır. */
  sira?: number | null;
  grupBuyuklugu?: number;
  /**
   * Üçüncü sütunun açıklama cümlesi: hangi ölçütler doldu, neden ölçülemedi.
   * Çağıran verir çünkü gerekçe VERİDEN türetilir (skorun bileşenleri, belge
   * sayısı); bileşen onu uyduramaz. Verilmezse bileşen kendi asgari
   * gerekçesini basar.
   */
  gerekce?: ReactNode;
};

/**
 * 0..1 skoru yıldıza çevirir.
 *
 * Yarım yıldız YOK: yarım yıldız, kalibre edilmemiş bir skorda var olmayan bir
 * çözünürlük iddia eder. Tam yıldıza yuvarlanır ve gerçek kesir zaten yanında
 * yazılır — yıldız özet, sayı kaynaktır.
 *
 * Alt sınır 1: sıralamaya GİREBİLMİŞ bir kampanyaya sıfır yıldız vermek, onu
 * ölçülemeyen türle aynı görsele düşürürdü (bkz. kural 3).
 */
function yildizSayisi(score: number): number {
  return Math.max(1, Math.min(AZAMI_YILDIZ, Math.round(score * AZAMI_YILDIZ)));
}

export default function YildizPuan({
  skor,
  tur,
  belge,
  sira,
  grupBuyuklugu,
  gerekce,
}: Props) {
  // Üç kapı, tek koşulda: skor yok / kıyas dışı / kapsama yok → YILDIZ YOK.
  // Sırası önemli değil, hepsi aynı sonuca çıkar; önemli olan hiçbirinin
  // atlanamaması.
  const olculdu =
    skor.score !== null && skor.comparable && belge !== null && belge > 0;

  if (!olculdu) {
    return (
      <div className="tur-satir">
        <span className="tur-ad tur-ad-solgun">{tur}</span>
        {/* Yıldız YERİNE etiket. `aria-hidden` DEĞİL: bu metin bilginin
            kendisidir, dekor değil. */}
        <span className="tur-olculemedi">ölçülemedi</span>
        <span className="tur-kapsama">
          {gerekce ?? (
            <>
              {belge === null ? (
                <>Bu türdeki belge sayısı henüz okunmadı.</>
              ) : belge === 0 ? (
                <>Bu türde hiç belge toplanamadı.</>
              ) : (
                <>
                  <b className="tur-kapsama-sayi">{belge} belge.</b>{" "}
                  {skor.note || "yetersiz kapsama — bu türde sıralama yapılmadı"}
                </>
              )}
            </>
          )}
        </span>
      </div>
    );
  }

  const dolu = yildizSayisi(skor.score as number);

  return (
    <div className="tur-satir">
      <span className="tur-ad">{tur}</span>

      {/* Tek düğüm, tek `aria-hidden`: dolu ve boş yıldızlar aynı dizedir,
          böylece ekran okuyucu beş ayrı «yıldız» sözcüğü okumaz. */}
      <span className="tur-yildizlar" aria-hidden="true">
        {"★".repeat(dolu)}
        {"☆".repeat(AZAMI_YILDIZ - dolu)}
      </span>

      <span className="tur-kapsama">
        {/* Yıldızın METİN karşılığı + PAYDASI. Yıldız buradan ayrı basılamaz. */}
        <b className="tur-kapsama-sayi">
          {dolu} / {AZAMI_YILDIZ} · {belge} belge.
        </b>{" "}
        {sira != null && grupBuyuklugu ? (
          <>
            Tür içinde {sira}/{grupBuyuklugu}.{" "}
          </>
        ) : null}
        {gerekce}
      </span>
    </div>
  );
}
