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
 * ## Kırılım: «bu yıldız nasıl hesaplandı»
 *
 * Yıldız bir ÖZETTİR ve özet, taşımadığı bir kesinlik izlenimi verebilir:
 * ölçüldü (13 Ağustos, Kuveyt Türk · Alışveriş Puanı, `campaign_id` 317) →
 * `score` 1,00 ile BEŞ yıldız, ama o beş yıldız ağırlık tablosunun tek bir
 * %20'lik kaleminden geliyor; tablonun %65'i o türde hiç ölçülememiş.
 * Katlanmış `<details>` bu üç paydayı açar (hesabın kendisi ./../lib/kirilim.ts
 * içinde, saf ve test edilmiş).
 *
 * Kırılım YILDIZA BAĞLIDIR: ölçülemeyen satırda hiç çizilmez (bkz. kural 3 —
 * açılacak bir hesap yoktur) ve varsayılan KAPALI gelir; sayfada dokuz tür
 * satırı var, hepsi açık gelirse ekran bir hesap tablosuna döner.
 *
 * ## Erişilebilirlik
 *
 * Yıldız dizisi tek bir `aria-hidden` düğümdür; ekran okuyucu onu hiç görmez.
 * Gerçek değer ÜÇÜNCÜ SÜTUNDAKİ metinde okunur (`3 / 5 · 12 belge.`), yani
 * bilgi renkten ve şekilden bağımsız olarak yazıyla mevcuttur. Bu, "renk tek
 * sinyal değil" kuralının bu bileşendeki karşılığıdır. Aynı kural kırılımda da
 * geçerli: boş kalan ölçüt satırı yalnız solgunlaşmaz, hücresinde
 * «ölçülemedi» YAZAR. Kırılım gerçek bir `<table>`dır — başlıklı sütunlar ve
 * satır başlıklarıyla; div ızgarası, ekran okuyucuda sayıları başlıksız
 * bırakırdı.
 */

import type { ReactNode } from "react";
import type { CompositeScore, WeightRow } from "../lib/api";
import { formatValue, sayiIyelik, trNum } from "../lib/format";
import {
  kirilimCizilir,
  kirilimOzetSayilari,
  kirilimOzeti,
} from "../lib/kirilim";

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
  /**
   * `/advantageous.weights` — ağırlık TABLOSUNUN tamamı.
   *
   * Bileşen listesi bu tablonun yalnız o türde AKTİF olan alt kümesidir
   * (compare.py:935); tablonun ne kadarının hiç ölçülemediği ancak küme farkıyla
   * görülür. Gelmemişse (yükleme/hata) kırılım o satırı BASMAZ: ölçemediğimiz
   * bir yokluğu yokluk gibi göstermeyiz.
   */
  agirliklar?: WeightRow[] | null;
  /**
   * Alan adı → Türkçe etiket (`/fields`). Hiçbir alan adı bu dosyada sabit
   * yazılmaz; verilmezse ham ad basılır (kod okutmak, yanlış etiket
   * uydurmaktan iyidir).
   */
  etiket?: (field: string) => string;
};

