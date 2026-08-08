import type { ReactNode } from "react";
import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/components.css";

/**
 * Kök yerleşim.
 *
 * Stiller ÜÇ katmandan gelir ve sıra önemlidir: token → taban → bileşen.
 * Eskiden tek `globals.css` vardı (471 satır, `docs/archive/globals-v1.css`);
 * 16 tokenının 14'ü renkti, boşluk/tipografi/gölge için token yoktu ve
 * `@media` sorgusu hiç bulunmuyordu. Ayrıntılı gerekçe: `styles/tokens.css`.
 *
 * Tema seçilmez, DEVRALINIR: açık palet `:root`'ta, koyu palet
 * `prefers-color-scheme` altında tanımlıdır. Sunucu ve istemci aynı HTML'i
 * üretir, hidrasyon uyuşmazlığı olmaz.
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
