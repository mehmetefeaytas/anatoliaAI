"use client";

/**
 * Grafik iskeleti — palet çözülene kadar yer tutar.
 *
 * İlgili: ../../lib/grafikPaleti.ts, ./KapsamaCetveli.tsx,
 *         ../../styles/cetvel.css
 *
 * Bu dosya İKİ ayrı bekleyişi karşılar ve ikisinin sebebi farklıdır.
 *
 * ## 1) Canvas grafikleri: PALET bekler
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
 *
 * ## 2) Kapsama cetveli: VERİ bekler, palet beklemez
 *
 * `KapsamaCetveli` saf DOM + CSS'tir; paletle hiç işi yoktur, `/compare`
 * yanıtını bekler. `bankalar` verildiğinde bu bileşen o bekleyişin iskeletini
 * çizer ve kural şudur: **banka adları ve satır sayısı hemen basılır, yalnız
 * çubuklar bekler.**
 *
 * Yükleme sırasında hiçbir sayı, hiçbir sıra numarası ve hiçbir animasyonlu
 * sayaç görünmez. Sebep: yükleme anında ekranda duran bir rakam bir sonraki
 * karede değişecek demektir ve okunmuş bir yanlış, okunmamış bir doğrudan
 * kötüdür. Sıra numarası da yok — sıralama henüz YAPILMADI, yer tutucu bir «1»
 * o an var olmayan bir iddiayı basardı.
 *
 * İskelet `aria-hidden` DEĞİLDİR bu kez: basılan banka adları gerçek
 * içeriktir ve satır sayısı gerçek bir bilgidir. Bekleyen kısım
 * `aria-busy` ile duyurulur.
 */

import { useGrafikPaleti } from "../../lib/grafikPaleti";

type Props = {
  /** Ayrılacak yükseklik (px) — çizilecek grafiğinkiyle aynı olmalı. */
  yukseklik?: number;
  /**
   * Cetvel iskeleti için banka adları. Verildiğinde palet BEKLENMEZ: cetvel
   * canvas değil, bekleyen şey veri. Boş/verilmemişse eski (nötr kutu)
   * davranış sürer.
   */
  bankalar?: string[];
};

export default function GrafikIskeleti({ yukseklik = 220, bankalar }: Props) {
  const palet = useGrafikPaleti();

  if (bankalar && bankalar.length > 0) {
    return (
      <div className="cetvel-iskelet" aria-busy="true">
        {bankalar.map((ad) => (
          <div className="cetvel-iskelet-satir" key={ad}>
            <span className="cetvel-iskelet-ad">{ad}</span>
            {/* Çubuğun YERİ ayrılır, çubuk çizilmez: uzunluğu her satırda aynı,
                yani bir büyüklük iddiası taşımıyor. */}
            <div className="cetvel-iskelet-ray" aria-hidden="true" />
          </div>
        ))}
      </div>
    );
  }

  if (palet) return null;
  return (
    <div
      className="grafik-iskelet"
      style={{ height: yukseklik }}
      aria-hidden="true"
    />
  );
}
