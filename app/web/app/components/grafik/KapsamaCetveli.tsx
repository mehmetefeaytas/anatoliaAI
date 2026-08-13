"use client";

/**
 * KAPSAMA CETVELİ — ekranın imza öğesi.
 *
 * İlgili: ../../styles/cetvel.css, ../../lib/api.ts (`CompareRow`, `Bank`,
 *         `BankaKapsami`), ../../lib/format.ts, ../KaynakDipnotu.tsx,
 *         ../ComparePanel.tsx, CLAUDE.md §17 (adil kıyas), §6 (zor vakalar)
 *
 * ## Neden canvas değil, saf DOM
 *
 * Chart.js tuvali üç şeyi birden yapamıyor ve üçü de bu ürünün tezine ait:
 *
 *  1. **Erişilebilirlik ağacında yok.** `<canvas>` içine çizilen bir çubuk
 *     ekran okuyucuya hiçbir şey söylemez. `KiyasCubuklari` bu yüzden grafiğin
 *     ALTINA ayrıca metin bir liste basmak zorundaydı — aynı bilgi iki kez.
 *     Cetvelde çubuğun kendisi `role="img"` + `aria-label` taşır; grafiğin
 *     erişilebilir eşi diye ayrı bir şey yoktur, grafik ZATEN erişilebilirdir.
 *  2. **Dört kapsama hâlini ayrı BİÇİMLERLE anlatamıyor.** Tuvalde elde renk ve
 *     uzunluk var; kesikli çerçeve, 135° tarama dokusu, kesik taban çizgisi ve
 *     konumlu aralık kutusu yok. Renk TEK sinyal olamaz (WCAG 1.4.1).
 *  3. **`aria-label` / `title` taşıyamıyor.** Bir çubuğun «%1,69,
 *     kıyaslanabilir» olduğu ancak tuvalin dışında yazılabiliyordu.
 *
 * `KiyasCubuklari` ve `RadarKiyas` 2026-08-12'de SİLİNDİ. Hiçbir kod onları
 * import etmiyordu (yalnız yorumlar anıyordu) ve `chart.js` +
 * `react-chartjs-2`nin TEK tüketicisiydiler: sıfır piksel karşılığında iki
 * çalışma-zamanı bağımlılığı ve onların lisans denetimi yükü (CLAUDE.md §20
 * yalnız Apache/MIT/BSD paket şartı koyuyor). Yukarıdaki üç maddelik gerekçe
 * onların dosya başlığından DEĞİL buradan okunur — silinen şey kod, karar değil.
 *
 * ## Onbir satırın onbiri her zaman çizilir
 *
 * ÖLÇÜLDÜ: `kar_payi_orani` 1.774 belgenin 56'sında, 11 bankanın 6'sında var.
 * `/compare` yalnız değer TAŞIYAN satırları döndürür; cetveli doğrudan onunla
 * çizmek beş bankayı sessizce yok ederdi ve ekran «bu alanda 6 banka var»
 * derdi. Bu yüzden bileşen banka kataloğunu (`/banks`) ve belge sayaçlarını
 * (`/stats` → `banka_kapsami`) da alır: ölçülemeyen banka kesik taban çizgisi
 * ve «veri yok · N belge» etiketiyle yerini korur.
 *
 * İddia «kim kazandı» değil, «neyi ne kadar biliyoruz». Boşluğun kendisi
 * sayılır.
 *
 * ## Dört hâl, dört BİÇİM
 *
 *   dolu     · değer çıkarıldı, kıyaslanabilir → dolu mürekkep çubuk
 *   kosullu  · değer var, doğrudan kıyaslanamaz → kesikli çerçeve + tarama
 *   aralik   · değer bir aralık → eksende KONUMLU kutu, iki ucu kalın
 *   bos      · belge var, bu alanda değer yok → kesik taban çizgisi
 *   belgesiz · bu bankada hiç belge yok → nötr gri kutu
 *
 * Beşi de renkten bağımsız ayırt edilebilir; ayrıca her satır durumunu YAZIYLA
 * ve `aria-label` ile söyler. Renk asla tek sinyal değil.
 *
 * ## %0 ≠ null
 *
 * `%0` / «masrafsız» gerçek bir üründür ve alanın en avantajlı ucudur
 * (CLAUDE.md §6, negasyon). Sıfır genişlikli çizilse kesik çizgiyle karışırdı;
 * bu yüzden sıfır GÖRÜNÜR bir mürekkep işaretidir. `null` kesik çizgi, `%0`
 * görünür işaret — ikisi asla aynı çubuğa çizilmez.
 */

