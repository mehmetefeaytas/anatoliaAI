"use client";

/**
 * Dashboard giriş sayfası — yalnızca sekme yönlendirmesi ve ortak veri yüklemesi.
 *
 * İlgili: ../components/*, ../lib/api.ts, ../lib/tabState.ts, CLAUDE.md §7
 *
 * Eskiden bu dosya 191 satırlık tek bileşendi: tip tanımları, biçimlendirici,
 * sayfa mantığı ve 11 inline stil objesi bir aradaydı. Artık her sorumluluk
 * kendi dosyasında; burada kalan tek iş sekmeler ve üç ortak istek
 * (`/fields`, `/stats`, `/campaigns`).
 *
 * ## Kampanya türleri `/stats`ten geliyor, `/campaigns`ten türetilmiyor
 *
 * Bu sayfa `<select>`i doldurmak için tüm kampanya listesini indirip
 * `campaign_type` alanlarını tekilleştiriyordu. Ölçüldü (2026-08-11): o istek
 * ham gövdelerle birlikte **10.339.015 bayttı** ve gövdeleri hiçbir bileşen
 * okumuyordu. Liste artık üstveri olarak geliyor (uç `raw_text`i varsayılan
 * göndermiyor) ve tür listesi sunucudan hazır alınıyor.
 *
 * `/campaigns` isteği KALDI: Jüri Audit Paneli belge seçicisini ondan besliyor.
 * Ama artık üstveri ölçeğinde — sayfanın açılışta indirdiği veri değil.
 *
 * ## Sekme durumu artık URL'de
 *
 * `useState<TabKey>` yerine `useTabState` (bkz. ../lib/tabState.ts): jüri bir
 * ekranı paylaşabilir, geri tuşu çalışır, yenilemede çalışılan ekran kaybolmaz.
 * ARIA tab deseni de tamamlandı — şerit artık `role="tabpanel"`,
 * `aria-controls` eşlemesi ve ok tuşu navigasyonu taşıyor (bkz. ui/Tabs.tsx).
 */

import { useCallback, useEffect, useState } from "react";
import AdvantageousPanel from "./components/AdvantageousPanel";
import AuditPanel from "./components/AuditPanel";
import BankDeltaPanel from "./components/BankDeltaPanel";
import BankaSayfasi from "./components/BankaSayfasi";
import ChatPanel from "./components/ChatPanel";
import ComparePanel from "./components/ComparePanel";
import ContradictionAlert from "./components/ContradictionAlert";
import { ErrorNotice, Loading } from "./components/ErrorNotice";
import ExtractLive from "./components/ExtractLive";
import GunlukPanel from "./components/GunlukPanel";
import IsiPanel from "./components/IsiPanel";
import DurumSeridi, { ApiKapaliUyarisi } from "./components/DurumSeridi";
import JuryModeToggle from "./components/JuryModeToggle";
import KomutPaleti from "./components/KomutPaleti";
import SohbetCekmecesi, {
  type SohbetBaglami,
} from "./components/SohbetCekmecesi";
import SummaryCoverage from "./components/SummaryCoverage";
import AyarlarPanel from "./components/AyarlarPanel";
import TazelemePanel from "./components/TazelemePanel";
import TemaSecici from "./components/TemaSecici";
import Tabs, { TabPanel, type SekmeTanimi } from "./components/ui/Tabs";
import { api, type Stats } from "./lib/api";
import { trNum } from "./lib/format";
import { JuryModeProvider, useJuryMode } from "./lib/juryMode";
import { SaglikProvider, useSaglik } from "./lib/saglik";
import { TemaProvider } from "./lib/tema";
import { useTabState } from "./lib/tabState";
import { useAsync } from "./lib/useAsync";

type TabKey =
  | "compare"
  | "isi"
  | "advantageous"
  | "banka"
  | "delta"
  | "audit"
  | "contradictions"
  | "extract"
  | "chat"
  | "tazele"
  | "gunluk"
  | "ayarlar";

