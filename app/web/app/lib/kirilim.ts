/**
 * Yıldızın kırılımı — hesabın SAF çekirdeği.
 *
 * İlgili: ../components/YildizPuan.tsx (kırılımı çizen tek yer),
 *         ../components/BankaSayfasi.tsx (`weights`i geçiren yer),
 *         ./api.ts (`CompositeScore`, `ScoreComponent`, `WeightRow`),
 *         src/comparison/compare.py:934-1002 (formülün TEK doğruluk kaynağı),
 *         ../../tests/kirilim.test.ts
 *
 * ## Neden ayrı bir modül
 *
 * Yıldızın altındaki hesap tablosu bir GÖRSEL değil, bir İDDİADIR: «bu beş
 * yıldız şu paydadan geliyor». İddia edilen sayılar sunucunun formülüyle
 * birebir tutmak zorunda; tutmadığı gün ekran, düzeltmeye çalıştığı hatanın
 * daha kötü bir biçimini üretir (yanlış gerekçeli bir kesinlik iddiası).
 * Bu yüzden hesap JSX'ten çıkarıldı: React kurulumu olmadan, elden yazılmış
 * ve CANLI uçtan alınmış kayıtlarla test edilebilsin.
 *
 * ## Üç payda — compare.py'den birebir
 *
 * Sunucuda tek bir "puan" yok, üç ayrı payda var (satır numaraları
 * `src/comparison/compare.py`):
 *
 *  1. **`total_active`** (935-936) — tür grubunda HİÇBİR kampanyanın değer
 *     taşımadığı ölçüt baştan devre dışı kalır ve bileşen listesine hiç
 *     girmez. Yani `skor.components`, ağırlık tablosunun tamamı değil, o
 *     türde AKTİF olan alt kümesidir. Ağırlık tablosunun ne kadarının hiç
 *     ölçülemediği ancak `/advantageous.weights` ile bileşenlerin KÜME FARKI
 *     alınarak görülebilir — bu modülün asıl işi budur.
 *  2. **`coverage = covered_w / total_active`** (979) — bu kampanyanın değer
 *     taşıdığı aktif ağırlık oranı.
 *  3. **`score = total / covered_w`** (980) — skor yalnız KAPSANAN ağırlık
 *     üzerinden ortalanır. Ölçülemeyen ölçüt skoru düşürmez; kapsamayı
 *     düşürür. Beş yıldızın tek bir ölçütten gelebilmesinin sebebi tam olarak
 *     bu satırdır ve kırılımın söylemesi gereken şey de bu.
 *
 * Hiçbir alan adı burada sabit yazılmaz: küme farkı `weights` üzerinden
 * alınır, insan etiketi çağıran tarafın `FieldMeta` sözlüğünden gelir.
 *
 * ## Modül SADECE tip alır
 *
 * Buradaki tek `import` bir `import type`tır ve bu bilinçli: testler bu dosyayı
 * Node'un kendi çözümleyicisiyle (uzantı arama YOK) yüklüyor, bir çalışma-zamanı
 * `import`u eklendiği an ya test kırılır ya da kaynak dosyaya `.ts` uzantılı bir
 * import girer (TS5097). Biçimlendirme ve Türkçe ek işi bu yüzden ÇAĞIRANIN
 * (`YildizPuan`) tarafında kalıyor; burada yalnız sayı üretilir.
 */

import type { CompositeScore, ScoreComponent, WeightRow } from "./api";

/** Ağırlık tablosunda olup bu türde hiç aktif olmayan ölçüt. */
export type OlculemeyenOlcut = {
  field_name: string;
  weight: number;
};

export type KirilimOzeti = {
  /** Bu türde aktif ölçüt sayısı = `skor.components` uzunluğu. */
  aktif: number;
  /** Aktif ağırlıkların toplamı = `total_active` (compare.py:936). */
  aktifAgirlik: number;
  /** Bu kampanyada değer taşıyan (`normalized !== null`) ölçüt sayısı. */
  kapsanan: number;
  /** Kapsanan ağırlıkların toplamı = `covered_w` (compare.py:969). */
  kapsananAgirlik: number;
  /** Katkıların toplamı = `total` (compare.py:970). */
  katkiToplami: number;
  /**
   * `katkiToplami / kapsananAgirlik` — sunucunun `score`u BURADA yeniden
   * türetilir. İki sayı ayrışırsa kırılım yalan söylüyor demektir; test tam
   * olarak bunu kovalar. Kapsanan ağırlık yoksa `null` (0 DEĞİL).
   */
  skor: number | null;
  /** `kapsananAgirlik / aktifAgirlik` = `coverage`. Aktif ağırlık yoksa null. */
  kapsama: number | null;
  /** `normalized === null` olan aktif ölçütler — bu kampanyada boş kalanlar. */
  bosKalan: ScoreComponent[];
  /**
   * Ağırlık tablosunda olup bileşenlerde HİÇ geçmeyen ölçütler.
   * `null` = ağırlık tablosu gelmedi (yükleme/hata). Boş dizi ile `null` AYNI
   * ŞEY DEĞİLDİR: biri «ölçtük, hepsi aktif», diğeri «ölçemedik».
   */
  olculemeyen: OlculemeyenOlcut[] | null;
  /** Ağırlık tablosundaki toplam ölçüt sayısı; tablo gelmediyse `null`. */
  tabloToplam: number | null;
  /** Ölçülemeyen ağırlığın tablodaki toplam ağırlığa oranı; yoksa `null`. */
  olculemeyenPay: number | null;
};

