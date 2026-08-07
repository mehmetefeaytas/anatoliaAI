"use client";

/**
 * Dashboard giriş sayfası — yalnızca sekme yönlendirmesi ve ortak veri yüklemesi.
 *
 * İlgili: ../components/*, ../lib/api.ts, CLAUDE.md §7
 *
 * Eskiden bu dosya 191 satırlık tek bileşendi: tip tanımları, biçimlendirici,
 * sayfa mantığı ve 11 inline stil objesi bir aradaydı. Artık her sorumluluk
 * kendi dosyasında; burada kalan tek iş sekmeler ve iki ortak istek
 * (`/fields`, `/campaigns`).
 */

import { useState } from "react";
import AuditPanel from "./components/AuditPanel";
import BankDeltaPanel from "./components/BankDeltaPanel";
import ChatPanel from "./components/ChatPanel";
import ComparePanel from "./components/ComparePanel";
import ContradictionAlert from "./components/ContradictionAlert";
import { ErrorNotice, Loading } from "./components/ErrorNotice";
import ExtractLive from "./components/ExtractLive";
import JuryModeToggle from "./components/JuryModeToggle";
import { api } from "./lib/api";
import { JuryModeProvider } from "./lib/juryMode";
import { useAsync } from "./lib/useAsync";

type TabKey =
  | "compare"
  | "delta"
  | "audit"
  | "contradictions"
  | "extract"
  | "chat";

const TABS: { key: TabKey; label: string }[] = [
  { key: "compare", label: "Karşılaştırma" },
  { key: "delta", label: "Banka İçi Delta" },
  { key: "audit", label: "Jüri Audit Paneli" },
  { key: "contradictions", label: "Çelişki Tespiti" },
  { key: "extract", label: "Canlı Çıkarım" },
  { key: "chat", label: "Chatbot" },
];

/** Jüri modu tüm sekmeleri sarar; ComparePanel içeriden okur. */
export default function Home() {
  return (
    <JuryModeProvider>
      <Dashboard />
    </JuryModeProvider>
  );
}

function Dashboard() {
  const [tab, setTab] = useState<TabKey>("compare");
  const [auditTarget, setAuditTarget] = useState<number | null>(null);

  const fields = useAsync(() => api.fields(), []);
  const campaigns = useAsync(() => api.campaigns(), []);

  const campaignTypes = Array.from(
    new Set((campaigns.data ?? []).map((c) => c.campaign_type).filter(Boolean)),
  ) as string[];

  function inspect(campaignId: number) {
    setAuditTarget(campaignId);
    setTab("audit");
  }

  return (
    <main>
      <JuryModeToggle />

      <nav className="tabs" role="tablist" aria-label="Panel bölümleri">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            role="tab"
            aria-selected={tab === t.key}
            className="chip"
            onClick={() => setTab(t.key)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      {/* Ortak veri hataları sekmelerden bağımsız gösterilir. */}
      {!!fields.error && (
        <div style={{ marginBottom: 16 }}>
          <ErrorNotice error={fields.error} />
        </div>
      )}
      {!!campaigns.error && !fields.error && (
        <div style={{ marginBottom: 16 }}>
          <ErrorNotice error={campaigns.error} />
        </div>
      )}

      {tab === "compare" &&
        (fields.loading ? (
          <Loading label="Alan listesi yükleniyor…" />
        ) : fields.data && fields.data.length > 0 ? (
          <ComparePanel fields={fields.data} campaignTypes={campaignTypes} />
        ) : !fields.error ? (
          <div className="notice notice-warn">
            <strong>Alan listesi boş</strong>
            API <span className="mono">/fields</span> ucundan hiçbir alan dönmedi.
          </div>
        ) : null)}

      {tab === "delta" &&
        (fields.loading || campaigns.loading ? (
          <Loading label="Banka ve alan listesi yükleniyor…" />
        ) : fields.data && fields.data.length > 0 ? (
          <BankDeltaPanel
            fields={fields.data}
            campaigns={campaigns.data ?? []}
            campaignTypes={campaignTypes}
            onInspect={inspect}
          />
        ) : !fields.error ? (
          <div className="notice notice-warn">
            <strong>Alan listesi boş</strong>
            API <span className="mono">/fields</span> ucundan hiçbir alan dönmedi;
            delta hesaplanamaz.
          </div>
        ) : null)}

      {tab === "audit" &&
        (campaigns.loading ? (
          <Loading label="Belgeler yükleniyor…" />
        ) : (
          <AuditPanel campaigns={campaigns.data ?? []} selectedId={auditTarget} />
        ))}

      {tab === "contradictions" && <ContradictionAlert onInspect={inspect} />}

      {tab === "extract" && <ExtractLive />}

      {tab === "chat" && <ChatPanel onInspect={inspect} />}
    </main>
  );
}