/**
 * Sıra kasıtlı: tek alanlı kıyastan çok alanlı bileşik skora, oradan banka
 * özeline; denetim yüzeyleri sonra gelir.
 *
 * Banka sayfası deltadan ÖNCE geliyor çünkü ikisi de tek bankayı konu alıyor
 * ama sayfa künyeyi ve kampanya türü içindeki puanı da taşıyor; delta ise o
 * bankanın tek bir sorusunu («nerede geriyim») ayrıntılandırıyor ve sayfanın
 * içinde de duruyor.
 *
 * Modül düzeyinde sabit — `useTabState` bunu bağımlılık olarak alıyor, her
 * render'da yeniden oluşan bir dizi olsaydı efektler sonsuz döngüye girerdi.
 */
const TABS: readonly SekmeTanimi<TabKey>[] = [
  { key: "compare", label: "Karşılaştırma" },
  // Isı haritası kıyasın HEMEN ARDINDA: kıyas «kim daha avantajlı» der, harita
  // «bunu nerede ölçebiliyoruz» der. İkincisi birincinin okunma koşulu — bir
  // sıralamaya bakan kişinin ilk sorusu o sıralamanın kaç bankayı kapsadığı.
  { key: "isi", label: "Isı Haritası" },
  { key: "advantageous", label: "En Avantajlı" },
  { key: "banka", label: "Banka Sayfası" },
  { key: "delta", label: "Banka İçi Delta" },
  // KATILMA ORANLARI ARTIK SEKME DEĞİL (2026-08-24).
  //
  // Bir sekme olarak durduğu sürece "ayrı bir araç" gibi okunuyordu; oysa
  // sorduğu soru Karşılaştırma sekmesininkiyle AYNI («hangi banka daha iyi
  // veriyor»), yalnız kaynağı farklı — TKBB'nin haftalık yayını, kampanya
  // korpusu değil. Bu yüzden ComparePanel'in görünüm anahtarına ÜÇÜNCÜ
  // seçenek olarak taşındı (bkz. ComparePanel.tsx `gorunum`), tıpkı ürün
  // tablosunun ayrı sekme değil görünüm olması gibi. Kaynak farkı
  // gizlenmiyor: seçeneğin adında «(TKBB)» yazıyor.
  { key: "contradictions", label: "Çelişki Tespiti" },
] as const;

/**
 * Jüri modunda EK sekmeler — DENETİM ve OPERATÖR yüzeyleri.
 *
 * Ayrımın ölçütü şu: bir ekran KAMPANYA hakkında bir soru mu yanıtlıyor, yoksa
 * SİSTEM hakkında mı? Ürün şeridinde kalan altı sekme birincisini yapıyor
 * («hangi banka daha avantajlı», «bu alan nerede ölçülebiliyor», «bu banka
 * nerede geride»). Buradaki dördü ikincisini:
 *
 *   audit    belge → çıkarılan alan → kaynak span zinciri; denetim yüzeyi
 *   extract  «sistem gerçekten çalışıyor» ispatı (CLAUDE.md §11), ürün akışı değil
 *   tazele   ağa çıkan TEK yüzey; offline demo akışının parçası değil
 *   ayarlar  gelecek faz uçlarının sözleşmesi
 *
 * `chat` de buraya taşındı ama SOHBETİN KENDİSİ HER EKRANDA DURUYOR: sağ alttaki
 * yüzen düğme ve çekmecesi jüri modundan bağımsız. Kalkan yalnız sekme, yani tam
 * sayfa yerleşim. Gerekçe: çekmece 396px ve kaynak tablosunu daraltıyor, tam
 * sayfa hâli o tabloyu tam genişlikte isteyen denetleyici için var — ürün
 * kullanıcısı için değil. Sohbete erişim hiçbir hâlde kaybolmuyor
 * (bkz. aşağıda `SohbetCekmecesi`, `TabPanel`in DIŞINDA).
 *
 * İki dizi de modül düzeyinde SABİT: her render'da yeniden oluşan bir dizi
 * `useTabState`'in efektlerini sonsuz döngüye sokardı.
 */
