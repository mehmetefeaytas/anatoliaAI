"use client";

/**
 * Grafik paleti — canvas'ın okuyamadığı tokenları okuyup ona taşır.
 *
 * İlgili: ./tema.tsx, ../styles/tokens.css, ../components/grafik/*
 *         CLAUDE.md §1 (offline), §7 (Next.js + React)
 *
 * ## Neden bu dosya var
 *
 * Kıyas ekranı grafik ağırlıklı hâle geldi ve çubuk/radar grafikleri Chart.js
 * ile, yani CANVAS üzerine çiziliyor. Canvas bir DOM ağacı değildir: içine
 * `fill="var(--accent)"` yazılamaz, CSS özel nitelikleri oraya kaskatlanmaz.
 * Renkler JavaScript'te ÇÖZÜLMÜŞ hâlleriyle verilmek zorunda.
 *
 * Bu dosya o çözme işini tek yerde yapar. Kural: hiçbir grafik yapılandırmasında
 * düz bir renk kodu bulunmaz — hepsi buradan gelir. Böylece değerler
 * `scripts/kontrast_kontrol.py`'nin ölçtüğü paletin içinde kalır. (Kapı
 * canvas piksellerini GÖREMEZ; bkz. aşağıdaki uyarı.)
 *
 * ## Tuzak: tema bağlamına abone olmak YETMEZ
 *
 * `tema.tsx` bilinçli olarak şunu savunuyor ve CSS için tamamen haklı:
 *
 *   «Sistem hâlinde JavaScript'in dinlemesi GEREKMEZ: nitelik kaldırıldığında
 *   karar tümüyle `prefers-color-scheme` medya sorgusuna döner… Bir
 *   `matchMedia` dinleyicisi burada aynı işi ikinci kez, daha kırılgan
 *   biçimde yapardı.»
 *
 * Canvas için bu ters yönde ısırıyor. `tema === "sistem"` iken işletim sistemi
 * koyuya geçtiğinde HİÇBİR React durumu değişmez: CSS sessizce yeniden boyanır,
 * sayfa dönüşür, ama her canvas eski paletiyle ekranda kalır — açık temanın
 * koyu zemine çizilmiş çubukları olarak.
 *
 * Yani canvas, o dosyanın gerekçeyle reddettiği dinleyiciyi geri getirtiyor.
 * Bu bilinçli bir İSTİSNADIR ve kapsamı dar tutuldu: dinleyici yalnız
 * `tema === "sistem"` iken kuruluyor (diğer iki hâlde karar zaten React
 * durumunda, dinlemeye gerek yok) ve tek iş yapıyor — yeniden okuma tetiklemek.
 *
 * ## Hidrasyon
 *
 * `getComputedStyle` render sırasında ÇAĞRILAMAZ: sunucuda `document` yoktur ve
 * projenin hidrasyon disiplini (bkz. `tema.tsx`, `juryMode.tsx`) sunucu ile ilk
 * istemci render'ının aynı olmasını şart koşar. Bu yüzden palet mount öncesi
 * `null`'dur ve çağıran bileşen o hâlde grafiği çizmez, iskelet gösterir.
 *
 * ## Kontrast kapısı bu renkleri ÖLÇMÜYOR
 *
 * `kontrast_kontrol.py` `tokens.css`'i ayrıştırıp `CIFTLER`'deki sabit çiftleri
 * ölçer. Canvas çıktısı erişilebilirlik ağacında hiç yoktur — ne o betik, ne
 * axe, ne Lighthouse görebilir. İki sonuç:
 *
 *  1. Değerlerin ölçülmüş palette kalması için buradaki token adları
 *     `tokens.css`'te TANIMLI olmak zorunda; uydurma ad sessizce boş dize
 *     döndürür (bu yüzden `_zorunlu` boş değeri yakalar).
 *  2. Seri dolguları METİN DEĞİLDİR: WCAG 2.1 1.4.11 onlar için 3:1 ister,
 *     4,5:1 değil. Betikte 3:1 kipi yok. Bu yüzden renk ASLA tek sinyal
 *     olmayacak — değer çubuğun içine basılır, eksik veri kesikli boş hücreyle
 *     gösterilir (1.4.1).
 */

