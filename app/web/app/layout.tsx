import type { ReactNode } from "react";

export const metadata = {
  title: "Anatolia AI — Katılım Bankacılığı Kampanya Paneli",
  description: "Katılım bankaları kampanya bilgi çıkarımı, karşılaştırma ve chatbot",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="tr">
      <body
        style={{
          fontFamily: "system-ui, -apple-system, Segoe UI, Roboto, sans-serif",
          margin: 0,
          background: "#0f172a",
          color: "#e2e8f0",
        }}
      >
        <div style={{ maxWidth: 980, margin: "0 auto", padding: "24px 16px" }}>
          <header style={{ marginBottom: 24 }}>
            <h1 style={{ margin: 0, fontSize: 24 }}>Anatolia AI</h1>
            <p style={{ margin: "4px 0 0", color: "#94a3b8", fontSize: 14 }}>
              Katılım Bankacılığı Kampanya Bilgi Çıkarımı & Karşılaştırma
            </p>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