import type { Bank, BankaKapsami, CompareRow } from "../../lib/api";
import { formatValue, trNum } from "../../lib/format";
import KaynakDipnotu from "../KaynakDipnotu";

/**
 * Cetvele giren bir satır: kayıt + TÜR İÇİNDEKİ sırası.
 *
 * Sıra dışarıdan gelir, burada yeniden hesaplanmaz: aynı numarayı hem cetvel
 * hem denetlenebilir tablo basıyor ve iki yerde hesaplanırsa er ya da geç
 * ayrışır (`ComparePanel.turlereBol`).
 */
export type CetvelGirdisi = { row: CompareRow; sira: number | null };

type Props = {
  /** Tek kampanya türünün satırları — sunucunun sırasıyla. */
  satirlar: CetvelGirdisi[];
  /** Tüm bankalar; verisi olmayanların satırı ancak buradan bilinir. */
  bankalar?: Bank[];
  /** Kıyaslanan alan (değer biçimlendirmesi için). */
  alan: string;
  /**
   * Banka slug → belge/alan kapsamı (`/stats` → `banka_kapsami`). «veri yok»
   * satırındaki belge sayısı buradan gelir; yoksa sayı UYDURULMAZ, yalnız
   * «veri yok» yazılır.
   */
  kapsam?: Record<string, BankaKapsami> | null;
};

type Hal = "dolu" | "kosullu" | "aralik" | "bos" | "belgesiz";

type Satir = {
  slug: string;
  ad: string;
  hal: Hal;
  /** Eksendeki konum (dolu/koşullu); yoksa `null`. */
  deger: number | null;
  /** Aralığın uçları — yalnız `hal === "aralik"`. */
  min: number | null;
  max: number | null;
  /** Ekrana basılan değer metni. */
  metin: string;
  /** Mono durum etiketi: `kıyaslanabilir` / `koşullu oran` / `aralık`. */
  durum: string;
  /** Ölçülemeyen satırda taranan belge sayısı; bilinmiyorsa `null`. */
  belge: number | null;
  sira: number | null;
  row: CompareRow | null;
};

/** Yüzde ile yazılan alanlar — eksen etiketi ve aralık metni için. */
function yuzdeliMi(alan: string): boolean {
  return alan === "kar_payi_orani" || alan === "indirim_orani";
}

/** Kanonik değer bir aralık mı (`{min, max}`) — öyleyse uçları. */
function aralikUclari(v: unknown): { min: number; max: number } | null {
  if (typeof v !== "object" || v === null) return null;
  const o = v as Record<string, unknown>;
  if (typeof o.min === "number" && typeof o.max === "number") {
    return { min: o.min, max: o.max };
  }
  return null;
}

/**
 * Cetvelin değer kolonu 132px'tir ve `formatValue` aralığı «%2,95 – %4,42»
 * olarak yazar; iki yüzde işareti o kolonu taşırıyor. Cetvelde aralık tek
 * yüzdeyle kısaltılır — TABLODA tam hâli durur, yani kısaltma bilgi kaybı
 * değil, aynı bilginin iki ölçüsü.
 */
function kisaMetin(v: unknown, alan: string): string {
  const ar = aralikUclari(v);
  if (!ar) return formatValue(v, alan);
  const on = yuzdeliMi(alan) ? "%" : "";
  return `${on}${trNum(ar.min)}–${trNum(ar.max)}`;
}

/**
 * Bir satırın kapsama hâli. Cetvel ile KAPSAMA SAYACI aynı kuralı kullanır:
 * ekranın başındaki «kıyaslanabilir: 1 · aralık: 2 · koşullu: 1» kırılımı ile
 * çubukların biçimi iki ayrı yerde hesaplanırsa er ya da geç ayrışır.
 */
export function satirHali(row: CompareRow): "dolu" | "kosullu" | "aralik" {
  if (aralikUclari(row.value)) return "aralik";
  return row.comparable && row.sort_key !== null ? "dolu" : "kosullu";
}

/** Kapsama sayacının verisi: kaç banka, hangi hâlde. */
export type KapsamaOzeti = {
  /** Bu alanda değer TAŞIYAN tekrarsız banka sayısı. */
  kapsanan: number;
  kiyaslanabilir: number;
  aralik: number;
  kosullu: number;
};