import { useEffect, useState } from "react";
import { useTema } from "./tema";

/**
 * Grafiklerin kullandığı token kümesi.
 *
 * Liste bilinçli olarak DAR: her eklenen ad, kontrast kapısının göremediği bir
 * yüzeye bir renk daha taşır. Yeni bir ad eklenirken `scripts/kontrast_kontrol.py`
 * içindeki `CIFTLER` listesine de ilgili çift eklenmeli.
 */
const TOKENLAR = [
  "--accent",
  "--accent-soft",
  "--accent-wash",
  "--ok",
  "--ok-wash",
  "--warn",
  "--warn-wash",
  "--bad",
  "--bad-wash",
  "--fg",
  "--fg-dim",
  "--fg-faint",
  "--line",
  "--line-soft",
  "--bg",
  "--bg-2",
  "--bg-3",
  "--font-sans",
  "--font-mono",
] as const;

export type GrafikPaleti = Record<(typeof TOKENLAR)[number], string>;

/**
 * Tek bir tokenı çözer.
 *
 * Tanımsız ad boş dize döndürür ve bu SESSİZ bir hatadır: Chart.js boş rengi
 * saydam sayar, yani grafik "çalışır" ama görünmez çizer. Boş değer burada
 * yakalanıp konsola yazılır; üretimde çökertmiyoruz çünkü eksik bir çubuk
 * rengi, jüri demosunu durdurmaya değmez.
 */
function tokenOku(kok: CSSStyleDeclaration, ad: string): string {
  const deger = kok.getPropertyValue(ad).trim();
  if (!deger && process.env.NODE_ENV !== "production") {
    // eslint-disable-next-line no-console
    console.warn(`grafikPaleti: "${ad}" tokens.css'te tanımlı değil`);
  }
  return deger;
}

function paletiOku(): GrafikPaleti {
  const kok = getComputedStyle(document.documentElement);
  const palet = {} as GrafikPaleti;
  for (const ad of TOKENLAR) palet[ad] = tokenOku(kok, ad);
  return palet;
}

/**
 * Çözülmüş grafik paleti. Mount öncesi `null` — çağıran o hâlde iskelet çizer.
 *
 * Yeniden okuma iki olayda tetiklenir:
 *  - `tema` değişince (kullanıcı açık/koyu/sistem seçti)
 *  - `tema === "sistem"` iken işletim sistemi görünümü değişince
 *
 * İkincisi için dinleyici gereklidir; gerekçesi dosya başlığında.
 */
export function useGrafikPaleti(): GrafikPaleti | null {
  const { tema } = useTema();
  const [palet, setPalet] = useState<GrafikPaleti | null>(null);

  // Sistem hâlinde işletim sistemi görünümü değişince React'e haber verecek
  // tek sinyal budur — nitelik değişmediği için `tema` sabit kalır.
  const [nesil, setNesil] = useState(0);

  useEffect(() => {
    if (tema !== "sistem") return;
    const sorgu = window.matchMedia("(prefers-color-scheme: dark)");
    const degisti = () => setNesil((n) => n + 1);
    sorgu.addEventListener("change", degisti);
    return () => sorgu.removeEventListener("change", degisti);
  }, [tema]);

  useEffect(() => {
    // `tema.tsx` niteliği kendi `useEffect`'inde uyguluyor. Aynı turda okursak
    // bir önceki paleti okuma riski var; okuma bir sonraki kareye bırakılıyor.
    const kare = requestAnimationFrame(() => setPalet(paletiOku()));
    return () => cancelAnimationFrame(kare);
  }, [tema, nesil]);

  return palet;
}
