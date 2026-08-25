"use client";

/**
 * Sunum modu — tek tuşla tam ekran + araç çubuğu sadeleştirme.
 *
 * İlgili: ../styles/sunum.css, ../components/SunumToggle.tsx,
 *         ./tema.tsx (aynı `data-*` niteliği deseni, farklı gerekçe)
 *
 * ## Neden kalıcı DEĞİL (tema/jüri modunun tersi)
 *
 * `tema.tsx` ve `juryMode.tsx` seçimi `localStorage`'a yazar çünkü ikisi de
 * kalıcı bir TERCİH. Sunum modu tam tersi: bir demo ANI. Bir önceki oturumdan
 * kalıp bir sonraki açılışta sessizce tam ekrana geçmek veya araç çubuğunu
 * gizli tutmak, ekibi kendi panelinde şaşırtırdı. Bu yüzden başlangıç değeri
 * her zaman `false` ve hiçbir depoya yazılmaz — bu da `tema.tsx`'in
 * `hazir` kapısını (hidrasyon uyuşmazlığını önlemek için) gereksiz kılar:
 * sunucu ve istemcinin ilk render'ı zaten aynı (`false`).
 *
 * ## Neden tam ekran + nitelik BİRLİKTE
 *
 * Tam ekran API'si (`requestFullscreen`) kullanıcı jestine bağlıdır ve bazı
 * bağlamlarda (iframe, izin reddi) sessizce reddedilebilir — bu yüzden
 * `catch(() => {})` ile yutuluyor. Ret olsa da araç çubuğu sadeleştirmesi
 * (`data-sunum` niteliği → sunum.css) çalışmaya devam eder; ikisi bağımsız
 * kanallar, biri diğerini engellemez.
 *
 * ## Esc ile çıkış senkronize edilir
 *
 * Tarayıcı tam ekrandan Esc ile çıkarıldığında `fullscreenchange` olayı
 * dinlenip anahtar `false`e döner. Aksi hâlde düğme «Sunumdan Çık» yazmaya
 * devam eder ama artık tam ekranda değildir — anahtar YALAN söylerdi.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

const NITELIK = "data-sunum";

type SunumDegeri = {
  acik: boolean;
  degistir: () => void;
};

const SunumContext = createContext<SunumDegeri>({
  acik: false,
  degistir: () => {},
});

export function SunumProvider({ children }: { children: ReactNode }) {
  const [acik, setAcik] = useState(false);

  useEffect(() => {
    const kok = document.documentElement;
    if (acik) kok.setAttribute(NITELIK, "acik");
    else kok.removeAttribute(NITELIK);
  }, [acik]);

  useEffect(() => {
    function senkronla() {
      if (!document.fullscreenElement) setAcik(false);
    }
    document.addEventListener("fullscreenchange", senkronla);
    return () => document.removeEventListener("fullscreenchange", senkronla);
  }, []);

  const degistir = useCallback(() => {
    setAcik((onceki) => {
      const yeni = !onceki;
      if (yeni) {
        document.documentElement.requestFullscreen?.().catch(() => {});
      } else if (document.fullscreenElement) {
        document.exitFullscreen?.().catch(() => {});
      }
      return yeni;
    });
  }, []);

  return (
    <SunumContext.Provider value={{ acik, degistir }}>
      {children}
    </SunumContext.Provider>
  );
}

export function useSunum(): SunumDegeri {
  return useContext(SunumContext);
}