export function kapsamaOzeti(satirlar: CetvelGirdisi[]): KapsamaOzeti {
  const ozet: KapsamaOzeti = {
    kapsanan: 0,
    kiyaslanabilir: 0,
    aralik: 0,
    kosullu: 0,
  };
  const gorulen = new Set<string>();
  for (const { row } of satirlar) {
    if (gorulen.has(row.bank)) continue;
    gorulen.add(row.bank);
    ozet.kapsanan += 1;
    const hal = satirHali(row);
    if (hal === "dolu") ozet.kiyaslanabilir += 1;
    else if (hal === "aralik") ozet.aralik += 1;
    else ozet.kosullu += 1;
  }
  return ozet;
}

/** Eksen işaretinin metni. Birim ekleri (ay/taksit) işarette YAZILMAZ:
 *  altı işaretin altısında tekrar eden bir birim, ölçeği okunmaz kılıyor. */
function eksenEtiketi(t: number, alan: string): string {
  return `${yuzdeliMi(alan) ? "%" : ""}${trNum(t)}`;
}

/** Eksen adımı için "yuvarlak" katsayılar. */
const ADIM_ADAYLARI = [1, 2, 2.5, 5, 10];

/**
 * Eksenin üst ucu ve adımı — altı işaret (0'dan uca beş aralık).
 *
 * Uç, en büyük değere göre YUKARI yuvarlanır: eksen tam en büyük değerde
 * bitse, birinci satırın çubuğu rayı tamamen doldurur ve «tavana vurdu» diye
 * okunur — oysa söylenen yalnızca «bu kümenin en büyüğü».
 */
function ekseniKur(enBuyuk: number): { uc: number; adim: number } {
  if (!(enBuyuk > 0)) return { uc: 1, adim: 0.2 };
  const kaba = enBuyuk / 5;
  const buyukluk = 10 ** Math.floor(Math.log10(kaba));
  for (const k of ADIM_ADAYLARI) {
    const adim = k * buyukluk;
    if (adim * 5 >= enBuyuk) return { uc: adim * 5, adim };
  }
  const adim = 10 * buyukluk;
  return { uc: adim * 5, adim };
}

/**
 * Satırları kurar: ölçülenler sunucunun sırasıyla, ölçülemeyenler belge
 * sayısına göre azalan sırada.
 *
 * Ölçülemeyenlerin sırası alfabetik DEĞİL: «291 belge tarandı, alan geçmedi»
 * ile «2 belge tarandı, alan geçmedi» aynı güçte bulgu değildir ve göz güçlü
 * olanı önce görmeli.
 */
function cetveliKur(
  satirlar: CetvelGirdisi[],
  bankalar: Bank[] | undefined,
  alan: string,
  kapsam: Record<string, BankaKapsami> | null | undefined,
): { olculen: Satir[]; olculemeyen: Satir[]; uc: number; adim: number } {
  const olculen: Satir[] = [];
  const gorulen = new Set<string>();

  for (const { row, sira } of satirlar) {
    if (gorulen.has(row.bank)) continue;
    gorulen.add(row.bank);
    const ar = aralikUclari(row.value);
    const hal: Hal = satirHali(row);
    olculen.push({
      slug: row.bank,
      ad: row.bank_name || row.bank,
      hal,
      deger: ar ? null : row.sort_key,
      min: ar?.min ?? null,
      max: ar?.max ?? null,
      metin: kisaMetin(row.value, alan),
      durum:
        hal === "dolu"
          ? "kıyaslanabilir"
          : hal === "aralik"
            ? "aralık"
            : "koşullu oran",
      belge: null,
      // Numara YALNIZ sıralamaya giren satıra verilir; kıyaslanamayan bir
      // satıra numara vermek, reddedilen sıralamayı geri getirmek olurdu.
      sira: hal === "dolu" ? sira : null,
      row,
    });
  }

  const olculemeyen: Satir[] = [];
  for (const b of bankalar ?? []) {
    if (gorulen.has(b.slug)) continue;
    const belge = kapsam?.[b.slug]?.belge ?? null;
    olculemeyen.push({
      slug: b.slug,
      ad: b.name,
      // Belge sayısı BİLİNMİYORSA (kapsam gelmediyse) «belgesiz» denmez:
      // ölçülmemiş bir şeyi sıfır saymak, tam olarak bu ürünün reddettiği şey.
      hal: belge === 0 ? "belgesiz" : "bos",
      deger: null,
      min: null,
      max: null,
      // Boşluğun kendisi SAYILIR: belge sayısı olmadan bu satır «hiç bakmadık»
      // diye okunurdu, oysa 291 belge tarandı ve alan geçmedi. Sayı yoksa
      // uydurulmaz, cümle kısalır.
      metin:
        belge === 0
          ? "belge yok"
          : `veri yok${belge === null ? "" : ` · ${trNum(belge)} belge`}`,
      durum: belge === 0 ? "belge yok" : "ölçülemedi",
      belge,
      sira: null,
      row: null,
    });
  }
  olculemeyen.sort((a, b) => (b.belge ?? -1) - (a.belge ?? -1));

  const sayilar = olculen.flatMap((s) =>
    s.hal === "aralik"
      ? [s.min ?? 0, s.max ?? 0]
      : s.deger === null
        ? []
        : [s.deger],
  );
  const { uc, adim } = ekseniKur(sayilar.length ? Math.max(...sayilar) : 0);

  return { olculen, olculemeyen, uc, adim };
}

