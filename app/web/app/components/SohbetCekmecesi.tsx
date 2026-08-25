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

/**
 * Sesli karşılama — bu SAYFA YÜKLEMESİNDE çekmecenin İLK açılışında,
 * tek seferlik.
 *
 * ## Neden "sayfa yüklemesi başına bir kez", "sohbet boşsa" değil
 *
 * Eskiden ölçüt "sohbet geçmişi boş mu" (`sohbetOturumu.ts`'in `oku()`sü,
 * `localStorage`) idi. Bu YANLIŞTI: geçmiş kalıcıdır, bir kez soru sorulduğunda
 * localStorage sonsuza dek dolu kalır ve karşılama bir daha HİÇ görünmez —
 * sayfa yenilense de, tarayıcı yeniden açılsa da. Ekip kendi test ettikçe
 * (ve yarışma günü demo öncesi provada) geçmiş dolar, karşılama kaybolurdu.
 *
 * Doğru ölçüt sohbet geçmişinden TAMAMEN BAĞIMSIZ: `gosterildiRef` component
 * mount olduğunda `false`'tur ve component HER SAYFA YÜKLEMESİNDE (F5, yeni
 * sekme) yeniden mount olur — yani bayrak sayfa yüklemesi başına doğal olarak
 * sıfırlanır, `localStorage`'a hiç yazılmaz. Aynı sayfa yüklemesi içinde
 * çekmece birkaç kez açılıp kapanırsa (jüri demoda deneyebilir) ref ilk
 * tetiklemede `true` olur ve ikinci/üçüncü açılışta karşılama tekrar
 * seslenmez — can sıkıcı olmaz.
 *
 * ## Neden FAB'ın `onClick`inde, `useEffect`te değil
 *
 * Tarayıcılar sesli `<audio>` oynatımını yalnız bir KULLANICI HAREKETİ
 * (tıklama vb.) içinde/hemen ardından izin verir; bir `useEffect`in içinde
 * çağrılan `play()` "kullanıcı hareketi" bağlamını kaybetmiş sayılabilir ve
 * sessizce reddedilebilir (`NotAllowedError`). FAB'a tıklamanın KENDİSİ o
 * hareket olduğu için çalma isteği doğrudan tıklama işleyicisinde yapılır.
 */
function karsilamaGerekiyorMu(gosterildiRef: { current: boolean }): boolean {
  return !gosterildiRef.current;
}

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
    "Albaraka Türk konut finansmanının koşulları neler?",
  ],
  advantageous: [
    "Konut finansmanında en avantajlı banka hangisi?",
    "En yüksek ödül veren kampanya hangisi?",
    // Eski soru ("Bileşik skor nasıl hesaplanıyor?") RAG'e düşüyordu ve
    // korpusta hiçbir kampanya kendi puanlama yöntemimizi açıklamadığı için
    // "bilgi verimde yok" döndürüyordu — metodoloji sorusu, kampanya sorusu
    // değil (ölçüldü, 2026-08-25). Aynı ekranın konusuna uyan, gerçekten
    // yanıtlanabilen bir soruyla değiştirildi.
    "Yatırım ürününde en avantajlı banka hangisi?",
  ],
  delta: [
    // Eski soru ("Kuveyt Türk hangi alanlarda geride?") RAG'e düşüyor ve
    // ilgisiz bir pazarlama pasajı döndürüyordu — router bunu yapısal delta
    // karşılaştırmasına değil semantik aramaya yönlendiriyordu (ölçüldü,
    // 2026-08-25). Banka adı olmayan, aynı "en geride" sorusunu yapısal yola
    // düşüren bir ifadeyle değiştirildi.
    "Vade açısından hangi banka en geride?",
    "36 ay ve üzeri vade veren konut finansmanlarını listele",
    "Taşıt finansmanında bankalar arasındaki en büyük fark ne?",
  ],
  audit: [
    // Eski soru ("Bu belgede hangi alanlar çıkarıldı?") belirli bir belge
    // seçilmeden anlamsızdı ve "safety" kapısından geri dönüyordu (ölçüldü,
    // 2026-08-25). Kendi başına anlamlı ve yanıtlanabilen bir soruyla
    // değiştirildi.
    "Hangi bankada en yüksek tahsis ücreti var?",
    "Kâr payı oranı hangi bankalarda hiç yok?",
    "Kampanya süresi nasıl belirleniyor?",
  ],
  contradictions: [
    "Masrafsız denip ücret alınan kampanyalar hangileri?",
    // Eski iki soru ("Hangi bankalarda çelişki tespit edildi?" zaman aşımına
    // uğruyordu; "Çelişki nasıl tespit ediliyor?" metodoloji sorusu olduğu
    // için "safety" kapısından dönüyordu — ölçüldü, 2026-08-25) yanıtlanabilen
    // sorularla değiştirildi.
    "Hangi bankada en yüksek tahsis ücreti var?",
    "İlk 6 ay masrafsız kampanya hangi bankada var?",
  ],
  extract: [
    // Üç eski soru da ("Aralıklı oran nasıl işleniyor?" vb.) normalizasyon
    // ALGORİTMASINI açıklamayı istiyordu — chatbot yalnız kampanya
    // belgelerinden cevap verir, kendi kodunu anlatamaz; üçü de "safety"
    // kapısından dönüyordu (ölçüldü, 2026-08-25). Aynı "zor vaka" temasını
    // (aralık, koşullu muafiyet) GERÇEK kampanya verisiyle gösteren,
    // yanıtlanabilen sorularla değiştirildi.
    "Kâr payı oranı aralık olarak verilen kampanya hangi bankada?",
    "İlk 6 ay masrafsız kampanya hangi bankada var?",
    "Taksit sayısı en fazla hangi bankada?",
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
  /**
   * Sunum turu (page.tsx `TUR_ADIMLARI`) bir soru sordurmak istediğinde dolar.
   * Çekmece kendini açar ve soruyu `ChatPanel`e iletir — kullanıcı elle
   * tıklamadan «gerçek» bir soru-cevap turu gösterilir.
   */
  turSorusu?: string | null;
  /**
   * Değiştiğinde (artan bir sayaç) çekmece kapanır. Sunum turunun "bu
   * adımda sohbet gösterilmiyor" sinyali — normal kullanımda hiç
   * değişmediği için (page.tsx yalnız tur SIRASINDA artırır) elle
   * açma/kapamaya karışmaz.
   */
  kapatIsareti?: number;
};

