"use client";

/**
 * Jüri / geliştirici modu — kalıcı bir görünürlük anahtarı.
 *
 * İlgili: ../components/JuryModeToggle.tsx, ../components/ComparePanel.tsx
 *
 * NEDEN VAR: güven skoru bir DENETİM sinyalidir, bir ürün rozeti değil. Kıyas
 * tablosunda her satırın yanında duran «0,62 orta» çubuğu, bilgiyi arayan bir
 * müşteriye ticari bir kalite iddiası gibi görünüyor — oysa skor kalibre
 * edilmemiştir (bkz. src/extraction/rules/confidence.py). Jüri ve geliştirici
 * ise tam tersine bu skoru GÖRMEK zorundadır.
 *
 * Çözüm: skoru kaldırmak değil, izleyiciye göre açmak. Mod KAPALIYKEN yalnız
 * kıyas tablosundaki rozet gizlenir; Jüri Audit Paneli, Canlı Çıkarım ve
 * Şeffaf Skorlama zaten denetim yüzeyleridir ve HER HÂLDE gösterirler.
 *
 * Nasıl açılır (üçü de aynı yere yazar):
 *   1. Sağ üstteki «Jüri modu» düğmesi,
 *   2. Adres satırına `?juri=1` eklemek,
 *   3. Bir kez açıldıktan sonra kendiliğinden (localStorage) — sekme
 *      kapansa da açık kalır.
 *
 * Ortam değişkenine (NEXT_PUBLIC_*) BİLEREK bağlanmadı: demo makinesinde
 * derleme zamanı değişkeni ayarlanmamış olabilir ve o durumda mod hiçbir
 * şekilde açılamaz. URL + localStorage her makinede çalışır.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

const STORAGE_KEY = "anatolia.juri-modu";
const URL_PARAM = "juri";

type JuryModeValue = {
  /** Jüri/geliştirici modu açık mı. */
  jury: boolean;
  setJury: (value: boolean) => void;
  /** İstemci tarafı okuma tamamlandı mı (hidrasyon uyuşmazlığını önler). */
  ready: boolean;
};

const JuryModeContext = createContext<JuryModeValue>({
  jury: false,
  setJury: () => {},
  ready: false,
});

function readInitial(): boolean {
  try {
    // URL parametresi localStorage'ı EZER: jüriye gönderilen bağlantı,
    // tarayıcıda daha önce ne yapıldığından bağımsız olarak açık gelmeli.
    const param = new URLSearchParams(window.location.search).get(URL_PARAM);
    if (param !== null) return param !== "0" && param !== "false";
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    // localStorage kapalı olabilir (gizli sekme / katı gizlilik ayarı).
    return false;
  }
}

export function JuryModeProvider({ children }: { children: ReactNode }) {
  // Sunucu ve ilk istemci render'ı AYNI olmalı → başlangıç her zaman kapalı,
  // gerçek değer mount sonrası okunur.
  const [jury, setJuryState] = useState(false);
  const [ready, setReady] = useState(false);

  const persist = useCallback((value: boolean) => {
    try {
      window.localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
    } catch {
      /* depolama yoksa mod yalnız bu sekmede yaşar — çökme sebebi değil */
    }
    try {
      const url = new URL(window.location.href);
      if (value) url.searchParams.set(URL_PARAM, "1");
      else url.searchParams.delete(URL_PARAM);
      window.history.replaceState(null, "", url.toString());
    } catch {
      /* adres çubuğu güncellenemedi — işlevsel bir kayıp değil */
    }
  }, []);

  useEffect(() => {
    const initial = readInitial();
    setJuryState(initial);
    // `?juri=1` ile gelindiyse kalıcılaştır: jüri sekmeler arasında gezerken
    // modun kendiliğinden kapanması en can sıkıcı arıza olurdu.
    persist(initial);
    setReady(true);
  }, [persist]);

  const setJury = useCallback(
    (value: boolean) => {
      setJuryState(value);
      persist(value);
    },
    [persist],
  );

  const value = useMemo<JuryModeValue>(
    () => ({ jury, setJury, ready }),
    [jury, setJury, ready],
  );

  return (
    <JuryModeContext.Provider value={value}>{children}</JuryModeContext.Provider>
  );
}

export function useJuryMode(): JuryModeValue {
  return useContext(JuryModeContext);
}