const TABS_JURI: readonly SekmeTanimi<TabKey>[] = [
  ...TABS,
  { key: "audit", label: "Jüri Audit Paneli" },
  { key: "extract", label: "Canlı Çıkarım" },
  { key: "chat", label: "Chatbot" },
  { key: "tazele", label: "Veri Tazeleme" },
  { key: "gunluk", label: "İşlem Günlüğü" },
  { key: "ayarlar", label: "Ayarlar" },
] as const;

/**
 * Jüri modu kapanınca terk edilmesi gereken sekmeler.
 *
 * Görünmeyen bir sekmede kalmak boş bir panel bırakır. Liste `TABS_JURI`'den
 * TÜRETİLİYOR, elle yazılmıyor: yeni bir jüri sekmesi eklendiğinde bu koruma
 * kendiliğinden kapsıyor. Elle yazılmış bir liste, eklenen sekmeyi sessizce
 * dışarıda bırakırdı — `audit` ve `extract` ürün şeridinden buraya taşınırken
 * eski koruma tam olarak bunu yapıyordu (yalnız `tazele`/`ayarlar` sayılıydı).
 */
const JURI_SEKMELERI: ReadonlySet<TabKey> = new Set(
  TABS_JURI.filter((t) => !TABS.some((u) => u.key === t.key)).map((t) => t.key),
);

const TAB_KEYS = TABS.map((t) => t.key);
const TAB_KEYS_JURI = TABS_JURI.map((t) => t.key);

/**
 * Jüri modu tüm sekmeleri sarar; ComparePanel içeriden okur.
 *
 * Tema sağlayıcısı da buradadır, kök yerleşimde değil: seçim `localStorage`'a
 * ve `document`e dokunur, yani istemci tarafı bir işlemdir. Kök yerleşim ise
 * sunucu bileşenidir ve öyle kalması, sayfanın kabuğunun sunucuda üretilmeye
 * devam etmesi demektir.
 */
export default function Home() {
  return (
    <TemaProvider>
      <JuryModeProvider>
        {/* Sağlık en dışta değil, en içte: tema ve jüri modu kullanıcı
            tercihleri, sağlık ise sunucu olgusu — ikisi birbirine bağlı
            değil ve sağlık yoklaması ilk ikisinin okunmasını beklemiyor. */}
        <SaglikProvider>
          <Dashboard />
        </SaglikProvider>
      </JuryModeProvider>
    </TemaProvider>
  );
}

