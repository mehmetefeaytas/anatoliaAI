"use client";

/**
 * Komut paleti — ⌘K / Ctrl+K ile açılan, gruplu arama.
 *
 * İlgili: src/api/main.py (`GET /search`), ../lib/arama.ts, ../lib/api.ts,
 *         ../lib/useAsync.ts, ./ui/Tabs.tsx (ARIA klavye deseni),
 *         ./KaynakDipnotu.tsx (Esc kapatır, odak tetikleyiciye döner),
 *         ../styles/arama.css
 *
 * ## Neden var
 *
 * Korpus 1774 belge; arayüzde hiçbir arama yoktu. Bir belgeye ulaşmanın tek
 * yolu, denetim panelindeki 1774 seçenekli açılır listeyi kaydırmaktı. Bu
 * palet, üç farklı niyeti (bir bankaya git / bir belgeyi aç / bir kampanya
 * türünü süz) tek kutuda karşılar ve hangisinin arandığını kullanıcıya
 * sormaz — üçünü de gruplayarak gösterir.
 *
 * ## Sonuç KANITLIDIR
 *
 * Her belge satırının altında eşleşmenin NEDENİ durur: hangi alan, hangi
 * cümlenin içinde. Bu ürünün her yüzeyinde bir iddia kaynağını gösterir;
 * arama kutusunun bir istisna olması için sebep yok. Eşleşen harfler ayrıca
 * vurgulanır, böylece kullanıcı sonucu gözüyle doğrular.
 *
 * ## Gecikme (debounce) elle yazıldı
 *
 * Yeni bağımlılık yok (offline kısıtı + lisans denetimi) — `useAsync.ts`
 * başlığındaki gerekçenin aynısı. 250 ms, yazma hızının altında kalan ama
 * her tuşta sunucuya gitmeyi engelleyen aralık.
 *
 * ## Klavye
 *
 * Odak DAİMA arama kutusunda kalır; seçenekler `aria-activedescendant` ile
 * duyurulur (WAI-ARIA combobox+listbox deseni). Ok tuşlarıyla odak gerçekten
 * taşınsaydı her tuşta yazma kesilirdi. Esc kapatır ve odağı paleti açmadan
 * önceki öğeye GERİ VERİR — `KaynakDipnotu` ile aynı disiplin.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import type { AramaBelgesi, AramaSonucu } from "../lib/api";
import { alanEtiketi, aramaTerimleri, vurgulariBul } from "../lib/arama";
import { useAsync } from "../lib/useAsync";
import { ErrorNotice } from "./ErrorNotice";

/** Kullanıcının seçtiği şey. Üç niyet, üç ayrı biçim. */
export type AramaSecimi =
  | { tur: "banka"; slug: string; ad: string }
  | { tur: "belge"; id: number }
  | { tur: "tur"; ad: string };

type Props = {
  /** Seçim yapıldığında çağrılır; palet kendini kapatır. */
  onSec: (secim: AramaSecimi) => void;
  /** Listede gösterilecek azami sonuç (grup başına). */
  limit?: number;
};

/** Sunucuya gitmeden önce beklenen süre (ms). */
const GECIKME_MS = 250;

/** Tek bir satırın klavye/tıklama birimi. */
type Oge = {
  anahtar: string;
  secim: AramaSecimi;
};

/** Eşleşen harfleri `<mark>` ile boyar; eşleşme yoksa metni olduğu gibi basar. */
function Vurgulu({ metin, terimler }: { metin: string; terimler: string[] }) {
  const parcalar = useMemo(
    () => vurgulariBul(metin, terimler),
    [metin, terimler],
  );
  return (
    <>
      {parcalar.map((p, i) =>
        p.vurgulu ? (
          <mark key={i}>{metin.slice(p.bas, p.son)}</mark>
        ) : (
          <span key={i}>{metin.slice(p.bas, p.son)}</span>
        ),
      )}
    </>
  );
}

/** Belge satırının sağındaki durum rozetleri. */
function BelgeRozetleri({ belge }: { belge: AramaBelgesi }) {
  return (
    <>
      {belge.belge_turu === "sozlesme" && (
        <span className="badge badge-sozlesme">sözleşme</span>
      )}
      {belge.campaign_status === "expired" && (
        <span className="badge badge-expired">süresi dolmuş</span>
      )}
    </>
  );
}

