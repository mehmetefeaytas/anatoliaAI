"use client";

/**
 * Belgeyi yazdır / PDF olarak kaydet.
 *
 * İlgili: ../styles/baski.css, ./AuditPanel.tsx, ./SourceText.tsx
 *
 * ## Neden bir kütüphane değil
 *
 * Gerekçenin tamamı `styles/baski.css` başlığında; özeti: jsPDF'in standart
 * fontları ASCII ile sınırlı ve Türkçe metni varsayılan olarak bozuyor,
 * html2pdf DOM'u yeniden rasterize edip seçilemeyen bulanık metin üretiyor.
 * Tarayıcının kendi yolu metni ZATEN doğru fontla çiziyor.
 *
 * ## Etiket neden «yazdır» diyor
 *
 * Düğme bir dosya İNDİRMİYOR. Tarayıcının yazdırma penceresini açıyor;
 * kullanıcı orada hedef olarak «PDF olarak kaydet»i seçiyor. Etiketi
 * «PDF indir» yapmak, tek tıkta dosya bekleyen kullanıcıyı yanıltırdı —
 * kaldırılan «tekrar dene» vaadiyle aynı hata sınıfı.
 *
 * Dosya adı programatik olarak ATANAMAZ; tarayıcı onu sayfa başlığından
 * türetir. Bu yüzden başlık çağrıdan önce geçici olarak değiştirilip sonra
 * geri konuyor: kullanıcıya «anatolia-ai-belge-1421.pdf» önerilir,
 * «localhost:3000» değil.
 */

import { useCallback } from "react";

type Props = {
  /** Dosya adının gövdesi — belge numarası, banka adı vb. */
  ad: string;
  etiket?: string;
};

/** Dosya adı için güvenli slug: Türkçe harfler sadeleşir, boşluk tireye döner. */
function slug(ham: string): string {
  const harita: Record<string, string> = {
    ş: "s", Ş: "s", ç: "c", Ç: "c", ğ: "g", Ğ: "g",
    ı: "i", İ: "i", ö: "o", Ö: "o", ü: "u", Ü: "u", â: "a", î: "i", û: "u",
  };
  return ham
    .split("")
    .map((h) => harita[h] ?? h)
    .join("")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 60);
}

export default function BelgeyiIndir({ ad, etiket }: Props) {
  const yazdir = useCallback(() => {
    const eskiBaslik = document.title;
    document.title = `anatolia-ai-${slug(ad)}`;
    // Başlık HEMEN geri konulamaz: Chrome adı yazdırma penceresi açılırken
    // okur ve senkron `print()` dönüşünde pencere hâlâ açık olabilir. Geri
    // koyma bir sonraki olay turuna bırakılıyor.
    try {
      window.print();
    } finally {
      setTimeout(() => {
        document.title = eskiBaslik;
      }, 0);
    }
  }, [ad]);

  return (
    <button type="button" className="btn-ghost baski-gizle" onClick={yazdir}>
      {etiket ?? "Yazdır / PDF olarak kaydet"}
    </button>
  );
}
