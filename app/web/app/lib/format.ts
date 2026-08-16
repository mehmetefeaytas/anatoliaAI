/**
 * Görüntüleme yardımcıları — kanonik değer → Türkçe metin.
 *
 * İlgili: CLAUDE.md §10 (kanonik birimler), §19 (kullanıcıya dönük metinler Türkçe)
 * Sayı biçimi Türkçe kurala göre (binlik `.`, ondalık `,`) yazılır.
 */

import type { Extractor } from "./api";

const NF = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 });
/** Türkçe sayı biçimlendirici (binlik `.`, ondalık `,`). */
export const trNum = NF.format.bind(NF);

/**
 * «12 alandan 2'si», «5 ölçütün 1'i» — sayıya 3. tekil iyelik eki.
 *
 * Türkçe ek ses uyumuna bağlıdır ve sayının OKUNUŞUNA göre değişir (2 → iki'si,
 * 3 → üç'ü, 6 → altı'sı). Bir kural yazmak yerine 0–12 aralığı sayıldı: ekranda
 * bu ekin geçtiği iki yerde payda ya `/fields` uzunluğu (12) ya da ağırlık
 * tablosunun ölçüt sayısıdır (5) ve pay ondan büyük olamaz. Aralık dışında
 * kalırsa ek yerine «tanesi» kullanılır — yanlış ek yazmaktansa daha uzun ama
 * doğru bir cümle.
 *
 * Tek yerde durur çünkü iki ekran (banka künyesi ve yıldız kırılımı) aynı eki
 * kullanıyor; iki kopya bir gün ayrışırdı.
 */
const IYELIK: Record<number, string> = {
  0: "0'ı",
  1: "1'i",
  2: "2'si",
  3: "3'ü",
  4: "4'ü",
  5: "5'i",
  6: "6'sı",
  7: "7'si",
  8: "8'i",
  9: "9'u",
  10: "10'u",
  11: "11'i",
  12: "12'si",
};

export function sayiIyelik(n: number): string {
  return IYELIK[n] ?? `${n} tanesi`;
}

function isRec(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null;
}

const AYLAR = [
  "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
  "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
];

const ISO_TARIH = /^(\d{4})-(\d{2})-(\d{2})$/;

/**
 * ISO-8601 tarihi Türkçe okunuşa çevirir: `2026-12-31` → `31 Aralık 2026`.
 *
 * Kanonik biçim ISO'dur (CLAUDE.md §10) ve DEĞİŞMEZ — bu yalnız GÖSTERİM.
 * Şartname s.12 tablosunun «Kampanya Süresi» hücresi tam bu okunuşu yazıyor
 * ("31 Aralık 2026"); ekranda `2026-12-31` basmak, kanonik saklama biçimini
 * kullanıcıya sızdırmak olurdu (§19: kullanıcıya dönük metinler Türkçe).
 *
 * Ay adları SABİT bir diziden gelir, `Intl.DateTimeFormat`ten değil: `Intl`in
 * tarih verisi Node/tarayıcı derlemesine göre değişebiliyor (küçük ICU
 * derlemesinde İngilizce'ye düşer) ve bu ekran offline bir jüri makinesinde
 * açılacak. Sabit dizi her yerde aynı çıktıyı verir.
 *
 * ISO OLMAYAN ya da geçersiz bir dizeye `null` döner — çağıran ham değeri
 * basar. Tanımadığı bir biçimi tarih sanıp yeniden yazmak, olmayan bir bilgi
 * iddia etmek olurdu.
 */
export function trTarih(deger: string): string | null {
  const m = deger.match(ISO_TARIH);
  if (!m) return null;
  const [, yil, ay, gun] = m;
  const ayNo = Number(ay);
  const gunNo = Number(gun);
  if (ayNo < 1 || ayNo > 12 || gunNo < 1 || gunNo > 31) return null;
  return `${gunNo} ${AYLAR[ayNo - 1]} ${yil}`;
}

function num(v: unknown): string {
  return typeof v === "number" ? trNum(v) : String(v);
}

