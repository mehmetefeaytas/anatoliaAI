/**
 * Türkçe-doğru arama eşleştirme — istemci tarafı.
 *
 * İlgili: src/preprocessing/clean.py (`tr_fold_ascii` — SUNUCU ikizi),
 *         src/db/base.py (`ARAMA_ALANLARI`, `arama_terimleri`, `arama_suz`),
 *         ../components/KomutPaleti.tsx, ../components/BelgeSecici.tsx,
 *         ../../tests/arama.test.ts
 *
 * ## Neden kendi katlayıcımız — `toLowerCase()` Türkçe'de BOZUKTUR
 *
 * JavaScript'in `"İhtiyaç".toLowerCase()` çağrısı `"i̇htiyaç"` üretir: 'İ'
 * harfi 'i' + U+0307 (birleşen nokta) olarak iki karaktere açılır. Sonuç,
 * ekranda 'ihtiyaç' gibi GÖRÜNEN ama `includes("ihtiyac")` ile eşleşmeyen bir
 * dizedir. Aynı hata ters yönde de var: `"IŞIK".toLowerCase()` → `"ışık"`
 * değil `"isik"` beklenirken 'ı' yerine 'i' üretilir.
 *
 * Bu yüzden iki adım birden gerekir:
 *   1. `toLocaleLowerCase("tr-TR")` — 'I'→'ı', 'İ'→'i' doğru yapılır.
 *   2. Diakritik sadeleştirme — 'ş ç ğ ü ö ı â î û' → ASCII, çünkü kullanıcı
 *      Türkçe klavyesi olmadan da arar: 'ihtiyac' yazan biri 'İhtiyaç
 *      Finansmanı'nı bulmalıdır.
 *
 * ## Sunucuyla AYNI olmak zorunda
 *
 * Arama iki katmanlıdır: sunucu `GET /search` ile eler, istemci gelen listeyi
 * yerinde daraltır ve eşleşmeyi vurgular. İki katlayıcı ayrışırsa kullanıcı
 * sunucunun bulduğu bir satırın istemcide kaybolduğunu (ya da tersini) görür
 * ve bunu bir arıza olarak bildiremez bile. Parite ortak bir fikstürle
 * kanıtlanır: `tests/arama_katlama_ornekleri.json` iki testte de okunur.
 *
 * Yeni bağımlılık YOK: `useAsync.ts` başlığındaki gerekçenin aynısı (offline
 * kısıtı + lisans denetimi). Eşleşme de gecikme de elle yazılır.
 */

/**
 * Diakritik sadeleştirme haritası — `clean.py` içindeki `_TR_ASCII` ile
 * BİREBİR aynı olmak zorunda. Küçük harfli anahtarlar yeterli: harita
 * küçültmeden SONRA uygulanır.
 */
const TR_ASCII: Readonly<Record<string, string>> = {
  ş: "s",
  ç: "c",
  ğ: "g",
  ü: "u",
  ö: "o",
  ı: "i",
  â: "a",
  î: "i",
  û: "u",
};

/**
 * Türkçe-doğru küçültme + diakritik sadeleştirme.
 *
 * Sunucudaki `tr_fold_ascii` ile aynı sonucu üretir; sıra da aynıdır
 * (küçült → sadeleştir → NFKD → birleşen işaretleri at).
 */
export function trKatla(metin: string): string {
  if (!metin) return "";
  let cikti = "";
  for (const harf of metin.toLocaleLowerCase("tr-TR")) {
    cikti += TR_ASCII[harf] ?? harf;
  }
  // NFKD ayrıştırması 'é' gibi birleşik karakterleri taban + işaret hâline
  // getirir; `\p{M}` (mark) sınıfı işaretleri atar. Böylece kaynak metinde
  // hangi biçimde kodlandığından bağımsız aynı forma inilir.
  return cikti.normalize("NFKD").replace(/\p{M}/gu, "");
}

/**
 * Sorguyu katlanmış, tekrarsız terimlere böler.
 *
 * Terimler **VE** ile birleşir ve farklı alanlara dağılabilir: 'kuveyt konut'
 * sorgusu banka adında 'kuveyt', kampanya türünde 'konut' bulan bir belgeyi
 * eşleşmiş sayar. Sunucudaki `arama_terimleri()` ile aynı kural.
 */
export function aramaTerimleri(sorgu: string): string[] {
  if (!sorgu) return [];
  const gorulen = new Set<string>();
  for (const parca of trKatla(sorgu).split(/\s+/)) {
    if (parca) gorulen.add(parca);
  }
  return [...gorulen];
}