function Dashboard() {
  const { jury, setJury } = useJuryMode();
  // API kapalıyken ortak veri hataları BASTIRILIR: üçü de aynı tek olayı
  // anlatıyor ve kabuktaki bant onu zaten açıklıyor. Üstelik o kutuların
  // ipucu metni operatöre yazılmış (`uvicorn … çalışıyor mu?`) — jüri
  // ekranında geliştirici talimatı görünmemeli.
  const { kapali: apiKapali } = useSaglik();
  const sekmeler = jury ? TABS_JURI : TABS;
  const { sekme, setSekme } = useTabState<TabKey>(
    jury ? TAB_KEYS_JURI : TAB_KEYS,
    "compare",
  );
  const [auditTarget, setAuditTarget] = useState<number | null>(null);
  // Banka sayfasının öznesi. `auditTarget` ile aynı desen: bir ekran başka bir
  // ekranın konusunu belirleyebilmeli, kullanıcı seçimi elle tekrarlamamalı.
  const [bankaTarget, setBankaTarget] = useState<string | null>(null);
  // Komut paletinden seçilen kampanya türü. Tür bir ekran değil süzgeç;
  // kıyas paneline başlangıç değeri olarak geçiyor.
  const [turSuzgeci, setTurSuzgeci] = useState<string | null>(null);
  // Isı haritasının konusu olan alan. `null` iken bileşen alan listesinin ilk
  // öğesine düşer — sabit bir alan adı yazmak, `/fields` sırası değiştiğinde
  // sessizce var olmayan bir alanı sorardı.
  const [isiAlani, setIsiAlani] = useState<string | null>(null);

  // Jüri modu kapatılınca jüri sekmesinde kalmak boş bir panel bırakırdı;
  // görünmeyen bir sekmede durmak yerine varsayılana dönülür. Koruma artık
  // `JURI_SEKMELERI` üzerinden — sekme adları elle sayılmıyor.
  useEffect(() => {
    if (!jury && JURI_SEKMELERI.has(sekme)) setSekme("compare");
  }, [jury, sekme, setSekme]);

  const fields = useAsync(() => api.fields(), []);
  const stats = useAsync(() => api.stats(), []);
  const campaigns = useAsync(() => api.campaigns(), []);
  // Banka KATALOĞU — künyedeki «banka» sayısı buradan gelir, `/stats`ten değil.
  // İki uç iki farklı soruyu yanıtlıyor ve sayıları farklı: gerekçe
  // `KorpusKunyesi` başlığında.
  const banks = useAsync(() => api.banks(), []);

  const rows = campaigns.data ?? [];
  // Kampanya türleri artık `/stats`ten geliyor, `/campaigns` yanıtından
  // türetilmiyor. Türetme ölçülen bir maliyetti: liste yanıtı ham gövdelerle
  // birlikte 10,3 MB'tı ve tek amacı bir `<select>` doldurmaktı. `/stats` aynı
  // listeyi sunucuda, `extracted_fields` sayaçlarıyla birlikte tek istekte
  // verir; üstelik sıralı ve tekrarsız.
  const campaignTypes = stats.data?.campaign_types ?? [];
  /**
   * Bir belgenin kanıt zincirine sıçrama — `¶` kaynak dipnotunun hedefi.
   *
   * ## Neden jüri modunu AÇIYOR
   *
   * Denetim paneli artık jüri modu sekmesi. Ama `¶` düğmesi ürünün TEZİ ve ürün
   * ekranlarının her yerinde duruyor: kıyas cetvelinde, denetim tablosunda,
   * çelişki kartlarında, sohbet cevaplarında. «Ekranda bir sayı görüyorsan, o
   * sayının çıkarıldığı cümle bir tık uzakta» diyen bir panelde o tık sessizce
   * boşa düşemez.
   *
   * Üç seçenek vardı ve ikisi kötüydü: (a) `¶`yi ürün modunda gizlemek — tezi
   * ekrandan silmek; (b) görünmeyen bir sekmeye gitmek — hiçbir sekmenin seçili
   * görünmediği bir panel bırakmak. Seçilen (c): kanıta gitmek denetim yüzeyini
   * AÇAR. Anahtar görünür biçimde devrilir, sekme şeridi genişler ve kullanıcı
   * neden değiştiğini görür. Sessiz bir kip değişikliği değil, okunan bir sonuç.
   */
  const inspect = useCallback(
    (campaignId: number) => {
      setAuditTarget(campaignId);
      if (!jury) setJury(true);
      setSekme("audit");
    },
    [jury, setJury, setSekme],
  );
  /**
   * Banka adından banka sayfasına sıçrama — `inspect`in banka karşılığı.
   *
   * Ekranlar arasında öznenin taşınması elle kurulduğunda kayboluyordu:
   * kullanıcı delta ekranında bir bankayı seçip sayfasına bakmak istediğinde
   * sekme değiştirip aynı bankayı bir kez daha seçmek zorundaydı.
   */
  const bankaAc = useCallback(
    (slug: string) => {
      setBankaTarget(slug);
      setSekme("banka");
    },
    [setSekme],
  );

  return (
    <main>
      {/* Korpus künyesi başlığın hemen altında: kabuk (layout.tsx) TEZİ
          söylüyor, künye onun SAYISAL karşılığını veriyor. Sunucu bileşeni
          olan kabukta duramaz çünkü değerler `/stats` ve `/fields`ten iner. */}
      <KorpusKunyesi
        stats={stats.data}
        alanSayisi={fields.data?.length ?? null}
        bankaSayisi={banks.data?.length ?? null}
        yukleniyor={stats.loading || fields.loading || banks.loading}
      />

      {/* İki anahtar tek şeritte: ikisi de panelin tamamını etkiler ve
          ikisi de sekmelerden bağımsızdır. */}
      <div className="arac-cubugu">
        <JuryModeToggle />
        <TemaSecici />
        {/* Sunumda sunucu düştü ve arayüz bunu ancak paneller çökünce
            söyledi. Şerit artık kalıcı: API, depo, yerel model ve korpus
            ölçeği her ekranda okunuyor. */}
        <DurumSeridi />
      </div>

      {/* Ölü API bugüne kadar beş panelde beş ayrı kırmızı kutu olarak
          görünüyordu; hepsi aynı tek olayı anlatıyordu. Tek bant. */}
      <ApiKapaliUyarisi />

      {/* Kapsam sayacı artık kendi verisini `/summaries/coverage`'tan okur:
          "özet var mı" istemcide sayılabilirdi, "özet neden yok" sayılamazdı
          (gerekçe bileşenin başlığında). */}
      <SummaryCoverage />

      <Tabs
        sekmeler={sekmeler}
        aktif={sekme}
        onDegis={setSekme}
        etiket="Panel bölümleri"
      />

      {/* Ortak veri hataları sekmelerden bağımsız gösterilir — ama yalnız
          API AYAKTAYKEN. Kapalıyken hepsinin sebebi tektir ve bant söyler. */}
      {!apiKapali && !!fields.error && (
        <div style={{ marginBottom: "var(--sp-4)" }}>
          <ErrorNotice error={fields.error} />
        </div>
      )}
      {!apiKapali && !!stats.error && !fields.error && (
        <div style={{ marginBottom: "var(--sp-4)" }}>
          <ErrorNotice error={stats.error} />
        </div>
      )}
      {!apiKapali && !!campaigns.error && !fields.error && !stats.error && (
        <div style={{ marginBottom: "var(--sp-4)" }}>
          <ErrorNotice error={campaigns.error} />
        </div>
      )}

      <TabPanel sekme={sekme}>
        {sekme === "compare" &&
          (fields.loading ? (
            <Loading label="Alan listesi yükleniyor…" />
          ) : fields.data && fields.data.length > 0 ? (
            <ComparePanel
              fields={fields.data}
              campaignTypes={campaignTypes}
              baslangicTuru={turSuzgeci}
            />
          ) : !fields.error ? (
            <AlanListesiBos />
          ) : null)}

        {/* Isı haritası alan listesini bekler: seçicisi ondan doluyor ve
            haritanın başlığı alanın etiketini taşıyor. */}
        {sekme === "isi" &&
          (fields.loading ? (
            <Loading label="Alan listesi yükleniyor…" />
          ) : fields.data && fields.data.length > 0 ? (
            <IsiPanel
              fields={fields.data}
              kayitlar={rows}
              kayitlarYukleniyor={campaigns.loading}
              alan={isiAlani ?? fields.data[0].field}
              onAlanDegis={setIsiAlani}
            />
          ) : !fields.error ? (
            <AlanListesiBos />
          ) : null)}

        {sekme === "advantageous" && (
          <AdvantageousPanel campaignTypes={campaignTypes} onInspect={inspect} />
        )}

        {/* Kapsama etiketi `/stats`ten iner: bu sayfa o isteği zaten atıyor,
            banka sayfasının ikinci bir kez atması boşuna bir tur olurdu. */}
        {sekme === "banka" && (
          <BankaSayfasi
            campaignTypes={campaignTypes}
            kapsam={stats.data?.banka_kapsami ?? null}
            secili={bankaTarget}
            onInspect={inspect}
          />
        )}

        {sekme === "delta" && (
          <BankDeltaPanel
            campaignTypes={campaignTypes}
            onInspect={inspect}
            onBankaAc={bankaAc}
          />
        )}

        {/* Denetim yüzeyi — jüri modunda. `¶` kaynak dipnotu buraya sıçrarken
            kipi kendisi açıyor (bkz. `inspect`), yani ürün modunda tıklanan bir
            dipnot boşa düşmüyor. */}
        {sekme === "audit" &&
          jury &&
          (campaigns.loading ? (
            <Loading label="Belgeler yükleniyor…" />
          ) : (
            <AuditPanel campaigns={rows} selectedId={auditTarget} />
          ))}

        {sekme === "contradictions" && <ContradictionAlert onInspect={inspect} />}

        {/* «Sistem gerçekten çalışıyor» ispatı (CLAUDE.md §11) — bir kampanya
            sorusunu değil, sistemin kendisini konu alıyor. Denetim yüzeyi. */}
        {sekme === "extract" && jury && <ExtractLive />}

        {/* Sohbetin TAM SAYFA hâli. Çekmece (sağ altta, her ekranda) bundan
            bağımsız ve jüri modu kapalıyken de duruyor; kalkan yalnız geniş
            yerleşim. Gerekçe `TABS_JURI` başlığında. */}
        {sekme === "chat" && jury && <ChatPanel onInspect={inspect} />}

        {/* Ağa çıkan tek yüzey — yalnız jüri modunda erişilebilir. */}
        {sekme === "tazele" && jury && <TazelemePanel />}

        {/* İşlem günlüğü — «ne oldu, ne zaman oldu, kim tetikledi».
            Tazelemenin HEMEN ARDINDA: bu sekmenin var olma sebebi, bir
            tazelemenin 40 dosya yazması ve kimin tetiklediğinin saatlerce
            bulunamamasıydı. Sorunun sorulduğu ekranın yanında duruyor. */}
        {sekme === "gunluk" && jury && <GunlukPanel />}

        {/* Gelecek faz uçlarının sözleşmesi. Operatör yüzeyi olduğu için
            tazeleme ile aynı yerde: jüri modunda. */}
        {sekme === "ayarlar" && jury && <AyarlarPanel />}
      </TabPanel>

      {/* Sohbet SEKMENİN DIŞINDA da duruyor: kullanıcı bir tabloya bakarken
          aklına soru geldiğinde sekme değiştirmek, baktığı tabloyu terk etmek
          demekti — oysa sorular tam da o tablodan doğuyor. Çekmece ekranı
          terk ettirmiyor.

          Sekme KALDIRILMADI: geniş kaynak tablosu 420px'lik çekmecede
          okunmuyor ve jüri kanıt tablosunu tam genişlikte görmek istiyor.
          İki yerleşim, tek bileşen (`ChatPanel` `genis` prop'u).

          Çekmece açıldığı ekranı biliyor ve hazır soruları ona göre veriyor;
          sabit liste her ekranda aynı altı soruyu gösteriyordu. */}
      <SohbetCekmecesi baglam={sohbetBaglami(sekme)} onInspect={inspect} />

      {/* Komut paleti (⌘K / Ctrl+K) — uygulamada hiç arama yoktu.
          1.774 belge tek bir <select> içindeydi ve bankaya, türe ya da
          belgeye gitmenin başka yolu yoktu. Palet kendi açılma durumunu ve
          klavye dinleyicisini taşıyor; buradaki tek iş, seçimin hangi ekrana
          düştüğünü söylemek. */}
      <KomutPaleti
        onSec={(secim) => {
          if (secim.tur === "banka") bankaAc(secim.slug);
          else if (secim.tur === "belge") inspect(secim.id);
          else {
            // Kampanya türü bir SÜZGEÇ, bir ekran değil: kıyas ekranına
            // götürüp türü oraya taşımak, kullanıcıyı aradığı şeyin
            // kıyaslandığı yere bırakır.
            setTurSuzgeci(secim.ad);
            setSekme("compare");
          }
        }}
      />
    </main>
  );
}

