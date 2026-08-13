/**
 * İşlem günlüğü (audit log) — saf görüntüleme yardımcıları.
 *
 * İlgili: ../components/GunlukPanel.tsx, ../../../src/api/gunluk.py
 *         CLAUDE.md §19 (kullanıcıya dönük metinler Türkçe)
 *
 * Bileşen değil bu dosya test ediliyor: web tarafında DOM testi yok (Node'un
 * yerleşik koşucusu, sıfır bağımlılık), bu yüzden karar veren her şey saf
 * fonksiyona çekilip `.tsx` ince bir çizici olarak bırakılıyor.
 *
 * ## Zaman neden UTC gösteriliyor
 *
 * Kayıtlar sunucuda UTC yazılıyor (`utc_now_iso()`). Panel onları yerel saate
 * çevirseydi ekrandaki satır ile dosyadaki satır BİRBİRİNİ TUTMAZDI ve "şu
 * saatte ne oldu" sorusu, denetim kaydının asıl işi, her seferinde bir saat
 * dilimi hesabına dönerdi. Sütun başlığı bu yüzden açıkça «Zaman (UTC)»
 * diyor — sessizce UTC göstermek, yerel sanılmasından daha kötü olurdu.
 */

import type { GunlukKaydi } from "./api";

/**
 * Türkçe sayı biçimi (binlik `.`, ondalık `,`) — `format.ts`'teki `trNum` ile
 * AYNI yapılandırma, ama burada yeniden kuruluyor. Gerekçe test koşucusudur,
 * üslup değil:
 *
 * `npm run test` Node'un yerleşik koşucusu + tip sıyırmasıdır (sıfır bağımlılık
 * — offline kısıtı). Node'un ESM çözücüsü uzantısız göreli bir import'u
 * ÇALIŞMA ZAMANINDA bulamaz; komşu `lib/*.ts` dosyaları bu yüzden yalnız TİP
 * import ediyor (tipler derlemede silinir). `import { trNum } from "./format"`
 * yazmak bu dosyayı test edilemez yapardı; `"./format.ts"` yazmak ise
 * `tsc --noEmit` altında kaynak dosyada TS5097 üretirdi
 * (`allowImportingTsExtensions` kapalı).
 *
 * Kopyalanan şey bir KURAL değil, tek satırlık bir yerel ayar; kural
 * (CLAUDE.md §10: binlik `.`, ondalık `,`) zaten belgede duruyor ve iki
 * tanımın ayrışması `web/tests/gunluk.test.ts` içindeki beklentileri kırar.
 */
const NF = new Intl.NumberFormat("tr-TR", { maximumFractionDigits: 2 });
const trNum = NF.format.bind(NF);

/** Değer yoksa basılacak işaret. Boş dize DEĞİL: hücrenin boş olduğu görünmeli. */
export const YOK = "—";

/**
 * `2026-08-13T09:14:22+00:00` → `2026-08-13 09:14:22` (UTC).
 *
 * Ayrıştırılamayan damga UYDURULMAZ: `YOK` döner. `Invalid Date` basmak,
 * kaydın bozuk olduğunu söylemek yerine ekrana çöp yazmak olurdu.
 */
export function zamanDamgasi(iso: string | null | undefined): string {
  if (typeof iso !== "string" || !iso.trim()) return YOK;
  const t = Date.parse(iso);
  if (!Number.isFinite(t)) return YOK;
  const d = new Date(t);
  const iki = (n: number) => String(n).padStart(2, "0");
  return (
    `${d.getUTCFullYear()}-${iki(d.getUTCMonth() + 1)}-${iki(d.getUTCDate())} ` +
    `${iki(d.getUTCHours())}:${iki(d.getUTCMinutes())}:${iki(d.getUTCSeconds())}`
  );
}

/** `12.4` → `12,4 ms`; saniyeye taşan süreler `1,24 s`. */
export function sureEtiketi(ms: number | null | undefined): string {
  if (typeof ms !== "number" || !Number.isFinite(ms)) return YOK;
  if (ms >= 1000) return `${trNum(ms / 1000)} s`;
  return `${trNum(ms)} ms`;
}

/**
 * Durum koduna göre rozet sınıfı.
 *
 * 4xx UYARI, 5xx HATA olarak ayrılıyor: birincisi çoğunlukla istemcinin
 * gönderdiği bir şeydir (bilinmeyen banka, meşgul iş), ikincisi sunucunun
 * kendi arızasıdır ve denetim kaydında göze çarpması gerekir.
 */
export function durumSinifi(kod: number | null | undefined): string {
  if (typeof kod !== "number" || !Number.isFinite(kod)) return "badge";
  if (kod >= 500) return "badge badge-bad";
  if (kod >= 400) return "badge badge-warn";
  return "badge badge-ok";
}