/**
 * Bilgi YOKLUĞUNUN jetonu.
 *
 * Şartnamenin beklenen çıktı tablosu (s.11–12) bu sözcüğü BİREBİR kullanıyor:
 * B Bankası satırının «Kampanya Süresi» hücresi «Belirtilmemiş», C Bankası
 * satırının «Masraf Durumu» hücresi «Masraf belirtilmemiş». Yani boş hücrenin
 * beklenen biçimi bir tire değil, bir CÜMLEDİR.
 *
 * Eskiden burada `«—»` vardı. Tire iki ayrı şeyi aynı işarete indiriyordu:
 * «bu bilgi kampanyada belirtilmemiş» ile «burada gösterilecek bir şey yok».
 * Ekran okuyucuda ise hiçbir şey okunmuyordu — erişilebilirlik açısından da
 * boş bir hücre.
 *
 * Şartnamenin alan-nitelemeli varyantı («Masraf belirtilmemiş») BİLEREK
 * kurulmadı: aynı bilgiyi iki biçimde üreten bir sözlük, sütun adı
 * değiştiğinde sessizce ayrışır. Sütun başlığı zaten hangi alan olduğunu
 * söylüyor; jeton tektir.
 */
export const BELIRTILMEMIS = "Belirtilmemiş";

/** Kanonik değeri insan-okur Türkçe metne çevirir. */
export function formatValue(v: unknown, field?: string): string {
  if (v === null || v === undefined) return BELIRTILMEMIS;
  if (typeof v === "boolean") return v ? "var" : "yok";
  if (typeof v === "number") {
    if (field === "kar_payi_orani" || field === "indirim_orani") return `%${num(v)}`;
    if (field === "vade_ay") return `${num(v)} ay`;
    if (field === "taksit_sayisi") return `${num(v)} taksit`;
    return num(v);
  }
  // Boş liste de bilgi taşımaz; `null` ile aynı jetonu kullanır. İkisini iki
  // ayrı işarete ayırmak, kullanıcıya anlamı olmayan bir ayrım göstermek olurdu.
  if (Array.isArray(v))
    return v.length ? v.map((x) => formatValue(x)).join(", ") : BELIRTILMEMIS;
  if (isRec(v)) {
    if ("min" in v && "max" in v) {
      const pfx = field === "kar_payi_orani" || field === "indirim_orani" ? "%" : "";
      return `${pfx}${num(v.min)} – ${pfx}${num(v.max)}`;
    }
    if ("value" in v) {
      const cur = typeof v.currency === "string" ? v.currency : "";
      return `${num(v.value)} ${cur === "TRY" ? "TL" : cur}`.trim();
    }
    if ("has_fee" in v) {
      if (v.has_fee === false) return "masrafsız";
      const amt = v.amount;
      return amt === null || amt === undefined ? "masraf var" : `${num(amt)} TL`;
    }
    if ("segments" in v && Array.isArray(v.segments)) {
      return v.segments.length ? v.segments.join(", ") : BELIRTILMEMIS;
    }
    if ("start" in v || "end" in v) {
      const s = v.start ? formatValue(v.start) : "?";
      const e = v.end ? formatValue(v.end) : "?";
      return `${s} → ${e}`;
    }
    return JSON.stringify(v);
  }
  if (typeof v === "string") {
    // Boş/boşluklu dize de bilgi taşımaz — boş liste ve `null` ile AYNI
    // jetonu kullanır. Üç ayrı yokluk biçimini üç ayrı işarete ayırmak,
    // kullanıcıya anlamı olmayan bir ayrım göstermek olurdu.
    if (v.trim() === "") return BELIRTILMEMIS;
    // Kanonik tarih ekranda Türkçe okunur; ISO olmayan dize aynen basılır.
    return trTarih(v) ?? v;
  }
  return String(v);
}

/**
 * Sunucunun işareti: bu avantaj parçası, yanındaki bir tablo kolonuyla AYNI
 * çıkarımdan geliyor (bkz. `compare.SUTUN_AVANTAJ_CAKISAN`).
 *
 * Dize sunucuyla birebir aynı olmak zorunda; tek kopya orada, buradaki sabit
 * onun okunuşu. Ayrışırsa dal hiç ateşlenmez ve hücre eski (tekrarlı) biçime
 * döner — sessiz ama zararsız bir bozulma, yanlış metin basmaktan iyidir.
 */
export const SUTUN_AVANTAJ_CAKISAN = "kampanya_avantaji_cakisan";

/** Avantaj hücresini oluşturan tek parça — sunucunun `TabloHucresi`si. */
export type AvantajParcasi = {
  field_name: string | null;
  value: unknown;
  /** Hangi dalda üretildi; çakışan parçalarda `SUTUN_AVANTAJ_CAKISAN`. */
  sutun?: string;
  /** Bankanın kendi ifadesi — çakışan parçada BU basılır. */
  raw_value?: string | null;
};

