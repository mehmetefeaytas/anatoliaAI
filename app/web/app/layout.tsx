import type { ReactNode } from "react";
import "./globals.css";

/**
 * Kök yerleşim. Stiller tek global stylesheet'ten gelir (bkz. globals.css);
 * inline `CSSProperties` objeleri kaldırıldı.
 *
 * Harici font/CDN çağrısı YOKTUR — sistem yazı tipleri kullanılır (offline kısıtı).
 */

export const metadata = {
  title: "Anatolia AI — Katılım Bankacılığı Kampanya Paneli",
  description:
    "Katılım bankaları kampanya bilgi çıkarımı, karşılaştırma, kaynak-span " +
    "denetimi ve chatbot",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="tr">
      <body>
        <div className="shell">
          <header className="site-header">
            <h1>Anatolia AI</h1>
            <p>
              Katılım Bankacılığı Kampanya Bilgi Çıkarımı &amp; Karşılaştırma —
              her değer kaynağına, güvenine ve onu üreten katmana bağlıdır.
            </p>
          </header>
          {children}
        </div>
      </body>
    </html>
  );
}
