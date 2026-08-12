"use client";

/**
 * Yıldızlı puan — yalnız KAMPANYA TÜRÜ İÇİNDE, yalnız kapsamasıyla birlikte.
 *
 * İlgili: ../lib/api.ts (CompositeScore), ./AdvantageousPanel.tsx,
 *         src/comparison/compare.py (CompositeScore, MIN_GROUP_SIZE),
 *         CLAUDE.md §17 (adil kıyas garantisi)
 *
 * ## Neden bu bileşen bu kadar çok şeyi reddediyor
 *
 * Yıldız istendi ve yapıldı. Ama beş yıldızlı bir rozet, taşımadığı bir
 * kesinlik izlenimi verir ve bu proje tam olarak o izlenime karşı kurulmuştur.
 * Üç somut sınır ölçüldü ve koda gömüldü:
 *
 * 1. **Banka başına puan YOKTUR ve hesaplanamaz.** `/advantageous` bileşik
 *    skoru kampanya başına ve KAMPANYA TÜRÜ İÇİNDE üretir. Normalizasyon grup
 *    içi rank tabanlıdır, yani farklı türlerden gelen skorların ortalaması
 *    matematiksel olarak anlamsızdır — ayrıca türler arası kıyas §17'nin
 *    açıkça yasakladığı şeydir. Bu yüzden bileşen `tur` parametresini ZORUNLU
 *    alır ve türü ekranda yazar: türsüz bir yıldız, tanımsız bir iddiadır.
 *
 * 2. **Az veri, kötü ürün demek değildir.** Bir bankanın tüm kampanyalarını
 *    ortalamak, kazıma kapsamasını kaliteye çevirirdi: az belge toplanabilmiş
 *    bir banka, ürünü kötü olduğu için değil verisi az olduğu için az yıldız
 *    alırdı. Bu yüzden yıldız hiçbir yerde YALNIZ görünmez — yanında her zaman
 *    kapsama etiketi durur.
 *
 * 3. **Kapsama yetmiyorsa yıldız yoktur.** Sunucu zaten `min_group_size` ve
 *    `min_coverage` kapılarını uyguluyor ve `score`u `null` bırakıyor. Bileşen
 *    o hâlde yıldız çizmez; gerekçeyi yazar. Boş beş yıldız «çok kötü» gibi
 *    okunurdu — oysa söylenen şey «ölçemedik».
 *
 * `ComparePanel.tsx` aynı hatayı zaten adıyla anıyor: «kalibre edilmemiş bir
 * skoru kalite iddiası gibi göstermek yanıltıcıdır.»
 *
 * ## Erişilebilirlik
 *
 * Yıldızlar dekoratiftir (`aria-hidden`); asıl bilgi metin olarak da yazılır.
 * Renk tek sinyal değildir: dolu yıldız hem doludur hem sayısı yazılıdır.
 */

import type { CompositeScore } from "../lib/api";

type Props = {
  skor: CompositeScore;
  /** Kıyasın yapıldığı kampanya türü. ZORUNLU — türsüz yıldız tanımsızdır. */
  tur: string;
  /** Bu bankadan bu türde kaç belge toplandı. */
  belge?: number;
  /** Kaç alan çıkarılabildi (12 üzerinden). */
  alan?: number;
  /** Grup içi sıra ve grup büyüklüğü — «2/7» olarak yazılır. */
  sira?: number | null;
  grupBuyuklugu?: number;
};

const AZAMI_YILDIZ = 5;
/** 12 alan — CLAUDE.md §9 veri modeli. */
const ALAN_SAYISI = 12;

/**
 * 0..1 skoru yıldıza çevirir.
 *
 * Yarım yıldız YOK: yarım yıldız, kalibre edilmemiş bir skorda var olmayan bir
 * çözünürlük iddia eder. Tam yıldıza yuvarlanır ve gerçek sayı zaten yanında
 * yüzde olarak yazılır — yıldız özet, sayı kaynaktır.
 */
function yildizSayisi(score: number): number {
  return Math.max(1, Math.round(score * AZAMI_YILDIZ));
}

export default function YildizPuan({
  skor,
  tur,
  belge,
  alan,
  sira,
  grupBuyuklugu,
}: Props) {
  const kapsamaEtiketi =
    belge !== undefined || alan !== undefined
      ? `veri kapsamı: ${belge ?? "?"} belge / ${alan ?? "?"} alan`
      : null;

  // Skor yoksa yıldız da yok. Boş yıldız «kötü» diye okunur; söylenen «ölçemedik».
  if (skor.score === null || !skor.comparable) {
    return (
      <div className="yildiz-satir">
        <span className="yildiz-tur">{tur}</span>
        <span className="yildiz-yok small">
          {skor.note || "yetersiz kapsama — sıralanmadı"}
        </span>
        {kapsamaEtiketi && <span className="yildiz-kapsam small muted">{kapsamaEtiketi}</span>}
      </div>
    );
  }

  const dolu = yildizSayisi(skor.score);
  // Kapsama düşükse yıldızlar soluk: rozet aynı ama iddiası zayıf.
  const zayif = skor.coverage < 0.75;

  return (
    <div className="yildiz-satir">
      <span className="yildiz-tur">{tur}</span>

      <span
        className={zayif ? "yildizlar yildizlar-zayif" : "yildizlar"}
        aria-hidden="true"
      >
        {Array.from({ length: AZAMI_YILDIZ }, (_, i) => (
          <span key={i} className={i < dolu ? "yildiz yildiz-dolu" : "yildiz"}>
            ★
          </span>
        ))}
      </span>

      {/* Yıldızın metin karşılığı — ekran okuyucu ve renk körlüğü için. */}
      <span className="yildiz-deger small mono">
        {dolu}/{AZAMI_YILDIZ}
        {sira != null && grupBuyuklugu
          ? ` · tür içinde ${sira}/${grupBuyuklugu}`
          : ""}
      </span>

      {kapsamaEtiketi && (
        <span className="yildiz-kapsam small muted">
          {kapsamaEtiketi}
          {alan !== undefined && alan < ALAN_SAYISI ? ` (${ALAN_SAYISI} alandan)` : ""}
          {zayif ? " · düşük kapsama" : ""}
        </span>
      )}
    </div>
  );
}
