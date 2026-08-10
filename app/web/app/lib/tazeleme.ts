/**
 * Veri tazeleme ekranının SAF yardımcıları — süre, ilerleme, özet cümlesi.
 *
 * İlgili: ../components/TazelemePanel.tsx, ./api.ts, ../../tests/tazeleme.test.ts
 *
 * Neden ayrı dosya: bu mantık bir React bileşeninin içinde kalsaydı ancak
 * tarayıcıda gözle sınanabilirdi. Yeni bir test bağımlılığı (jsdom, testing
 * library) eklemek offline/lisans kısıtı yüzünden söz konusu değil; saf
 * fonksiyonlar ise Node'un yerleşik koşucusuyla sınanabiliyor.
 *
 * Buradaki her metin kullanıcıya gösterilir, dolayısıyla Türkçedir.
 */

import type { RefreshDurum, RefreshJob, RefreshPreview } from "./api";

/** Saniyeyi okunur Türkçe süreye çevirir ("2 dk 30 sn", "45 sn"). */
export function sureMetni(saniye: number): string {
  const sn = Math.max(0, Math.round(saniye));
  if (sn < 60) return `${sn} sn`;
  const dk = Math.floor(sn / 60);
  const kalan = sn % 60;
  if (dk < 60) return kalan === 0 ? `${dk} dk` : `${dk} dk ${kalan} sn`;
  const saat = Math.floor(dk / 60);
  const dkKalan = dk % 60;
  return dkKalan === 0 ? `${saat} sa` : `${saat} sa ${dkKalan} dk`;
}

/** Ön izlemedeki alt–üst süre tahminini tek aralık cümlesine indirir. */
export function tahminiSure(onizleme: RefreshPreview): string {
  const alt = sureMetni(onizleme.tahmini_sure_alt_sn);
  const ust = sureMetni(onizleme.tahmini_sure_ust_sn);
  return alt === ust ? alt : `${alt} – ${ust}`;
}

/** Ön izlemedeki alt–üst istek sayısını tek aralık cümlesine indirir. */
export function tahminiIstek(onizleme: RefreshPreview): string {
  const { tahmini_istek_alt: alt, tahmini_istek_ust: ust } = onizleme;
  return alt === ust ? `${alt} istek` : `${alt}–${ust} istek`;
}

/** Durum kodunun kullanıcıya gösterilen Türkçe adı. */
export function durumEtiketi(durum: RefreshDurum): string {
  switch (durum) {
    case "bekliyor":
      return "Sıraya alındı";
    case "kesif":
      return "Sayfalar aranıyor";
    case "cekiliyor":
      return "Belgeler çekiliyor";
    case "yaziliyor":
      return "Arşive yazılıyor";
    case "tamam":
      return "Tamamlandı";
    case "hata":
      return "Tamamlanamadı";
    case "iptal":
      return "Durduruldu";
    default:
      return durum;
  }
}

/** Durum koduna karşılık gelen bildirim sınıfı. */
export function durumBildirimSinifi(durum: RefreshDurum): string {
  if (durum === "tamam") return "notice notice-ok";
  if (durum === "hata") return "notice notice-error";
  if (durum === "iptal") return "notice notice-warn";
  return "notice notice-info";
}

/**
 * İlerleme oranı (0–1). Toplam bilinmiyorsa `null` döner — belirsiz bir
 * ilerlemeyi %0 diye göstermek, donmuş bir çubuk izlenimi verirdi.
 */
export function ilerlemeOrani(is: RefreshJob): number | null {
  if (is.bitti) return 1;
  if (!is.toplam) return null;
  return Math.min(1, Math.max(0, is.tamamlanan / is.toplam));
}

/**
 * Sonuç özeti — "kaç belge çekildi, kaçı yeni, kaçı değişti, kaçı hata verdi".
 *
 * Bitmemiş iş için `null` döner: yarım sayıları sonuç gibi basmak, koşu
 * sürerken yanlış bir tamamlanma izlenimi yaratır.
 */
export function sonucOzeti(is: RefreshJob): string | null {
  if (!is.bitti) return null;
  const parcalar = [
    `${is.cekilen} belge çekildi`,
    `${is.yeni} yeni`,
    `${is.degisen} değişti`,
    `${is.ayni} aynı kaldı`,
    `${is.hata} hata`,
  ];
  return parcalar.join(" · ");
}

/** Belge durumunun Türkçe rozet metni. */
export function belgeDurumEtiketi(durum: "yeni" | "degisen" | "ayni"): string {
  if (durum === "yeni") return "yeni";
  if (durum === "degisen") return "değişti";
  return "aynı";
}

/** Belge durumunun rozet sınıfı — değişiklik dikkat çeker, aynılık sessizdir. */
export function belgeDurumSinifi(durum: "yeni" | "degisen" | "ayni"): string {
  if (durum === "yeni") return "badge badge-ok";
  if (durum === "degisen") return "badge badge-warn";
  return "badge";
}

/**
 * Alınamayan bir adresin gerekçesini Türkçeleştirir.
 *
 * Sunucu bu alanı toplama katmanının kendi diliyle üretiyor; ham kodu
 * ekrana basmak jüriye hiçbir şey anlatmaz.
 */
export function hataGerekcesi(reason: string): string {
  if (reason === "robots disallow")
    return "Sitenin tarama kuralları bu adrese izin vermiyor";
  if (reason === "baglanti hatasi") return "Bağlantı kurulamadı";
  if (reason.startsWith("HTTP ")) return `Site ${reason.slice(5)} yanıtı verdi`;
  return reason;
}
