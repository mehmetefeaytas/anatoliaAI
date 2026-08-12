"use client";

/**
 * Sohbet çekmecesi — sağ altta yuvarlak düğme, her ekranda.
 *
 * İlgili: ./ChatPanel.tsx, ../styles/sohbet.css, ../page.tsx
 *         CLAUDE.md §5 (hibrit chatbot), şartname s.13 (Senaryo-2)
 *
 * ## Neden sekme olmaktan çıktı
 *
 * Chatbot dokuz sekmeden biriydi ve yedinci sıradaydı: kullanıcı bir tabloya
 * bakarken aklına soru geldiğinde sekme değiştirmek, baktığı tabloyu terk
 * etmek demekti. Oysa sorular tam da o tablodan doğuyor — «bu bankada neden
 * veri yok», «en düşük olan hangisiydi». Çekmece ekranı terk ettirmiyor.
 *
 * İki biçim, tek bileşen: çekmece (her yerde, 420px) ve `/sohbet` tam sayfa
 * (geniş kaynak tablosu için). `ChatPanel` `genis` prop'uyla ikisini ayırıyor.
 *
 * ## Kaynak tablosu tuzağı
 *
 * `table.data.stackable`'ın kart yığınına dönmesi bir GÖRÜNÜM medya sorgusuna
 * bağlı (`components.css`, `@media max-width: 900px`). 1440px'lik bir ekranda
 * 420px'lik çekmecede bu sorgu TETİKLENMEZ ve dört sütunlu kaynak tablosu
 * ezilir. Çözüm `@container` değil — projenin `color-mix()`'i reddettiği
 * uyumluluk çıtasına fazla yakın; bunun yerine çekmece `.sohbet-cekmece`
 * içindeki tabloları koşulsuz olarak yığın moduna alıyor (bkz. sohbet.css).
 *
 * ## Hazır sorular ekrana göre değişir
 *
 * `ChatPanel` içindeki liste modül düzeyinde sabitti ve her ekranda aynı altı
 * soruyu gösteriyordu. Kullanıcı «En Avantajlı» ekranındayken bileşik skoru,
 * banka sayfasındayken o bankayı sormak istiyor. Aşağıdaki eşleme bunu verir.
 *
 * Şartname s.13'ün iki örnek diyaloğundan biri (tek banka sorgusu) böylece
 * banka ekranında HAZIR DÜĞME hâline geliyor: jüri kendi örneğini ekranda
 * buluyor, yazmak zorunda kalmıyor.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import ChatPanel from "./ChatPanel";

/** Çekmecenin hangi ekranda açıldığı — hazır soruları bu belirler. */
export type SohbetBaglami =
  | "compare"
  | "advantageous"
  | "delta"
  | "audit"
  | "contradictions"
  | "extract"
  | "genel";

const GENEL: readonly string[] = [
  "Hangi bankada en düşük kâr payı oranı var?",
  "En yüksek vade veren banka hangisi?",
  "Masrafsız kampanya sunan bankalar hangileri?",
];

/**
 * Ekran → hazır sorular.
 *
 * Her küme ÜÇ soruyla sınırlı: çekmece 420px ve altı çip iki satır kaplayıp
 * soru kutusunu aşağı itiyordu — düzeltilen «katlanan üstü» kusurunun
 * çekmecedeki karşılığı.
 *
 * İlk ikisi `router.py` anahtar kelimeleriyle yapısal sorguya (toplama /
 * sıralama), sonuncusu RAG'e (koşul / açıklama) düşecek şekilde yazıldı — jüri
 * tek ekranda iki yolu da görsün.
 */
const HAZIR_SORULAR: Record<SohbetBaglami, readonly string[]> = {
  compare: [
    "Hangi bankada en düşük kâr payı oranı var?",
    "En düşük tahsis ücreti hangi bankada?",
    "Konut finansmanı kampanyasının koşulları neler?",
  ],
  advantageous: [
    "Konut finansmanında en avantajlı banka hangisi?",
    "En yüksek ödül veren kampanya hangisi?",
    "Bileşik skor nasıl hesaplanıyor?",
  ],
  delta: [
    "Kuveyt Türk hangi alanlarda geride?",
    "36 ay ve üzeri vade veren konut finansmanlarını listele",
    "Taşıt finansmanında bankalar arasındaki en büyük fark ne?",
  ],
  audit: [
    "Bu belgede hangi alanlar çıkarıldı?",
    "Kâr payı oranı hangi bankalarda hiç yok?",
    "Kampanya süresi nasıl belirleniyor?",
  ],
  contradictions: [
    "Masrafsız denip ücret alınan kampanyalar hangileri?",
    "Hangi bankalarda çelişki tespit edildi?",
    "Çelişki nasıl tespit ediliyor?",
  ],
  extract: [
    "Aralıklı oran nasıl işleniyor?",
    "«İlk 6 ay %0» ifadesi nasıl normalize ediliyor?",
    "Masrafsız ifadesi neden sıfır olarak işleniyor?",
  ],
  genel: GENEL,
};