/**
 * Sekme anahtarını sohbet bağlamına çevirir.
 *
 * Çoğu birebir eşleşiyor; eşleşmeyenler («chat» — zaten sohbetin kendisi,
 * «tazele» ve «ayarlar» — operatör yüzeyleri, korpus hakkında soru sorulacak
 * yer değil) genel kümeye düşüyor.
 *
 * «banka»nın kendi hazır soru kümesi henüz yok; en yakın küme «delta»dır ve
 * seçim savunulabilir: banka sayfası delta görünümünü de taşıyor, yani oradaki
 * sorular bu ekranda da cevabını buluyor. Genel kümeye düşürmek, tek bankayı
 * konu alan bir ekranda korpus geneli sorular göstermek olurdu.
 */
function sohbetBaglami(sekme: TabKey): SohbetBaglami {
  switch (sekme) {
    case "banka":
      return "delta";
    // Isı haritasının kendi hazır soru kümesi yok; kıyas kümesine düşüyor
    // çünkü oradaki sorulardan biri («kâr payı oranı hangi bankalarda hiç
    // geçmiyor») tam olarak haritanın konusu. Genel kümeye düşürmek, tek bir
    // alanın kapsamasına bakan kişiye korpus geneli sorular göstermek olurdu.
    case "isi":
      return "compare";
    case "compare":
    case "advantageous":
    case "delta":
    case "audit":
    case "contradictions":
    case "extract":
      return sekme;
    default:
      return "genel";
  }
}