/** 0..1 oranı yüzdeye çevirir (AdvantageousPanel `yuzde()` ile aynı idiom). */
function yuzde(v: number | null): string {
  return v === null || Number.isNaN(v) ? "—" : `%${trNum(Math.round(v * 100))}`;
}

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
  agirliklar,
  etiket = (field) => field,
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

  // Kırılım kapısı yıldız kapısıyla AYNI yerden gelir (../lib/kirilim.ts).
  // Buraya gelindiğinde koşullar zaten sağlanmış durumda; çağrı yine de
  // yapılıyor ki «kırılım yıldıza bağlıdır» kuralı tek bir test edilebilir
  // fonksiyonda dursun ve bileşen listesi boş bir satır hesap açmasın.
  const ozet = kirilimCizilir(skor, belge)
    ? kirilimOzeti(skor, agirliklar)
    : null;

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

      {/* Kırılım satırın DÖRDÜNCÜ ızgara çocuğudur ve tüm sütunları kaplar
          (banka.css `.tur-kirilim`). Sarmalayıcı bir div eklenmiyor: cetvelin
          alt çizgi kuralı (`.tur-cetveli .tur-satir:last-child`) satırın
          cetvelin doğrudan çocuğu olmasına dayanıyor. */}
      {ozet && (
        <details className="tur-kirilim">
          <summary className="tur-kirilim-ozet">
            {/* Katlanmış hâlde de BİLGİ taşır: İKİ sayı birden — ağırlık
                tablosundaki ölçüt sayısı ve bu kampanyada ölçülen sayı (bkz.
                kirilimOzetSayilari). Tablo gelmediyse payda aktif ölçüt
                sayısına düşer ve cümle bunu SÖYLER; sessizce daha küçük bir
                paydaya geçmek kırılımı olduğundan geniş gösterirdi. */}
            {(() => {
              const { payda, pay, tabloyaDayali } = kirilimOzetSayilari(ozet);
              return tabloyaDayali
                ? `${payda} ölçütün ${sayiIyelik(pay)} bu kampanyada ölçüldü`
                : `${payda} aktif ölçütün ${sayiIyelik(pay)} bu kampanyada ölçüldü`;
            })()}{" "}
            — hesabı aç
          </summary>

          <div className="tur-kirilim-govde">
            <table className="tur-kirilim-tablo">
              <caption className="tur-kirilim-baslik">
                Bu yıldız nasıl hesaplandı
              </caption>
              <thead>
                <tr>
                  <th scope="col">ölçüt</th>
                  <th scope="col">ham değer</th>
                  <th scope="col">normalize (tür içi sıra)</th>
                  <th scope="col">ağırlık</th>
                  <th scope="col">katkı</th>
                  <th scope="col">not</th>
                </tr>
              </thead>
              <tbody>
                {/* Liste SUNUCUDA ağırlığa göre sıralı geldi
                    (compare.py:996); burada yeniden sıralanmaz. */}
                {skor.components.map((c) => {
                  const bos = c.normalized === null || c.normalized === undefined;
                  return (
                    <tr
                      key={c.field_name}
                      className={bos ? "tur-kirilim-bos" : undefined}
                    >
                      <th scope="row">{etiket(c.field_name)}</th>
                      <td>{formatValue(c.value, c.field_name)}</td>
                      <td className="tur-kirilim-sayi">
                        {bos ? (
                          // Renk TEK sinyal olamaz: boşluk YAZIYLA da durur.
                          <span className="tur-kirilim-yok">ölçülemedi</span>
                        ) : (
                          trNum(c.normalized as number)
                        )}
                      </td>
                      <td className="tur-kirilim-sayi">{trNum(c.weight)}</td>
                      <td className="tur-kirilim-sayi">
                        {bos ? "—" : trNum(c.contribution ?? 0)}
                      </td>
                      <td>{c.note ?? ""}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* ÜÇ PAYDA — üçü de veriden türetilir, hiçbiri sabit değil. */}
            <ul className="tur-kirilim-paydalar">
              {/* 1) Ağırlık tablosu gelmemişse bu satır HİÇ basılmaz:
                     ölçemediğimiz bir yokluğu iddia etmeyiz. */}
              {ozet.olculemeyen !== null && ozet.tabloToplam !== null && (
                <li className="tur-kirilim-payda">
                  <span className="tur-kirilim-payda-etiket">
                    türde hiç ölçülemeyen ölçütler
                  </span>
                  {ozet.olculemeyen.length === 0 ? (
                    <>
                      Ağırlık tablosundaki {ozet.tabloToplam} ölçütün tamamı bu
                      türde aktif; ağırlığın hiçbiri baştan devre dışı kalmadı.
                    </>
                  ) : (
                    <>
                      {ozet.tabloToplam} ölçütten{" "}
                      {sayiIyelik(ozet.olculemeyen.length)} — ağırlığın{" "}
                      <b>{yuzde(ozet.olculemeyenPay)}</b>
                      {"'i "}
                      baştan devre dışı:{" "}
                      {ozet.olculemeyen
                        .map((o) => etiket(o.field_name))
                        .join(" · ")}
                      . Bu türde hiçbir kampanya bu ölçütlerde değer taşımıyor,
                      o yüzden tabloya hiç girmiyorlar.
                    </>
                  )}
                </li>
              )}

              {/* 2) Aktif ama BU kampanyada boş kalan ölçütler → kapsama. */}
              <li className="tur-kirilim-payda">
                <span className="tur-kirilim-payda-etiket">
                  bu kampanyada boş kalan aktif ölçüt
                </span>
                {ozet.bosKalan.length === 0 ? (
                  <>
                    Aktif {ozet.aktif} ölçütün tamamı bu kampanyada ölçüldü →
                    kapsama <b>{yuzde(ozet.kapsama)}</b>.
                  </>
                ) : (
                  <>
                    {ozet.bosKalan
                      .map(
                        (c) => `${etiket(c.field_name)} (${trNum(c.weight)})`,
                      )
                      .join(" · ")}{" "}
                    → kapsama <b>{yuzde(ozet.kapsama)}</b>. Boş ölçüt skoru
                    düşürmez, PAYDAYI daraltır.
                  </>
                )}
              </li>

              {/* 3) Skorun paydası: yalnız kapsanan ağırlık. */}
              <li className="tur-kirilim-payda">
                <span className="tur-kirilim-payda-etiket">skor</span>
                Yalnız kapsanan ağırlık üzerinden ortalanır:{" "}
                {trNum(ozet.katkiToplami)} / {trNum(ozet.kapsananAgirlik)} ={" "}
                <b>
                  {ozet.skor === null ? "—" : trNum(ozet.skor)} → {dolu} /{" "}
                  {AZAMI_YILDIZ} yıldız
                </b>
                . Ölçülemeyen ölçüt bu bölmenin hiçbir yerinde geçmez; yıldız
                bu yüzden kapsamadan AYRI okunamaz.
              </li>
            </ul>
          </div>
        </details>
      )}
    </div>
  );
}
