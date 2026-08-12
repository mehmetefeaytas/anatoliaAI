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
import ChatPanel from "./components/ChatPanel";
import ComparePanel from "./components/ComparePanel";
import ContradictionAlert from "./components/ContradictionAlert";
import { ErrorNotice, Loading } from "./components/ErrorNotice";
import ExtractLive from "./components/ExtractLive";
import JuryModeToggle from "./components/JuryModeToggle";
import SohbetCekmecesi, {
  type SohbetBaglami,
} from "./components/SohbetCekmecesi";
import SummaryCoverage from "./components/SummaryCoverage";
import AyarlarPanel from "./components/AyarlarPanel";
import TazelemePanel from "./components/TazelemePanel";
import TemaSecici from "./components/TemaSecici";
import Tabs, { TabPanel, type SekmeTanimi } from "./components/ui/Tabs";
import { api } from "./lib/api";
import { JuryModeProvider, useJuryMode } from "./lib/juryMode";
import { TemaProvider } from "./lib/tema";
import { useTabState } from "./lib/tabState";
import { useAsync } from "./lib/useAsync";

type TabKey =
  | "compare"
  | "advantageous"
  | "delta"
  | "audit"
  | "contradictions"
  | "extract"
  | "chat"
  | "tazele"
  | "ayarlar";

/**
 * Sıra kasıtlı: tek alanlı kıyastan çok alanlı bileşik skora, oradan banka
 * özeline; denetim yüzeyleri sonra gelir.
 *
 * Modül düzeyinde sabit — `useTabState` bunu bağımlılık olarak alıyor, her
 * render'da yeniden oluşan bir dizi olsaydı efektler sonsuz döngüye girerdi.
 */
const TABS: readonly SekmeTanimi<TabKey>[] = [
  { key: "compare", label: "Karşılaştırma" },
  { key: "advantageous", label: "En Avantajlı" },
  { key: "delta", label: "Banka İçi Delta" },
  { key: "audit", label: "Jüri Audit Paneli" },
  { key: "contradictions", label: "Çelişki Tespiti" },
  { key: "extract", label: "Canlı Çıkarım" },
  { key: "chat", label: "Chatbot" },
] as const;

/**
 * Jüri modunda EK sekmeler: veri tazeleme ve ayarlar.
 *
 * Tazeleme ağa çıkan tek yüzey olduğu için ürün ekranında yeri yok, denetim
 * ekranında var. Ayarlar da operatör yüzeyidir: gelecek faz uçlarının
 * sözleşmesini gösterir, ürün akışının parçası değildir.
 *
 * İki dizi de modül düzeyinde SABİT: her render'da yeniden oluşan bir dizi
 * `useTabState`'in efektlerini sonsuz döngüye sokardı.
 */
const TABS_JURI: readonly SekmeTanimi<TabKey>[] = [
  ...TABS,
  { key: "tazele", label: "Veri Tazeleme" },
  { key: "ayarlar", label: "Ayarlar" },
] as const;

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
        <Dashboard />
      </JuryModeProvider>
    </TemaProvider>
  );
}

function Dashboard() {
  const { jury } = useJuryMode();
  const sekmeler = jury ? TABS_JURI : TABS;
  const { sekme, setSekme } = useTabState<TabKey>(
    jury ? TAB_KEYS_JURI : TAB_KEYS,
    "compare",
  );
  const [auditTarget, setAuditTarget] = useState<number | null>(null);

  // Jüri modu kapatılınca tazeleme sekmesinde kalmak boş bir panel bırakırdı;
  // görünmeyen bir sekmede durmak yerine varsayılana dönülür.
  useEffect(() => {
    if (!jury && (sekme === "tazele" || sekme === "ayarlar")) setSekme("compare");
  }, [jury, sekme, setSekme]);

  const fields = useAsync(() => api.fields(), []);
  const stats = useAsync(() => api.stats(), []);
  const campaigns = useAsync(() => api.campaigns(), []);

  const rows = campaigns.data ?? [];
  // Kampanya türleri artık `/stats`ten geliyor, `/campaigns` yanıtından
  // türetilmiyor. Türetme ölçülen bir maliyetti: liste yanıtı ham gövdelerle
  // birlikte 10,3 MB'tı ve tek amacı bir `<select>` doldurmaktı. `/stats` aynı
  // listeyi sunucuda, `extracted_fields` sayaçlarıyla birlikte tek istekte
  // verir; üstelik sıralı ve tekrarsız.
  const campaignTypes = stats.data?.campaign_types ?? [];
  const inspect = useCallback(
    (campaignId: number) => {
      setAuditTarget(campaignId);
      setSekme("audit");
    },
    [setSekme],
  );

  return (
    <main>
      {/* İki anahtar tek şeritte: ikisi de panelin tamamını etkiler ve
          ikisi de sekmelerden bağımsızdır. */}
      <div className="arac-cubugu">
        <JuryModeToggle />
        <TemaSecici />
      </div>

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

      {/* Ortak veri hataları sekmelerden bağımsız gösterilir. */}
      {!!fields.error && (
        <div style={{ marginBottom: "var(--sp-4)" }}>
          <ErrorNotice error={fields.error} />
        </div>
      )}
      {!!stats.error && !fields.error && (
        <div style={{ marginBottom: "var(--sp-4)" }}>
          <ErrorNotice error={stats.error} />
        </div>
      )}
      {!!campaigns.error && !fields.error && !stats.error && (
        <div style={{ marginBottom: "var(--sp-4)" }}>
          <ErrorNotice error={campaigns.error} />
        </div>
      )}

      <TabPanel sekme={sekme}>
        {sekme === "compare" &&
          (fields.loading ? (
            <Loading label="Alan listesi yükleniyor…" />
          ) : fields.data && fields.data.length > 0 ? (
            <ComparePanel fields={fields.data} campaignTypes={campaignTypes} />
          ) : !fields.error ? (
            <AlanListesiBos />
          ) : null)}

        {sekme === "advantageous" && (
          <AdvantageousPanel campaignTypes={campaignTypes} onInspect={inspect} />
        )}

        {sekme === "delta" && (
          <BankDeltaPanel campaignTypes={campaignTypes} onInspect={inspect} />
        )}

        {sekme === "audit" &&
          (campaigns.loading ? (
            <Loading label="Belgeler yükleniyor…" />
          ) : (
            <AuditPanel campaigns={rows} selectedId={auditTarget} />
          ))}

        {sekme === "contradictions" && <ContradictionAlert onInspect={inspect} />}

        {sekme === "extract" && <ExtractLive />}

        {sekme === "chat" && <ChatPanel onInspect={inspect} />}

        {/* Ağa çıkan tek yüzey — yalnız jüri modunda erişilebilir. */}
        {sekme === "tazele" && jury && <TazelemePanel />}

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
    </main>
  );
}

/**
 * Sekme anahtarını sohbet bağlamına çevirir.
 *
 * Çoğu birebir eşleşiyor; eşleşmeyenler («chat» — zaten sohbetin kendisi,
 * «tazele» ve «ayarlar» — operatör yüzeyleri, korpus hakkında soru sorulacak
 * yer değil) genel kümeye düşüyor.
 */
function sohbetBaglami(sekme: TabKey): SohbetBaglami {
  switch (sekme) {
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