function toplam(sayilar: number[]): number {
  return sayilar.reduce((a, b) => a + b, 0);
}

/** Bileşen bu kampanyada değer taşıyor mu — kapsamanın TEK ölçütü. */
function kapsandi(c: ScoreComponent): boolean {
  return c.normalized !== null && c.normalized !== undefined;
}

/**
 * Kırılım basılacak mı?
 *
 * `YildizPuan`ın «boş yıldız basılmaz» kuralının kırılım karşılığı: ölçülemeyen
 * tür için açılacak bir hesap YOKTUR. Yıldızın basılma koşullarının aynısı
 * (skor var · kıyaslanabilir · kapsama biliniyor ve sıfır değil) artı
 * bileşen listesinin boş olmaması — boş bir tabloyu «hesabı aç» diye sunmak,
 * olmayan bir gerekçeyi varmış gibi göstermek olurdu.
 */
export function kirilimCizilir(
  skor: CompositeScore,
  belge: number | null,
): boolean {
  return (
    skor.score !== null &&
    skor.comparable &&
    belge !== null &&
    belge > 0 &&
    skor.components.length > 0
  );
}

/**
 * Yıldızın arkasındaki üç paydayı VERİDEN türetir.
 *
 * `weights` verilmezse (yükleme/hata) ağırlık tablosuna dayanan alanlar `null`
 * kalır ve çağıran o satırı BASMAZ. Ölçemediğimiz bir yokluğu yokluk gibi
 * göstermek bu ekranın reddettiği hatanın ta kendisi.
 */
export function kirilimOzeti(
  skor: CompositeScore,
  weights?: WeightRow[] | null,
): KirilimOzeti {
  const bilesenler = skor.components;
  const kapsananlar = bilesenler.filter(kapsandi);
  const bosKalan = bilesenler.filter((c) => !kapsandi(c));

  const aktifAgirlik = toplam(bilesenler.map((c) => c.weight));
  const kapsananAgirlik = toplam(kapsananlar.map((c) => c.weight));
  // Katkı yalnız kapsanan bileşenlerden toplanır: compare.py boş bileşene de
  // `contribution = 0.0` yazıyor, ama toplamı `nv is not None` dalında
  // biriktiriyor (967-970). Aynı dalı izlemek, sunucu bir gün boş bileşene
  // başka bir değer yazarsa sessiz sapmayı önler.
  const katkiToplami = toplam(kapsananlar.map((c) => c.contribution ?? 0));

  let olculemeyen: OlculemeyenOlcut[] | null = null;
  let tabloToplam: number | null = null;
  let olculemeyenPay: number | null = null;

  if (weights && weights.length > 0) {
    const aktifAdlar = new Set(bilesenler.map((c) => c.field_name));
    // Sıra tablodan gelir, yeniden üretilmez: ağırlık tablosu bir ürün
    // kararıdır ve kendi sırasıyla okunur.
    olculemeyen = weights
      .filter((w) => !aktifAdlar.has(w.field_name))
      .map((w) => ({ field_name: w.field_name, weight: w.weight }));
    tabloToplam = weights.length;
    const tabloAgirlik = toplam(weights.map((w) => w.weight));
    olculemeyenPay =
      tabloAgirlik > 0
        ? toplam(olculemeyen.map((o) => o.weight)) / tabloAgirlik
        : null;
  }

  return {
    aktif: bilesenler.length,
    aktifAgirlik,
    kapsanan: kapsananlar.length,
    kapsananAgirlik,
    katkiToplami,
    skor: kapsananAgirlik > 0 ? katkiToplami / kapsananAgirlik : null,
    kapsama: aktifAgirlik > 0 ? kapsananAgirlik / aktifAgirlik : null,
    bosKalan,
    olculemeyen,
    tabloToplam,
    olculemeyenPay,
  };
}

/**
 * Katlanmış `<summary>` cümlesinin İKİ SAYISI — kapalı hâlde de bilgi taşır.
 *
 * İki sayı birden verilir çünkü «aktif» ile «kapsanan» ayrı şeylerdir (bkz.
 * dosya başlığındaki üç payda): payda ağırlık TABLOSUNUN ölçüt sayısıdır, pay
 * bu kampanyada değer taşıyan ölçüt sayısı.
 *
 * Tablo gelmediyse payda AKTİF ölçüt sayısına düşer ve `tabloya_dayali` bunu
 * `false` diye bildirir; çağıran cümleyi buna göre kurar. Sessizce daha küçük
 * bir paydaya geçmek, kırılımı olduğundan geniş gösterirdi.
 */
export function kirilimOzetSayilari(ozet: KirilimOzeti): {
  payda: number;
  pay: number;
  tabloyaDayali: boolean;
} {
  return {
    payda: ozet.tabloToplam ?? ozet.aktif,
    pay: ozet.kapsanan,
    tabloyaDayali: ozet.tabloToplam !== null,
  };
}