/**
 * Korpus künyesi — panelin ölçeği ve SINIRI, her ekranda.
 *
 * İlgili: styles/base.css (`.kunye`), lib/api.ts (`Stats`), lib/format.ts
 *
 * Tasarımın kuralı: ölçeği söyleyip kapsamayı gizlemek, tam olarak bu ürünün
 * reddettiği şey. Bu yüzden künyenin son çipi kasıtlı olarak en zayıf alanı
 * söyler ve uyarı rengini giyer — övünme değil, sınır bildirimi.
 *
 * ## Neden BELGE kesri, banka kesri değil
 *
 * v2 tasarımı bu çipe «kâr payı: 6/11 bankada» yazıyor. `/stats` o sayıyı
 * VERMİYOR: `alan_kapsami` alan → BELGE sayısı eşlemesidir, alan → kaç ayrı
 * bankada geçtiği değil. İki sayı farklı sorguların cevabı ve ikincisi
 * `extracted_fields`i `campaigns.bank_id` üzerinden tekilleştirmeyi gerektirir.
 *
 * Elimizde olmayan kesri yazmak, panelin tek kuralını ilk satırda çiğnemek
 * olurdu (CLAUDE.md §19 — bilgi yoksa uydurma). Bu yüzden çip ÖLÇÜLEN kesri
 * basıyor: alan → belge. Banka kesri istenirse `/stats`e `alan_banka_kapsami`
 * eklenmesi gerekir; API tarafı bir sonraki iş.
 *
 * ## «Banka» sayısı `/banks`ten gelir, `/stats`ten DEĞİL
 *
 * ÖLÇÜLDÜ (2026-08-12): `/stats` `korpus.banks = 11`, `/banks` ise 10 satır
 * döndürüyor. Fark `tkbb` — Türkiye Katılım Bankaları Birliği, yani bankaların
 * BİRLİĞİ; bir banka değil, bir otorite kaynağı.
 *
 * Künye ilk hâlinde `korpus.banks`i okuyup «11 banka» yazıyordu ve bu, aynı
 * ekranda kendisiyle çelişiyordu: kapsama cetveli paydayı `/banks`ten aldığı
 * için «4 / 10 banka» basıyordu. Üstelik yanlıştı — TKBB'yi banka saymak, tam
 * olarak bu panelin reddettiği türden bir kategori hatası.
 *
 * v2 tasarım dosyası da «11 banka» yazıyor ve ısı haritası fikstüründe TKBB'yi
 * banka satırı olarak listeliyor. Tasarımın sayısı alınmadı: iki uç iki farklı
 * sorunun cevabı ve künye artık ikisini de basıyor — kaç BANKA, kaç KAYNAK.
 *
 * ## Yükleniyor ≠ sıfır
 *
 * Ölçü okunmadan önce çip KESİKLİ çerçeveyle boş durur; sayı basılmaz. Panelin
 * dört kapsama hâliyle aynı mantık: boşluğun kendi biçimi var, sıfırla
 * karıştırılmaz.
 */