/**
 * Ham ifade tek başına bir hücreyi doldurabilir mi — ÖLÇÜLMÜŞ eşik.
 *
 * ÖLÇÜM (2026-08-16, `data/demo.db`, tazelenmiş korpus). `masraf_durumu`
 * alanında muafiyet bildiren **414 kaydın 414'ü de TEK sözcük**:
 *
 *     'Ücretsiz' (7) · 'ücretsiz' (6) · 'ücret' (5) · 'masraf' (3) ·
 *     'masrafsız' · 'Masrafsız' · 'Ücret'
 *
 * Çünkü kural yalnız TETİKLEYİCİ sözcüğü saklıyor, cümleyi değil. Çok
 * sözcüklü muafiyet ifadeleri ise en az ÜÇ sözcük:
 *
 *     'tahsis ücreti yansıtılmayacaktır'                        (3 sözcük)
 *     'ekspertiz ücreti banka tarafından karşılanmaktadır'      (5 sözcük)
 *
 * Dağılım iki kümede toplanıyor ve **2 sözcüklü hiçbir kayıt yok**. Eşik bu
 * boşluğa oturuyor — okunmuş, seçilmemiş. (Aynı yöntem `compare.ASGARI_GUVEN`
 * için de kullanıldı: eşik dağılımdaki boşluktan okunur.)
 *
 * Tek sözcük neden yetmez: «masraf» ya da «ücret» bir hücreyi doldurduğunda
 * kullanıcı ücretin VAR mı YOK mu olduğunu okuyamaz — muafiyet bilgisi
 * kanonik değerde, ham sözcükte değil. O yüzden tek sözcükte alan-adlı
 * biçime düşülür ve hücre asla boşalmaz.
 */
export function ayaktaDurur(ham: string | null | undefined): boolean {
  return typeof ham === "string" && ham.trim().split(/\s+/).length >= 2;
}

/**
 * «Kampanya Avantajı» hücresinin metni — PARÇALARDAN, serbest metinden değil.
 *
 * Şartname s.12'nin beşinci kolonu ("5.000 TL alışveriş çeki", "Ekspertiz
 * ücreti banka tarafından karşılanıyor") bir CÜMLEdir. Sistem o cümleyi
 * ÜRETMEZ (CLAUDE.md §21): sunucu, gerçek çıkarım satırlarından derlenmiş
 * parçalar gönderir (`/urun-tablosu`, `compare.avantaj_hucresi`) ve burada
 * yalnız **alan etiketi + kanonik değer** biçiminde okunur:
 *
 *     Ödül Miktarı: 5.000 TL · Alışveriş Puanı: 750
 *
 * Etiket dışarıdan gelir (`etiketle`), burada bir sözlük TUTULMAZ: alan
 * etiketlerinin tek kaynağı sunucunun `/fields` yanıtıdır ve ikinci bir kopya
 * bir gün ondan ayrışırdı. Etiket çözülemezse alan adı ham hâliyle basılır —
 * makine adı göstermek, yanlış bir Türkçe ad uydurmaktan iyidir.
 *
 * Parça yoksa `BELIRTILMEMIS`: boşluğun jetonu tablonun her yerinde aynıdır.
 */
export function avantajMetni(
  parcalar: readonly AvantajParcasi[],
  etiketle: (field: string) => string,
): string {
  if (parcalar.length === 0) return BELIRTILMEMIS;
  return parcalar
    .map((p) => {
      // Yandaki kolonu tekrar eden parça, bankanın KENDİ cümlesiyle basılır.
      if (p.sutun === SUTUN_AVANTAJ_CAKISAN && ayaktaDurur(p.raw_value)) {
        return `«${(p.raw_value as string).trim()}»`;
      }
      const deger = formatValue(p.value, p.field_name ?? undefined);
      if (!p.field_name) return deger;
      return `${etiketle(p.field_name)}: ${deger}`;
    })
    .join(" · ");
}

/** Güven skorunun sözel seviyesi — renk TEK sinyal olmasın diye (erişilebilirlik). */
export function confidenceLevel(c: number | null): {
  label: string;
  color: string;
} {
  if (c === null || Number.isNaN(c)) {
    return { label: "bilinmiyor", color: "var(--fg-faint)" };
  }
  if (c >= 0.85) return { label: "yüksek", color: "var(--ok)" };
  if (c >= 0.6) return { label: "orta", color: "var(--warn)" };
  return { label: "düşük", color: "var(--bad)" };
}

