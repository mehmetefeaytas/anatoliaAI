"use client";

/**
 * Sunum turu anlatım şeridi — sunum modu AÇIKKEN, tur adımları ilerlerken.
 *
 * İlgili: ../page.tsx (`TUR_ADIMLARI`, tur durumu makinesi), ../styles/sunum.css
 *
 * Yalnız bilgi verir, hiçbir kontrol taşımaz: durdurma tek yolu araç
 * çubuğundaki «Sunumdan Çık» (bkz. SunumToggle.tsx) — burada ikinci bir
 * durdurma düğmesi açmak aynı eylemi iki farklı yerde tekrarlardı.
 *
 * `role="status"` + `aria-live="polite"`: adım değiştiğinde ekran okuyucu
 * yeni başlığı otomatik duyurur, kullanıcı şeride odaklanmak zorunda kalmaz.
 */

type Props = {
  baslik: string;
  aciklama: string;
  adimNo: number;
  toplamAdim: number;
};

export default function SunumTuruBandi({
  baslik,
  aciklama,
  adimNo,
  toplamAdim,
}: Props) {
  return (
    <div className="sunum-turu-bandi" role="status" aria-live="polite">
      <span className="sunum-turu-adim">
        {adimNo}/{toplamAdim}
      </span>
      <span className="sunum-turu-baslik">{baslik}</span>
      <p className="sunum-turu-aciklama">{aciklama}</p>
    </div>
  );
}