/** Tek bir metin, verilen terimlerin HEPSİNİ içeriyor mu. */
export function terimlerEslesiyorMu(metin: string, terimler: string[]): boolean {
  if (terimler.length === 0) return false;
  const katli = trKatla(metin);
  return terimler.every((t) => katli.includes(t));
}

/**
 * Terimler alanlara DAĞILABİLİR: her terim en az bir alanda geçmeli.
 *
 * `terimlerEslesiyorMu(alanlar.join(" "), …)` ile aynı şey DEĞİLDİR: birleştirme
 * alan sınırında yeni bir dize üretir ve 'türkkonut' gibi olmayan bir kelimeyi
 * eşleştirebilirdi.
 */
export function alanlarEslesiyorMu(
  alanlar: ReadonlyArray<string | null | undefined>,
  terimler: string[],
): boolean {
  if (terimler.length === 0) return false;
  const katlanmis = alanlar.filter(Boolean).map((a) => trKatla(a as string));
  return terimler.every((t) => katlanmis.some((k) => k.includes(t)));
}

/**
 * `eslesme.alan` için Türkçe etiket.
 *
 * Sunucu sütun adını olduğu gibi döndürür (bir SINIF ETİKETİDİR, kullanıcıya
 * dönük metin değil); ekranda okunacak karşılığı burada üretilir. Bilinmeyen
 * bir alan adı UYDURULMAZ, boş dönerse arayüz etiketi hiç basmaz.
 */
const ALAN_ETIKETLERI: Readonly<Record<string, string>> = {
  ozet: "özet",
  campaign_type: "kampanya türü",
  bank_name: "banka",
  source_url: "adres",
};

export function alanEtiketi(alan: string): string {
  return ALAN_ETIKETLERI[alan] ?? "";
}

/** Eşleşen parçanın metin içindeki aralıkları — vurgulama için. */
export type Vurgu = { bas: number; son: number; vurgulu: boolean };

/**
 * Metni, terimlerin geçtiği yerlerden vurgulu/vurgusuz parçalara böler.
 *
 * Konumlar KATLANMIŞ metinde bulunur ama ÖZGÜN metnin indekslerine çevrilir:
 * kullanıcıya 'kar payi' değil 'kâr payı' gösterilmeli. Çeviri, katlamanın
 * karakter karakter yapılıp her katlanmış karakterin kaynağının saklanmasıyla
 * olur — katlama uzunluk korumaz (bkz. `tr_katla_haritali`, sunucu ikizi).
 */
export function vurgulariBul(metin: string, terimler: string[]): Vurgu[] {
  if (!metin) return [];
  if (terimler.length === 0) return [{ bas: 0, son: metin.length, vurgulu: false }];

  let katli = "";
  const harita: number[] = [];
  for (let i = 0; i < metin.length; i += 1) {
    const parca = trKatla(metin[i]);
    for (let j = 0; j < parca.length; j += 1) harita.push(i);
    katli += parca;
  }

  // Örtüşen aralıklar birleştirilsin diye önce toplanır, sonra sıralanır.
  const araliklar: Array<[number, number]> = [];
  for (const terim of terimler) {
    let k = katli.indexOf(terim);
    while (k >= 0) {
      araliklar.push([harita[k], harita[k + terim.length - 1] + 1]);
      k = katli.indexOf(terim, k + 1);
    }
  }
  if (araliklar.length === 0) {
    return [{ bas: 0, son: metin.length, vurgulu: false }];
  }
  araliklar.sort((a, b) => a[0] - b[0] || a[1] - b[1]);

  // Örtüşen VE bitişik aralıklar birleştirilir. Bitişikleri de birleştirmek
  // şart: 'finans' + 'finansmani' iki ayrı vurgu olarak kalsaydı ekranda tek
  // parça gibi görünen şey DOM'da ikiye bölünürdü ve kopyalanan metin sessizce
  // farklılaşabilirdi.
  const birlesik: Array<[number, number]> = [];
  for (const [bas, son] of araliklar) {
    const sonuncu = birlesik[birlesik.length - 1];
    if (sonuncu && bas <= sonuncu[1]) {
      sonuncu[1] = Math.max(sonuncu[1], son);
    } else {
      birlesik.push([bas, son]);
    }
  }

  const parcalar: Vurgu[] = [];
  let imlec = 0;
  for (const [bas, son] of birlesik) {
    if (bas > imlec) parcalar.push({ bas: imlec, son: bas, vurgulu: false });
    parcalar.push({ bas, son, vurgulu: true });
    imlec = son;
  }
  if (imlec < metin.length) {
    parcalar.push({ bas: imlec, son: metin.length, vurgulu: false });
  }
  return parcalar;
}