export default function SohbetCekmecesi({
  baglam = "genel",
  onInspect,
  turSorusu = null,
  kapatIsareti,
}: Props) {
  const [acik, setAcik] = useState(false);
  const [karsilamaGoster, setKarsilamaGoster] = useState(false);
  const dugmeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const sesRef = useRef<HTMLAudioElement>(null);
  // Bu SAYFA YÜKLEMESİNDE karşılama zaten gösterildi mi. Component her sayfa
  // yüklemesinde yeniden mount olduğu için `false` başlangıcı otomatik
  // sıfırlanır — bkz. dosya başındaki `karsilamaGerekiyorMu` gerekçesi.
  const gosterildiRef = useRef(false);

  const kapat = useCallback(() => {
    setAcik(false);
    // Odak düğmeye DÖNER: klavye kullanıcısı çekmece kapanınca sayfanın
    // başına fırlatılmamalı.
    dugmeRef.current?.focus();
  }, []);

  /**
   * FAB tıklaması — açılış/kapanışın TEK giriş noktası.
   *
   * Karşılama kararı burada verilir (bkz. `karsilamaGerekiyorMu` dosya
   * başlığı): tıklama anı, ses oynatımının izinli olduğu tek an.
   */
  const dugmeTikla = useCallback(() => {
    setAcik((a) => {
      const yeniAcik = !a;
      if (yeniAcik && karsilamaGerekiyorMu(gosterildiRef)) {
        gosterildiRef.current = true;
        setKarsilamaGoster(true);
        // `play()` bir Promise döner ve tarayıcı reddederse (otomatik oynatma
        // politikası, ses dosyası henüz inmediyse) reddedilmiş Promise
        // konsola sessizce YIĞIN İZİ basar — ses metnin yerine geçmediği için
        // (karşılama METNİ zaten aşağıda basılıyor) burada sohbeti
        // ENGELLEMEZ, ama ileride fark edilebilmesi için uyarı olarak loglanır.
        sesRef.current?.play().catch((hata) => {
          console.warn("karşılama sesi çalınamadı", hata);
        });
      } else if (!yeniAcik) {
        setKarsilamaGoster(false);
      }
      return yeniAcik;
    });
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

  // Sunum turu bir soru gönderince çekmece kendini açar — karşılama akışıyla
  // aynı `setAcik` yolunu KULLANMAZ çünkü bu açılış bir kullanıcı hareketi
  // değil; karşılama sesi burada ÇALINMAZ (otomatik oynatma reddi zaten
  // `dugmeTikla`nın gerekçesi, bkz. dosya başlığı).
  useEffect(() => {
    if (turSorusu) setAcik(true);
  }, [turSorusu]);

  // Sunum turunun "bu adımda sohbet yok" sinyali.
  useEffect(() => {
    if (kapatIsareti) setAcik(false);
  }, [kapatIsareti]);

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
        onClick={dugmeTikla}
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

      {/* Karşılama sesi — `demo-video/uret_ses.py` ile aynı ses
          (`tr-TR-AhmetNeural`), tutarlılık için. `preload="none"`: dosya
          yalnız gerçekten oynatılacaksa inmeli, her sayfa açılışında değil. */}
      <audio ref={sesRef} src="/ses/karsilama.mp3" preload="none" />

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
            {/* Sesli karşılamanın YAZILI karşılığı — ses çalışmasa/duyulmasa
                da (ekran okuyucu, sesi kapalı ortam, otomatik oynatma
                reddi) aynı bilgi metinde durur. Gerçek bir sohbet TURU
                değil — `sohbetOturumu.ts`'e yazılmaz, localStorage'a hiç
                girmez; sohbet boşken görünen, salt sunum amaçlı bir satır. */}
            {karsilamaGoster && (
              <div className="sohbet-karsilama" role="status">
                <span className="sohbet-karsilama-ad">Anatolia</span>
                <p className="sohbet-karsilama-metin">
                  Merhabalar, ben asistanınız Anatolia. Size nasıl yardımcı
                  olabilirim?
                </p>
              </div>
            )}

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
              otomatikSoru={turSorusu}
            />
          </div>
        </div>
      )}
    </>
  );
}