function KorpusKunyesi({
  stats,
  alanSayisi,
  bankaSayisi,
  yukleniyor,
}: {
  stats: Stats | null;
  alanSayisi: number | null;
  bankaSayisi: number | null;
  yukleniyor: boolean;
}) {
  // Sınır çipi: en DÜŞÜK kapsamalı alan değil, HABERİ olan alan. `kar_payi_orani`
  // senaryonun ana ölçütü (CLAUDE.md §12) ve kapsaması en çok yanlış anlaşılan
  // sayı — «6 bankada var» ile «11 bankanın hepsinde kıyaslanabilir» arasındaki
  // fark bu panelin varlık sebebi.
  const anaAlan = "kar_payi_orani";
  const anaAlanKapsami = stats?.alan_kapsami?.[anaAlan] ?? null;
  const belge = stats?.korpus.campaigns ?? null;

  const cip = (deger: number | null, birim: string) =>
    deger === null ? (
      <span className="kunye-cip kunye-cip-bekliyor">{birim} · ölçülüyor</span>
    ) : (
      <span className="kunye-cip">
        {trNum(deger)} {birim}
      </span>
    );

  return (
    <div className="kunye" aria-busy={yukleniyor}>
      {cip(belge, "belge")}
      {cip(bankaSayisi, "banka")}
      {/* Kaynak sayısı bankadan FAZLA olduğunda basılır ve farkı söyler:
          korpusta banka olmayan kaynaklar var (TKBB gibi otorite yayınları) ve
          onların belgeleri de sayılıyor. Fark yoksa çip hiç görünmez — okuyucuya
          anlamsız bir eşitlik göstermek yerine sessiz kalır. */}
      {stats && bankaSayisi !== null && stats.korpus.banks > bankaSayisi ? (
        <span
          className="kunye-cip"
          title="Korpusta banka olmayan kaynaklar da var — bankaların birliği gibi otorite yayınları. Onların belgeleri sayılır ama bankalar arası kıyasa girmez."
        >
          {trNum(stats.korpus.banks)} kaynak
        </span>
      ) : null}
      {cip(stats?.campaign_types.length ?? null, "kampanya türü")}
      {cip(alanSayisi, "çıkarım alanı")}
      {/* Sınır çipi. Renk tek sinyal değil: kesrin kendisi sınırı söylüyor. */}
      {anaAlanKapsami !== null && belge !== null ? (
        <span className="kunye-cip kunye-cip-sinir">
          kâr payı oranı · {trNum(anaAlanKapsami)} / {trNum(belge)} belgede
        </span>
      ) : (
        <span className="kunye-cip kunye-cip-bekliyor">
          kâr payı oranı · kapsama ölçülüyor
        </span>
      )}
    </div>
  );
}

function AlanListesiBos({ ek }: { ek?: string }) {
  return (
    <div className="notice notice-warn">
      <strong>Alan listesi boş</strong>
      <div className="notice-body">
        API <span className="mono">/fields</span> ucundan hiçbir alan dönmedi.
        {ek ? ` ${ek}` : ""}
      </div>
    </div>
  );
}
