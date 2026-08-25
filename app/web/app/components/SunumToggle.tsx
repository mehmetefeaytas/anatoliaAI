"use client";

/**
 * Sunum modu düğmesi — tek tuş.
 *
 * İlgili: ../lib/sunum.tsx, ../styles/sunum.css
 *
 * `arac-cubugu` içinde `JuryModeToggle`/`TemaSecici` ile aynı yerde durur ama
 * sunum modu AÇIKKEN o ikisi gizlenir (`sunum.css`) — bu düğme GİZLENMEZ,
 * çünkü sunumdan çıkışın tek yolu odur. Sohbet/hesap makinesi FAB'ları da
 * bilerek gizlenmez: onlar demoda GÖSTERİLECEK ürün özellikleri, araç
 * çubuğunun geliştirici-yüzü anahtarlarıyla aynı kategori değil.
 *
 * Basılı hâl `.chip[aria-pressed="true"]` üzerinden zaten genel olarak
 * stillendiği için (`components.css`) ayrı bir görünüm sınıfı gerekmiyor —
 * `TemaSecici`nin `.tema-dugmesi`si gibi özel bir CSS'e ihtiyaç yok.
 */

import { useSunum } from "../lib/sunum";

export default function SunumToggle() {
  const { acik, degistir } = useSunum();

  return (
    <button
      type="button"
      className="chip"
      aria-pressed={acik}
      onClick={degistir}
      title={
        acik
          ? "Sunum modundan çık — tam ekrandan çıkar, jüri/tema anahtarlarını geri getirir"
          : "Tek tuşla sunum modu — tam ekrana geçer, jüri/tema anahtarlarını gizler"
      }
    >
      {acik ? "Sunumdan Çık" : "Sunum Modu"}
    </button>
  );
}