/**
 * Ekran → çekmecenin başlığında basılan bağlam adı.
 *
 * Çekmece hangi ekranda açıldığını BİLİR ve söyler. Gerekçe: hazır sorular
 * ekrana göre değişiyor (`HAZIR_SORULAR`) ama kullanıcı bunu göremiyordu —
 * aynı düğme her ekranda farklı üç soru açıyordu ve değişimin sebebi görünmez
 * kalıyordu. Bağlam satırı o sebebi mono sesle (MAKİNE verisi: hangi ekranın
 * kümesi yüklü) tek satırda yazıyor.
 */
const BAGLAM_ADI: Record<SohbetBaglami, string> = {
  compare: "karşılaştırma",
  advantageous: "en avantajlı",
  delta: "banka içi delta",
  audit: "kanıt · denetim",
  contradictions: "çelişki tespiti",
  extract: "canlı çıkarım",
  genel: "genel",
};

type Props = {
  baglam?: SohbetBaglami;
  onInspect?: (campaignId: number) => void;
};

export default function SohbetCekmecesi({ baglam = "genel", onInspect }: Props) {
  const [acik, setAcik] = useState(false);
  const dugmeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  const kapat = useCallback(() => {
    setAcik(false);
    // Odak düğmeye DÖNER: klavye kullanıcısı çekmece kapanınca sayfanın
    // başına fırlatılmamalı.
    dugmeRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!acik) return;
    const tusa = (e: KeyboardEvent) => {
      if (e.key === "Escape") kapat();
    };
    document.addEventListener("keydown", tusa);
    return () => document.removeEventListener("keydown", tusa);
  }, [acik, kapat]);

  useEffect(() => {
    if (acik) panelRef.current?.focus();
  }, [acik]);

  return (
    <>
      {/* 56×56 daire, her ekranda AYNI yerde ve boyutta. Metin etiketi
          `aria-label` + `title` üzerinden geliyor: ekran okuyucu ve fare
          kullanıcısı aynı cümleyi alıyor, ama genişliği metne göre değişen bir
          kapsül artık sağ alt köşede kimi ekranda grafiği kimi ekranda tabloyu
          örtmüyor. Gerekçenin tamamı sohbet.css'te.

          Emoji yerine inline SVG: emoji font'a bağlıdır ve jüri makinesinde
          hangi biçimde çizileceği bilinmiyor — üstelik `--on-accent` rengini
          almıyor, kendi rengiyle basılıyordu. SVG `currentColor` taşıyor,
          yani tema tokenına uyuyor. Harici ikon paketi yok (offline kısıtı). */}
      <button
        ref={dugmeRef}
        type="button"
        className="sohbet-fab"
        aria-expanded={acik}
        aria-controls="sohbet-cekmece"
        aria-label={acik ? "Sohbeti kapat" : "Sohbeti aç"}
        title={acik ? "Sohbeti kapat" : "Soru sor"}
        onClick={() => setAcik((a) => !a)}
      >
        <svg
          width="26"
          height="26"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M4 5.5h16v11H9l-5 4z" />
          <path d="M8 9h8" />
          <path d="M8 12.5h5" />
        </svg>
      </button>

      {acik && (
        <div
          id="sohbet-cekmece"
          className="sohbet-cekmece"
          role="dialog"
          aria-label="Sohbet"
          ref={panelRef}
          tabIndex={-1}
        >
          <div className="sohbet-cekmece-bas">
            <span className="sohbet-cekmece-kimlik">
              <span className="sohbet-cekmece-ad">Sohbet</span>
              {/* MAKİNE sesi: hangi ekranın hazır soru kümesi yüklü. */}
              <span className="sohbet-cekmece-baglam">
                bağlam: {BAGLAM_ADI[baglam] ?? BAGLAM_ADI.genel}
              </span>
            </span>
            <button
              type="button"
              className="sohbet-kapat"
              onClick={kapat}
              aria-label="Sohbeti kapat"
            >
              ×
            </button>
          </div>

          <div className="sohbet-cekmece-govde">
            {/* Panelin sözleşmesi, cevaptan ÖNCE okunur. Bir chatbot'un
                uydurmadığına dair sözü, uydurma riski doğduktan sonra
                verilirse geç kalır. Provenans şeridi (3px sol kenar) bu
                cümleyi panelin diğer kanıt bloklarıyla aynı aileye koyuyor. */}
            <p className="sohbet-sozlesme">
              Yalnız korpustaki belgelerden cevap veriyorum. Cevabın her sayısı
              bir dipnot rozeti taşır; taşımıyorsa o sayıyı ben uydurmuşumdur ve
              öyle bir cevap üretmem.
            </p>

            <ChatPanel
              genis={false}
              presets={HAZIR_SORULAR[baglam] ?? GENEL}
              onInspect={onInspect}
            />
          </div>
        </div>
      )}
    </>
  );
}
