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

import { useCallback, useState } from "react";
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
import Tabs, { TabPanel, type SekmeTanimi } from "./components/ui/Tabs";
import { api } from "./lib/api";
import { JuryModeProvider } from "./lib/juryMode";
import { useTabState } from "./lib/tabState";
import { useAsync } from "./lib/useAsync";

type TabKey =
  | "compare"
  | "advantageous"
  | "delta"
  | "audit"
  | "contradictions"
  | "extract"
  | "chat";

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

const TAB_KEYS = TABS.map((t) => t.key);

/** Jüri modu tüm sekmeleri sarar; ComparePanel içeriden okur. */
export default function Home() {
  return (
    <JuryModeProvider>
      <Dashboard />
    </JuryModeProvider>
  );
}

function Dashboard() {
  const { sekme, setSekme } = useTabState<TabKey>(TAB_KEYS, "compare");
  const [auditTarget, setAuditTarget] = useState<number | null>(null);

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
        sekmeler={TABS}
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

        {sekme === "delta" &&
          (fields.loading || campaigns.loading ? (
            <Loading label="Banka ve alan listesi yükleniyor…" />
          ) : fields.data && fields.data.length > 0 ? (
            <BankDeltaPanel
              fields={fields.data}
              campaigns={rows}
              campaignTypes={campaignTypes}
              onInspect={inspect}
            />
          ) : !fields.error ? (
            <AlanListesiBos ek="Delta hesaplanamaz." />
          ) : null)}

        {sekme === "audit" &&
          (campaigns.loading ? (
            <Loading label="Belgeler yükleniyor…" />
          ) : (
            <AuditPanel campaigns={rows} selectedId={auditTarget} />
          ))}

        {sekme === "contradictions" && <ContradictionAlert onInspect={inspect} />}

        {sekme === "extract" && <ExtractLive />}

        {sekme === "chat" && <ChatPanel onInspect={inspect} />}
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