/** Yüzde genişliği — eksenin dışına taşmaz. */
function oran(v: number, uc: number): number {
  return Math.max(0, Math.min(100, (v / uc) * 100));
}

export default function KapsamaCetveli({
  satirlar,
  bankalar,
  alan,
  kapsam,
}: Props) {
  const { olculen, olculemeyen, uc, adim } = cetveliKur(
    satirlar,
    bankalar,
    alan,
    kapsam,
  );
  if (olculen.length === 0 && olculemeyen.length === 0) return null;

  const isaretler = Array.from({ length: 6 }, (_, i) => i * adim);

  return (
    <div className="cetvel">
      <div className="cetvel-bas">
        <span className="cetvel-bas-etiket">banka</span>
        <div className="cetvel-eksen" aria-hidden="true">
          {isaretler.map((t) => (
            <span key={t}>{eksenEtiketi(t, alan)}</span>
          ))}
        </div>
        <span className="cetvel-bas-deger">değer</span>
      </div>

      <ul className="cetvel-liste" role="list">
        {olculen.map((s) => (
          <OlculenSatir key={s.slug} s={s} alan={alan} uc={uc} />
        ))}
      </ul>

      {olculemeyen.length > 0 && (
        <>
          <div className="cetvel-ayirici">
            <span className="cetvel-ayirici-etiket">
              ölçülemedi · {olculemeyen.length} banka
            </span>
            <span className="cetvel-ayirici-not">
              Belge var, bu alanda değer yok. Satır silinmiyor: sıfır değil,
              boş.
            </span>
          </div>
          <ul className="cetvel-liste cetvel-liste-bos" role="list">
            {olculemeyen.map((s) => (
              <OlculemeyenSatir key={s.slug} s={s} />
            ))}
          </ul>
        </>
      )}

      <p className="cetvel-not">
        Dolu çubuk sıralamaya girer. Kesikli çerçeve ve tarama dokusu «değer
        okundu ama doğrudan kıyaslanamaz» der; kesik taban çizgisi «bu alan bu
        bankada hiç geçmiyor» der. Üçü ayrı biçim taşır, yalnız ayrı renk değil.
      </p>
    </div>
  );
}