/**
 * `confidence_source` → Türkçe etiket.
 *
 * Bu bir DÜRÜSTLÜK sinyalidir: skorun sabit mi, kanıttan mı, modelin
 * logprob'undan mı geldiğini jüriye açıkça söyler
 * (bkz. src/extraction/rules/confidence.py modül başlığı).
 */
export const CONFIDENCE_SOURCE_LABELS: Record<string, string> = {
  rule_heuristic: "kanıt tabanlı (kural sinyalleri)",
  constant: "sabit değer (kalibre edilmemiş)",
  logprob: "model logprob",
  self_reported: "modelin kendi beyanı",
};

export function confidenceSourceLabel(src: string | null): string {
  if (!src) return "kaydedilmedi";
  return CONFIDENCE_SOURCE_LABELS[src] ?? src;
}

/** Hangi katman üretti — jüri denetiminin çekirdek sorusu. */
export const EXTRACTOR_LABELS: Record<Extractor, string> = {
  rule: "kural",
  ner: "NER",
  llm: "LLM",
};

export function extractorLabel(e: Extractor | null): string {
  return e ? EXTRACTOR_LABELS[e] ?? e : "—";
}

export function extractorClass(e: Extractor | null): string {
  return e ? `badge badge-${e}` : "badge";
}

/**
 * Çelişki türü → Türkçe başlık.
 *
 * ÖLÇÜLDÜ (2026-08-12): sözlükte yalnız iki giriş vardı ama
 * `src/comparison/contradiction.py` YEDİ tür üretiyor. Eksik olanlar için
 * `contradictionLabel` ham kodu basıyordu, yani jüri ekranında
 * `suresi_dolmus_kampanya` yazıyordu — ölçülen canlı dağılımın 10/16'sı tam
 * olarak o tür. Çelişki tespiti CLAUDE.md §18-2'de yenilikçilik hedefi; en
 * güçlü kartın etiketi makine kodu olarak görünmemeli.
 *
 * Başlıklar UYDURULMADI, her biri kuralın kendi `detail` cümlesinden türetildi
 * (satır numaraları o dosyada): 496 çelişen tutar bandı, 588 aynı belgede iki
 * bitiş tarihi, 624 süresi dolmuş ama yayında, 765 kesişmeyen kâr payı, 829 iki
 * sayfada farklı bitiş.
 *
 * AYNI BELGE ile İKİ SAYFA ayrımı başlıkta korunuyor: birincisi belgenin kendi
 * içinde tutarsız, ikincisi iki ayrı sayfanın birbirini tutmaması. Sistem
 * hangisinin doğru olduğunu söylemez, nerede durduklarını söyler.
 */
export const CONTRADICTION_LABELS: Record<string, string> = {
  masrafsiz_ama_ucret: "«Masrafsız» denmiş ama tahsis ücreti var",
  masrafsiz_ama_tutar: "«Masrafsız» denmiş ama masraf tutarı var",
  celisen_tutar_bandi: "Aynı belgede çelişen tutar bandı",
  celisen_kampanya_bitisi: "Aynı belgede iki farklı kampanya bitiş tarihi",
  suresi_dolmus_kampanya: "Kampanya süresi dolmuş ama sayfa hâlâ sunuyor",
  capraz_kar_payi_uyusmazligi: "İki sayfada kesişmeyen kâr payı oranı",
  capraz_kampanya_bitisi: "İki sayfada farklı kampanya bitiş tarihi",
};

export function contradictionLabel(kind: string): string {
  return CONTRADICTION_LABELS[kind] ?? kind;
}

/**
 * Katlanan çerçeve bloğunun gerekçesi → Türkçe etiket.
 *
 * Bilinmeyen bir kod gelirse OLDUĞU GİBİ gösterilir: gerekçeyi "diğer"e
 * çevirmek, katlamanın neden yapıldığını gizlerdi.
 */
export const BLOCK_REASON_LABELS: Record<string, string> = {
  cerez: "çerez",
  cookie: "çerez",
  kvkk: "KVKK",
  gizlilik: "gizlilik metni",
  alan_disi: "alan dışı",
  menu: "menü",
  navigasyon: "navigasyon",
  header: "sayfa başlığı",
  footer: "sayfa altı",
  yasal_uyari: "yasal uyarı",
  tekrar: "tekrar eden metin",
};

export function blockReasonLabel(gerekce: string | null | undefined): string {
  if (!gerekce) return "gerekçe belirtilmemiş";
  return BLOCK_REASON_LABELS[gerekce] ?? gerekce;
}
