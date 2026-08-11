"use client";

/**
 * Tema seçimi — sistem / açık / koyu.
 *
 * İlgili: ../styles/tema.css (paletin üçüncü hâli), ../styles/tokens.css,
 *         ../components/TemaSecici.tsx, ./juryMode.tsx (aynı hidrasyon deseni)
 *
 * ## Neden üç hâl, iki değil
 *
 * Bir anahtar (açık ⇄ koyu) kurmak daha kısa olurdu ama SİSTEM hâlini yok
 * ederdi: kullanıcı bir kez dokunduktan sonra işletim sistemi teması artık
 * hiçbir şey ifade etmez, akşam karanlığa geçen bir makinede panel gündüz
 * hâlinde kalırdı. Üçüncü hâl «seçmedim, sen bak» demenin yoludur ve
 * varsayılan odur.
 *
 * Sistem hâlinde JavaScript'in dinlemesi GEREKMEZ: nitelik kaldırıldığında
 * karar tümüyle `prefers-color-scheme` medya sorgusuna döner, yani işletim
 * sistemi teması değişince sayfa kendiliğinden dönüşür. Bir `matchMedia`
 * dinleyicisi burada aynı işi ikinci kez, daha kırılgan biçimde yapardı.
 *
 * ## Hidrasyon
 *
 * Sunucu ve ilk istemci render'ı AYNI olmak zorundadır (Next.js sunucuda
 * render ediyor). Bu yüzden depo render sırasında DEĞİL, `useEffect` içinde
 * okunur ve başlangıç değeri her zaman «sistem»dir — `juryMode.tsx` ile
 * birebir aynı desen.
 *
 * Bunun bilinen bedeli, seçimin sistemle ÇELİŞTİĞİ durumda ilk karede kısa
 * bir sistem teması görünmesidir (koyu sistemde «açık» seçen kullanıcı bir
 * kare koyu görür). Bedeli ödemeyi seçtik: alternatif, `<head>`e engelleyici
 * bir betik gömüp React'in hidrasyon uyarısını bastırmaktır — sayfanın
 * sunucu çıktısıyla istemci çıktısı arasındaki farkı SUSTURAN bir ayar, yani
 * bu tek sorunu çözerken başka her uyuşmazlığı da görünmez kılan bir kaldıraç.
 * Bir karelik geçiş, gizlenmiş bir sınıf uyuşmazlığından ucuzdur.
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

const KAYIT_ANAHTARI = "anatolia.tema";
const NITELIK = "data-tema";

/** Seçilebilir tema hâlleri. «sistem» varsayılandır. */
export type Tema = "sistem" | "acik" | "koyu";

export const TEMALAR: readonly { deger: Tema; etiket: string; ipucu: string }[] = [
  {
    deger: "sistem",
    etiket: "Sistem",
    ipucu: "Cihazın görünüm ayarını izler; ayar değişince panel de değişir",
  },
  { deger: "acik", etiket: "Açık", ipucu: "Cihaz ayarından bağımsız açık tema" },
  { deger: "koyu", etiket: "Koyu", ipucu: "Cihaz ayarından bağımsız koyu tema" },
] as const;

type TemaDegeri = {
  tema: Tema;
  setTema: (deger: Tema) => void;
  /** İstemci tarafı okuma tamamlandı mı (hidrasyon uyuşmazlığını önler). */
  hazir: boolean;
};

const TemaContext = createContext<TemaDegeri>({
  tema: "sistem",
  setTema: () => {},
  hazir: false,
});

/** Depodan gelen değeri doğrular. Tanınmayan değer «sistem» sayılır. */
function temaCoz(ham: unknown): Tema {
  return ham === "acik" || ham === "koyu" ? ham : "sistem";
}

function oku(): Tema {
  try {
    return temaCoz(window.localStorage.getItem(KAYIT_ANAHTARI));
  } catch {
    // Depo kapalı olabilir (gizli sekme / katı gizlilik ayarı).
    return "sistem";
  }
}

/**
 * Seçimi belgeye uygular.
 *
 * «sistem» hâlinde nitelik SİLİNİR, boş bir değere ayarlanmaz: karar medya
 * sorgusuna geri dönmelidir, üçüncü bir seçici hâline değil.
 */
function uygula(tema: Tema): void {
  const kok = document.documentElement;
  if (tema === "sistem") kok.removeAttribute(NITELIK);
  else kok.setAttribute(NITELIK, tema);
}

export function TemaProvider({ children }: { children: ReactNode }) {
  // Sunucu ve ilk istemci render'ı AYNI olmalı → başlangıç her zaman «sistem»,
  // gerçek değer mount sonrası okunur.
  const [tema, setTemaState] = useState<Tema>("sistem");
  const [hazir, setHazir] = useState(false);

  useEffect(() => {
    const kayitli = oku();
    setTemaState(kayitli);
    uygula(kayitli);
    setHazir(true);
  }, []);

  const setTema = useCallback((deger: Tema) => {
    setTemaState(deger);
    uygula(deger);
    try {
      // «sistem» de SAKLANIR. Kaydı silmek, kullanıcının koyu temadan bilinçle
      // sisteme dönüşünü «hiç seçim yapmamış» hâline eşitlerdi; iki durum
      // bugün aynı görünüyor olsa da aynı şey değildir.
      window.localStorage.setItem(KAYIT_ANAHTARI, deger);
    } catch {
      /* depo yoksa seçim yalnız bu sekmede yaşar — çökme sebebi değil */
    }
  }, []);

  const deger = useMemo<TemaDegeri>(
    () => ({ tema, setTema, hazir }),
    [tema, setTema, hazir],
  );

  return <TemaContext.Provider value={deger}>{children}</TemaContext.Provider>;
}

export function useTema(): TemaDegeri {
  return useContext(TemaContext);
}
