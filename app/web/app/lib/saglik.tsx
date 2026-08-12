"use client";

/**
 * Sunucu sağlığı — «API kapalı» için TEK doğruluk kaynağı.
 *
 * İlgili: ./api.ts (`health`), ../components/DurumSeridi.tsx,
 *         ../components/ErrorNotice.tsx, CLAUDE.md §11 (demo stratejisi)
 *
 * ## Neden var
 *
 * Sunum sırasında sunucu düştü. Arayüzün o an yaptığı şey şuydu: her panel
 * kendi isteğini ayrı ayrı denedi, ayrı ayrı başarısız oldu ve ekranda BEŞ
 * AYRI KIRMIZI KUTU belirdi — hepsi aynı tek olayı anlatıyordu. Kullanıcı için
 * bu, beş ayrı arıza gibi okunur ve sistemin çöktüğü izlenimini verir.
 *
 * Tek bir yoklama, tek bir cevap: sağlık kırmızıysa kabukta TEK bir bant
 * durur, paneller kendi hata kutularını bastırır. Sistem çökmüş gibi değil,
 * zarif geri çekilmiş gibi görünür.
 *
 * ## Neden yoklama, olay değil
 *
 * Sunucudan istemciye bir kanal (SSE/WebSocket) kurmak, ayakta olduğunu
 * söyleyecek olan tarafın ayakta olmasını gerektirir — yani tam olarak
 * ölçmek istediğimiz şeyi varsayar. 15 saniyelik yoklama kaba ama doğru
 * yönde çalışıyor: ölü sunucu sessiz kalır ve sessizlik cevaptır.
 *
 * ## Hidrasyon
 *
 * İlk render'da durum her zaman «bilinmiyor»dur ve yoklama `useEffect` içinde
 * başlar — `tema.tsx` ve `juryMode.tsx` ile aynı desen. Sunucuda «API açık»
 * yazıp istemcide «kapalı» demek uyuşmazlık üretirdi.
 */

import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { api, type Health } from "./api";

/** İki yoklama arası. Kısaltmak sunucuya yük bindirir, uzatmak arızayı geciktirir. */
const ARALIK_MS = 15_000;

export type SaglikDurumu = {
  /** `null` = henüz yoklanmadı (ilk kare). */
  saglik: Health | null;
  /** Son yoklama başarısız mı — yani API'ye ULAŞILAMIYOR mu. */
  kapali: boolean;
  /** İlk yoklama tamamlandı mı (hidrasyon güvenliği). */
  hazir: boolean;
};

const SaglikContext = createContext<SaglikDurumu>({
  saglik: null,
  kapali: false,
  hazir: false,
});

export function SaglikProvider({ children }: { children: ReactNode }) {
  const [saglik, setSaglik] = useState<Health | null>(null);
  const [kapali, setKapali] = useState(false);
  const [hazir, setHazir] = useState(false);
  const canli = useRef(true);

  useEffect(() => {
    canli.current = true;
    let zaman: ReturnType<typeof setTimeout> | null = null;

    async function yokla() {
      try {
        const cevap = await api.health();
        if (!canli.current) return;
        setSaglik(cevap);
        setKapali(false);
      } catch {
        // Hata YUTULMUYOR, YORUMLANIYOR: bu ucun düşmesi bir bilgi ve
        // arayüzün göstereceği şeyin ta kendisi.
        if (!canli.current) return;
        setKapali(true);
      } finally {
        if (canli.current) {
          setHazir(true);
          zaman = setTimeout(yokla, ARALIK_MS);
        }
      }
    }

    void yokla();
    return () => {
      canli.current = false;
      if (zaman) clearTimeout(zaman);
    };
  }, []);

  const deger = useMemo<SaglikDurumu>(
    () => ({ saglik, kapali, hazir }),
    [saglik, kapali, hazir],
  );

  return (
    <SaglikContext.Provider value={deger}>{children}</SaglikContext.Provider>
  );
}

export function useSaglik(): SaglikDurumu {
  return useContext(SaglikContext);
}