export default function KomutPaleti({ onSec, limit = 20 }: Props) {
  const [acik, setAcik] = useState(false);
  const [sorgu, setSorgu] = useState("");
  const [gecikmeli, setGecikmeli] = useState("");
  const [imlec, setImlec] = useState(0);

  const girdiRef = useRef<HTMLInputElement>(null);
  const listeRef = useRef<HTMLDivElement>(null);
  // Palet açılmadan hemen önce odakta olan öğe; kapanınca odak buraya döner.
  const oncekiOdakRef = useRef<HTMLElement | null>(null);

  const kapat = useCallback(() => {
    setAcik(false);
    oncekiOdakRef.current?.focus();
  }, []);

  // --- ⌘K / Ctrl+K ---
  useEffect(() => {
    const tusa = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setAcik((a) => {
          if (!a) {
            oncekiOdakRef.current =
              document.activeElement instanceof HTMLElement
                ? document.activeElement
                : null;
          }
          return !a;
        });
      }
    };
    document.addEventListener("keydown", tusa);
    return () => document.removeEventListener("keydown", tusa);
  }, []);

  // Açılınca odak kutuya; kapanınca sorgu sıfırlanır (bir sonraki açılış
  // eski sonuçları göstermesin — kullanıcı yeni bir soru soruyor).
  useEffect(() => {
    if (acik) {
      girdiRef.current?.focus();
    } else {
      setSorgu("");
      setGecikmeli("");
      setImlec(0);
    }
  }, [acik]);

  // --- gecikme ---
  useEffect(() => {
    const zaman = setTimeout(() => setGecikmeli(sorgu.trim()), GECIKME_MS);
    return () => clearTimeout(zaman);
  }, [sorgu]);

  const sonuc = useAsync<AramaSonucu | null>(
    () =>
      acik && gecikmeli
        ? api.search(gecikmeli, limit)
        : Promise.resolve(null),
    [acik, gecikmeli, limit],
  );

  const terimler = useMemo(() => aramaTerimleri(gecikmeli), [gecikmeli]);
  const veri = sonuc.data;

  // Klavye gezinmesi grupları AŞAR: kullanıcı için liste tektir.
  const ogeler = useMemo<Oge[]>(() => {
    if (!veri) return [];
    return [
      ...veri.banks.map((b) => ({
        anahtar: `banka-${b.slug}`,
        secim: { tur: "banka", slug: b.slug, ad: b.name } as AramaSecimi,
      })),
      ...veri.campaigns.map((k) => ({
        anahtar: `belge-${k.id}`,
        secim: { tur: "belge", id: k.id } as AramaSecimi,
      })),
      ...veri.types.map((t) => ({
        anahtar: `tur-${t}`,
        secim: { tur: "tur", ad: t } as AramaSecimi,
      })),
    ];
  }, [veri]);

  // Sonuç kümesi değişince imleç başa döner: eski satırın numarası yeni
  // listede bambaşka bir şeyi işaret ederdi.
  useEffect(() => setImlec(0), [ogeler.length, gecikmeli]);

  const sec = useCallback(
    (secim: AramaSecimi) => {
      onSec(secim);
      setAcik(false);
      oncekiOdakRef.current?.focus();
    },
    [onSec],
  );

  // Seçili satır listeden taşarsa görünüre kaydırılır.
  useEffect(() => {
    if (!acik) return;
    listeRef.current
      ?.querySelector('[aria-selected="true"]')
      ?.scrollIntoView({ block: "nearest" });
  }, [imlec, acik]);

  if (!acik) return null;

  const secenekId = (i: number) => `komut-secenek-${i}`;

  function tusa(e: React.KeyboardEvent<HTMLDivElement>) {
    const son = ogeler.length - 1;
    if (e.key === "Escape") {
      e.preventDefault();
      kapat();
      return;
    }
    // Odak kutudan çıkmamalı: paletin arkasındaki sayfaya Tab'lamak, açık bir
    // katmanın altında gezinmek demek olurdu.
    if (e.key === "Tab") {
      e.preventDefault();
      return;
    }
    if (ogeler.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setImlec((i) => (i >= son ? 0 : i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setImlec((i) => (i <= 0 ? son : i - 1));
    } else if (e.key === "Home") {
      e.preventDefault();
      setImlec(0);
    } else if (e.key === "End") {
      e.preventDefault();
      setImlec(son);
    } else if (e.key === "Enter") {
      e.preventDefault();
      const secili = ogeler[imlec];
      if (secili) sec(secili.secim);
    }
  }

  let sira = -1;
  const siradaki = () => {
    sira += 1;
    return sira;
  };

  return (
    <div
      className="komut-ortu"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) kapat();
      }}
    >
      <div
        className="komut-paleti"
        role="dialog"
        aria-modal="true"
        aria-labelledby="komut-baslik"
        onKeyDown={tusa}
      >
        <h2 id="komut-baslik" className="gorunmez">
          Korpusta ara
        </h2>

        <div className="komut-bas">
          <label className="gorunmez" htmlFor="komut-girdi">
            Banka, belge veya kampanya türü ara
          </label>
          <input
            ref={girdiRef}
            id="komut-girdi"
            className="komut-girdi"
            type="text"
            role="combobox"
            autoComplete="off"
            aria-expanded={ogeler.length > 0}
            aria-controls="komut-liste"
            aria-activedescendant={
              ogeler.length > 0 ? secenekId(imlec) : undefined
            }
            placeholder="Banka, belge ya da kampanya türü ara…"
            value={sorgu}
            onChange={(e) => setSorgu(e.target.value)}
          />
          <span className="komut-ipucu" aria-hidden="true">
            ↑↓ gez · ↵ aç · Esc kapat
          </span>
        </div>

        {!!sonuc.error && (
          <div className="komut-durum">
            <ErrorNotice error={sonuc.error} />
          </div>
        )}

        {!gecikmeli && !sonuc.error && (
          <p className="komut-durum small muted">
            Aramak için yazmaya başlayın. Banka adı, kampanya türü, belge özeti
            ve belge adresi taranır; belgenin tam metni taranmaz.
          </p>
        )}

        {gecikmeli && sonuc.loading && (
          <p className="komut-durum small muted" role="status">
            Aranıyor…
          </p>
        )}

        {gecikmeli && !sonuc.loading && veri && ogeler.length === 0 && (
          <p className="komut-durum small muted" role="status">
            «{gecikmeli}» için sonuç bulunamadı. Belgenin içindeki bir ifadeyi
            arıyorsanız sohbet ekranını deneyin.
          </p>
        )}

        <div
          ref={listeRef}
          id="komut-liste"
          className="komut-liste"
          role="listbox"
          aria-label="Arama sonuçları"
        >
          {veri && veri.banks.length > 0 && (
            <div role="group" aria-labelledby="komut-grup-banka">
              <p id="komut-grup-banka" className="komut-grup-baslik">
                Bankalar
                <span className="komut-sayac">{veri.toplam.banks}</span>
              </p>
              {veri.banks.map((b) => {
                const i = siradaki();
                return (
                  <div
                    key={b.slug}
                    id={secenekId(i)}
                    role="option"
                    aria-selected={i === imlec}
                    className="komut-secenek"
                    onMouseEnter={() => setImlec(i)}
                    onClick={() =>
                      sec({ tur: "banka", slug: b.slug, ad: b.name })
                    }
                  >
                    <span className="komut-secenek-bas">
                      <Vurgulu metin={b.name} terimler={terimler} />
                    </span>
                    <span className="komut-secenek-alt small muted">
                      {b.campaign_count} belge
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {veri && veri.campaigns.length > 0 && (
            <div role="group" aria-labelledby="komut-grup-belge">
              <p id="komut-grup-belge" className="komut-grup-baslik">
                Belgeler
                <span className="komut-sayac">{veri.toplam.campaigns}</span>
              </p>
              {veri.campaigns.map((k) => {
                const i = siradaki();
                const etiket = alanEtiketi(k.eslesme.alan);
                return (
                  <div
                    key={k.id}
                    id={secenekId(i)}
                    role="option"
                    aria-selected={i === imlec}
                    className="komut-secenek"
                    onMouseEnter={() => setImlec(i)}
                    onClick={() => sec({ tur: "belge", id: k.id })}
                  >
                    <span className="komut-secenek-bas">
                      <span className="komut-belge-no mono">#{k.id}</span>
                      <Vurgulu
                        metin={k.bank_name || k.bank}
                        terimler={terimler}
                      />
                      {k.campaign_type && (
                        <>
                          {" · "}
                          <Vurgulu
                            metin={k.campaign_type}
                            terimler={terimler}
                          />
                        </>
                      )}
                      <BelgeRozetleri belge={k} />
                    </span>
                    <span className="komut-secenek-alt small muted">
                      {etiket && (
                        <span className="komut-eslesme-alan">{etiket}</span>
                      )}
                      <span className="komut-eslesme-parca">
                        <Vurgulu metin={k.eslesme.parca} terimler={terimler} />
                      </span>
                    </span>
                  </div>
                );
              })}
            </div>
          )}

          {veri && veri.types.length > 0 && (
            <div role="group" aria-labelledby="komut-grup-tur">
              <p id="komut-grup-tur" className="komut-grup-baslik">
                Kampanya türleri
                <span className="komut-sayac">{veri.toplam.types}</span>
              </p>
              {veri.types.map((t) => {
                const i = siradaki();
                return (
                  <div
                    key={t}
                    id={secenekId(i)}
                    role="option"
                    aria-selected={i === imlec}
                    className="komut-secenek"
                    onMouseEnter={() => setImlec(i)}
                    onClick={() => sec({ tur: "tur", ad: t })}
                  >
                    <span className="komut-secenek-bas">
                      <Vurgulu metin={t} terimler={terimler} />
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {veri && veri.toplam.campaigns > veri.campaigns.length && (
          <p className="komut-alt small muted">
            {veri.toplam.campaigns} belgeden ilk {veri.campaigns.length} tanesi
            gösteriliyor. Daraltmak için sorguya kelime ekleyin.
          </p>
        )}
      </div>
    </div>
  );
}
