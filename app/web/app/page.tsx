"use client";

/**
 * Dashboard giriş sayfası — yalnızca sekme yönlendirmesi ve ortak veri yüklemesi.
 *
 * İlgili: ../components/*, ../lib/api.ts, ../lib/tabState.ts, CLAUDE.md §7
 *
 * Eskiden bu dosya 191 satırlık tek bileşendi: tip tanımları, biçimlendirici,
 * sayfa mantığı ve 11 inline stil objesi bir aradaydı. Artık her sorumluluk
 * kendi dosyasında; burada kalan tek iş sekmeler ve iki ortak istek
 * (`/fields`, `/campaigns`).
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
import SummaryCoverage from "./components/SummaryCoverage";
import TazelemePanel from "./components/TazelemePanel";
import Tabs, { TabPanel, type SekmeTanimi } from "./components/ui/Tabs";
import { api } from "./lib/api";
import { JuryModeProvider, useJuryMode } from "./lib/juryMode";
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
  | "tazele";

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
 * Jüri modunda EK sekme: veri tazeleme.
 *
 * Ağa çıkan tek yüzey olduğu için ürün ekranında yeri yok, denetim ekranında
 * var. İki dizi de modül düzeyinde SABİT: her render'da yeniden oluşan bir
 * dizi `useTabState`'in efektlerini sonsuz döngüye sokardı.
 */
const TABS_JURI: readonly SekmeTanimi<TabKey>[] = [
  ...TABS,
  { key: "tazele", label: "Veri Tazeleme" },
] as const;

const TAB_KEYS = TABS.map((t) => t.key);
const TAB_KEYS_JURI = TABS_JURI.map((t) => t.key);

/** Jüri modu tüm sekmeleri sarar; ComparePanel içeriden okur. */
export default function Home() {
  return (
    <JuryModeProvider>
      <Dashboard />
    </JuryModeProvider>
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
    if (!jury && sekme === "tazele") setSekme("compare");
  }, [jury, sekme, setSekme]);

  const fields = useAsync(() => api.fields(), []);
  const campaigns = useAsync(() => api.campaigns(), []);

  const rows = campaigns.data ?? [];
  const campaignTypes = Array.from(
    new Set(rows.map((c) => c.campaign_type).filter(Boolean)),
  ) as string[];
  const ozetli = rows.filter(
    (c) => typeof c.ozet === "string" && c.ozet.trim() !== "",
  ).length;

  const inspect = useCallback(
    (campaignId: number) => {
      setAuditTarget(campaignId);
      setSekme("audit");
    },
    [setSekme],
  );

  return (
    <main>
      <JuryModeToggle />

      {!campaigns.loading && rows.length > 0 && (
        <SummaryCoverage toplam={rows.length} ozetli={ozetli} />
      )}

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
      {!!campaigns.error && !fields.error && (
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
      </TabPanel>
    </main>
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