/** Değer taşıyan satır: sıra rozeti · çubuk · değer + kaynak + durum. */
function OlculenSatir({
  s,
  alan,
  uc,
}: {
  s: Satir;
  alan: string;
  uc: number;
}) {
  // Aralık satırının değeri TAM hâliyle de söylenmeli: cetveldeki metin
  // kolonun genişliği için kısaltıldı, `aria-label` kısaltılmaz.
  const tamMetin =
    s.hal === "aralik" && s.row ? formatValue(s.row.value, alan) : s.metin;
  const etiket = `${s.ad}: ${tamMetin}, ${s.durum}`;
  // Sınıf adı şablonun DIŞINDA seçiliyor: `scripts/css_sinif_denetimi.py`
  // `className={`…${…}`}` içindeki dizge sabitlerini sınıf adı sayar ve
  // şablona gömülü bir `"dolu"` karşılaştırması tanımsız sınıf sanılırdı.
  const durumSinifi = s.hal === "dolu" ? "cetvel-durum-ok" : "cetvel-durum-uyari";
  const degerSinifi =
    s.hal === "dolu" ? "cetvel-deger-sayi" : "cetvel-deger-sayi-kisik";

  return (
    <li className="cetvel-satir">
      <div className="cetvel-banka">
        <span className={`rank-pill${s.sira === 1 ? " first" : ""}`}>
          {s.sira ?? "—"}
        </span>
        <span className="cetvel-banka-ad">{s.ad}</span>
      </div>

      <div className="cetvel-ray">
        <Cubuk s={s} uc={uc} etiket={etiket} />
      </div>

      <div className="cetvel-deger">
        <div className="cetvel-deger-satir">
          <strong className={degerSinifi}>{s.metin}</strong>
          {/* Her yüzeydeki AYNI jest: rozete bas, belge yandan açılsın,
              değerin karakter aralığı vurgulu olsun (bkz. KaynakDipnotu). */}
          {s.row && (
            <KaynakDipnotu
              campaignId={s.row.campaign_id}
              span={s.row}
              rawValue={s.row.raw_value}
            />
          )}
        </div>
        <span className={`cetvel-durum ${durumSinifi}`}>{s.durum}</span>
      </div>
    </li>
  );
}

/**
 * Rayın içindeki tek işaret. `role="img"` + `aria-label`: bu bir süs değil,
 * bir veri gösterimi ve ekran okuyucu onu okumak zorunda.
 */
function Cubuk({ s, uc, etiket }: { s: Satir; uc: number; etiket: string }) {
  if (s.hal === "aralik" && s.min !== null && s.max !== null) {
    const sol = oran(s.min, uc);
    const genislik = Math.max(0, oran(s.max, uc) - sol);
    return (
      <div
        className="cetvel-cubuk-aralik"
        style={{ left: `${sol}%`, width: `${genislik}%` }}
        role="img"
        aria-label={etiket}
        title={`${etiket} — aralık doğrudan kıyaslanamaz`}
      />
    );
  }

  if (s.hal === "kosullu") {
    // Eksende konumlandırılamayan koşullu değer (sayısal anahtarı yok) rayın
    // tamamını kaplar: bir uzunluk vermek uydurma bir büyüklük iddiası olurdu,
    // hiç çizmemek ise satırı boş satırla karıştırırdı.
    const genislik = s.deger === null ? 100 : oran(s.deger, uc);
    return (
      <div
        className="cetvel-cubuk-kosullu"
        style={{ width: `${genislik}%` }}
        role="img"
        aria-label={etiket}
        title={
          s.deger === null
            ? `${etiket} — eksende konumlandırılamıyor`
            : `${etiket} — kanal/müşteri/taban koşuluna bağlı`
        }
      />
    );
  }

  // dolu · %0 dahil. Sıfır GÖRÜNÜR bir işarettir (bkz. dosya başlığı).
  if (s.deger === 0) {
    return (
      <div
        className="cetvel-cubuk-sifir"
        role="img"
        aria-label={etiket}
        title={`${etiket} — sıfır bir ürün, eksik veri değil`}
      />
    );
  }
  return (
    <div
      className="cetvel-cubuk"
      style={{ width: `${oran(s.deger ?? 0, uc)}%` }}
      role="img"
      aria-label={etiket}
      title={etiket}
    />
  );
}

/** Ölçülemeyen satır: numara yok, çubuk yok — ama satır var. */
function OlculemeyenSatir({ s }: { s: Satir }) {
  const etiket =
    s.hal === "belgesiz"
      ? `${s.ad}: bu bankada hiç belge yok, ölçüm yapılamadı`
      : `${s.ad}: veri yok${
          s.belge === null ? "" : `, ${trNum(s.belge)} belge tarandı`
        }, bu alan metinde geçmiyor`;

  return (
    <li className="cetvel-satir cetvel-satir-bos">
      <span className="cetvel-banka-bos">{s.ad}</span>
      <div className="cetvel-ray-bos">
        {s.hal === "belgesiz" ? (
          <div
            className="cetvel-kutu-belgesiz"
            role="img"
            aria-label={etiket}
            title={etiket}
          />
        ) : (
          <div
            className="cetvel-cizgi"
            role="img"
            aria-label={etiket}
            title={etiket}
          />
        )}
      </div>
      <span className="cetvel-yok">{s.metin}</span>
    </li>
  );
}