/**
 * Eylem özeti anahtarlarının Türkçe etiketleri.
 *
 * Liste kapalı DEĞİL: bilinmeyen bir anahtar gizlenmez, ham adıyla basılır.
 * Gizlemek, bir ucun bildirdiği bilgiyi panelin sessizce yutması olurdu; ham
 * ad çirkin ama dürüsttür ve etiketi eklemek tek satır.
 */
export const EYLEM_ETIKETLERI: Record<string, string> = {
  banka: "banka",
  banka_adi: "banka adı",
  hedef_dizin: "hedef dizin",
  kampanya_turu: "kampanya türü",
  bulunan_alan: "bulunan alan",
  eksik_alan: "eksik alan",
  metin_uzunlugu: "metin uzunluğu",
  yazilan_dosya: "yazılan dosya",
  yazilan_ozet: "yazılan özet",
  durum_adi: "iş durumu",
};

/**
 * Eylem sözlüğünü tek satırlık okunur bir özete çevirir.
 *
 * `null` değerler ATLANIR: "hedef dizin: —" satırı bilgi taşımaz, yalnız
 * satırı uzatır. Özet tamamen boşsa `null` döner ve çağıran hücreyi boş
 * bırakır (boş ≠ 0 ≠ hata doktrini).
 */
export function eylemOzeti(
  eylem: Record<string, unknown> | null | undefined,
): string | null {
  if (!eylem || typeof eylem !== "object") return null;
  const parcalar: string[] = [];
  for (const [ad, deger] of Object.entries(eylem)) {
    if (deger === null || deger === undefined || deger === "") continue;
    const etiket = EYLEM_ETIKETLERI[ad] ?? ad;
    const yazi = typeof deger === "number" ? trNum(deger) : String(deger);
    parcalar.push(`${etiket}: ${yazi}`);
  }
  return parcalar.length ? parcalar.join(" · ") : null;
}

/**
 * Kaydın ne olduğunu anlatan tek cümle — döndürme kayıtları için ŞART.
 *
 * Döndürme (`gunluk_dondu`) bir istek değildir: metodu, yolu ve durum kodu
 * yoktur. Tabloda boş hücrelerle görünseydi okuyan kişi bozuk bir satır
 * sanardı; oysa cevapladığı soru tam da "kayıt kayboldu mu"dur.
 */
export function dondurmeCumlesi(kayit: GunlukKaydi): string | null {
  if (kayit.olay !== "gunluk_dondu") return null;
  const tasinan = kayit.tasinan_dosya
    ? `Eski kayıtlar ${kayit.tasinan_dosya} dosyasına taşındı.`
    : "Eski kayıtlar saklanmadı.";
  const silinen = kayit.silinen_dosya
    ? ` En eski kuşak (${kayit.silinen_dosya}) silindi.`
    : "";
  const boyut =
    typeof kayit.bayt === "number"
      ? ` Dosya ${trNum(Math.round(kayit.bayt / 1024))} KB sınırına ulaşmıştı.`
      : "";
  return `Günlük döndürüldü. ${tasinan}${silinen}${boyut}`;
}

/** Süzgeç durumu — panelin tek kaynağı, sorgu bundan türetilir. */
export type GunlukSuzgec = {
  yalnizYazanlar: boolean;
  metot: string;
  yol: string;
  baslangic: string;
  bitis: string;
};

export const BOS_SUZGEC: GunlukSuzgec = {
  yalnizYazanlar: true,
  metot: "",
  yol: "",
  baslangic: "",
  bitis: "",
};

/** Süzgeçten en az biri etkin mi (boş-hâl metni buna göre değişir). */
export function suzgecEtkin(s: GunlukSuzgec): boolean {
  return Boolean(s.metot || s.yol.trim() || s.baslangic || s.bitis);
}

/**
 * Süzgeç + sayfa → sunucu parametreleri.
 *
 * Boş alanlar HİÇ gönderilmez: `metot=""` sunucuda "metodu boş olan kayıt"
 * anlamına gelebilirdi ve süzgeç sessizce her şeyi eleyebilirdi.
 */
export function sorguParametreleri(
  s: GunlukSuzgec,
  sayfa: { limit: number; offset: number },
): Record<string, string | number | boolean> {
  const p: Record<string, string | number | boolean> = {
    yalniz_yazanlar: s.yalnizYazanlar,
    limit: sayfa.limit,
    offset: sayfa.offset,
  };
  if (s.metot) p.metot = s.metot;
  if (s.yol.trim()) p.yol = s.yol.trim();
  if (s.baslangic) p.baslangic = s.baslangic;
  if (s.bitis) p.bitis = s.bitis;
  return p;
}
