"use client";

/**
 * Sekme durumu — adres çubuğunda yaşar, `useState`'te değil.
 *
 * İlgili: ../page.tsx, ./juryMode.tsx (aynı URL deseni, farklı amaç)
 *
 * ## Neden
 *
 * Sekme eskiden yalnız `useState<TabKey>` idi. Üç somut sonucu vardı:
 * jüri bir ekranı paylaşamıyordu (bağlantı her zaman ilk sekmeyi açıyordu),
 * tarayıcının geri tuşu sekmeler arasında çalışmıyordu ve sayfa yenilenince
 * çalışılan ekran kayboluyordu. Dördüncüsü sunum sırasında en can sıkıcısı:
 * yanlışlıkla yenilenen bir sayfa demoyu başa sarıyordu.
 *
 * ## juryMode'dan farkı: pushState
 *
 * `juryMode` bir TERCİHtir ve `replaceState` kullanır — geri tuşuyla tercih
 * değiştirmek beklenmez. Sekme ise bir KONUMdur; `pushState` ile geçmişe
 * yazılır ve `popstate` dinlenir, böylece geri tuşu bir önceki sekmeye döner.
 *
 * ## Hidrasyon
 *
 * Sunucu ve ilk istemci render'ı AYNI olmak zorundadır, bu yüzden başlangıç
 * değeri her zaman `varsayilan`dır; gerçek değer mount sonrası okunur.
 * `hazir` bayrağı, okumanın tamamlandığını bildirir.
 */

import { useCallback, useEffect, useState } from "react";

const URL_PARAM = "sekme";

/** URL'den geçerli bir sekme anahtarı okur; tanınmayan değeri yok sayar. */
function urldenOku<T extends string>(gecerli: readonly T[]): T | null {
  try {
    const ham = new URLSearchParams(window.location.search).get(URL_PARAM);
    return ham && (gecerli as readonly string[]).includes(ham) ? (ham as T) : null;
  } catch {
    return null;
  }
}

export type SekmeDurumu<T extends string> = {
  sekme: T;
  setSekme: (deger: T) => void;
  /** İstemci tarafı okuma tamamlandı mı (hidrasyon uyuşmazlığını önler). */
  hazir: boolean;
};

export function useTabState<T extends string>(
  gecerliSekmeler: readonly T[],
  varsayilan: T,
): SekmeDurumu<T> {
  const [sekme, setSekmeState] = useState<T>(varsayilan);
  const [hazir, setHazir] = useState(false);

  // Mount: URL'de sekme varsa onu aç. Yoksa varsayılanda kal ve adres
  // çubuğunu KİRLETME — `?sekme=compare` yazmak paylaşılan bağlantıyı
  // gereksiz uzatır.
  useEffect(() => {
    const bulunan = urldenOku(gecerliSekmeler);
    if (bulunan) setSekmeState(bulunan);
    setHazir(true);
  }, [gecerliSekmeler]);

  // Geri/ileri tuşu: URL değişince durumu ona uydur.
  useEffect(() => {
    function geriIleri() {
      setSekmeState(urldenOku(gecerliSekmeler) ?? varsayilan);
    }
    window.addEventListener("popstate", geriIleri);
    return () => window.removeEventListener("popstate", geriIleri);
  }, [gecerliSekmeler, varsayilan]);

  const setSekme = useCallback(
    (deger: T) => {
      setSekmeState(deger);
      try {
        const url = new URL(window.location.href);
        if (deger === varsayilan) url.searchParams.delete(URL_PARAM);
        else url.searchParams.set(URL_PARAM, deger);
        // Aynı sekmeye tekrar tıklamak geçmişe yeni kayıt EKLEMEZ; aksi hâlde
        // geri tuşu aynı ekranda saplanıp kalırdı.
        if (url.toString() !== window.location.href) {
          window.history.pushState(null, "", url.toString());
        }
      } catch {
        /* adres çubuğu güncellenemedi — sekme yine de değişti */
      }
    },
    [varsayilan],
  );

  return { sekme, setSekme, hazir };
}
