"use client";

/**
 * Grafik iskeleti — palet çözülene kadar yer tutar.
 *
 * İlgili: ../../lib/grafikPaleti.ts, ./KiyasCubuklari.tsx, ./RadarKiyas.tsx
 *
 * Canvas grafikleri paleti `getComputedStyle` ile okur ve bu okuma mount
 * ÖNCESİ yapılamaz (sunucuda `document` yok; hidrasyon disiplini için bkz.
 * lib/grafikPaleti.ts). O hâlde `useGrafikPaleti()` `null` döner ve grafik
 * bileşenleri hiçbir şey çizmez.
 *
 * «Hiçbir şey» görünürde bir sorun değil ama ölçülebilir bir kusur üretiyor:
 * grafik bir kare sonra belirdiğinde altındaki tablo aşağı sıçrıyor ve
 * kullanıcı okumaya başladığı satırı kaybediyor. Bu bileşen o boşluğu önden
 * ayırır ve palet çözülür çözülmez kendini siler.
 *
 * Ekran okuyucuya `aria-hidden`: yer tutan boş bir kutunun duyurulacak hiçbir
 * içeriği yok, «yükleniyor» demek de yanlış olurdu — veri çoktan geldi, çizilen
 * yalnız renk bekliyor.
 */

import { useGrafikPaleti } from "../../lib/grafikPaleti";

type Props = {
  /** Ayrılacak yükseklik (px) — çizilecek grafiğinkiyle aynı olmalı. */
  yukseklik?: number;
};

export default function GrafikIskeleti({ yukseklik = 220 }: Props) {
  const palet = useGrafikPaleti();
  if (palet) return null;
  return (
    <div
      className="grafik-iskelet"
      style={{ height: yukseklik }}
      aria-hidden="true"
    />
  );
}
