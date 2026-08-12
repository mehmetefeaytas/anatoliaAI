import type { ReactNode } from "react";
import "./styles/tokens.css";
import "./styles/tema.css";
import "./styles/base.css";
import "./styles/components.css";
import "./styles/arama.css";
import "./styles/grafik.css";
import "./styles/banka.css";
import "./styles/sohbet.css";
import "./styles/baski.css";

/**
 * Kök yerleşim.
 *
 * Stiller ALTI katmandan gelir ve sıra önemlidir: token → tema seçimi →
 * taban → bileşen → grafik → sohbet. Son ikisi ayrı dosyadır çünkü
 * `components.css` zaten 1365 satır ve on bileşen ailesi taşıyor; grafik
 * katmanı ile sohbet çekmecesi yeni aileler olarak tek seferde geldi.
 * Denetim betiği `styles/*.css`'in tamamını tarar (`css_sinif_denetimi.py:69`),
 * yani ayrılık kapıdan kaçmak değildir.
 * Eskiden tek `globals.css` vardı (471 satır,
 * `docs/archive/globals-v1.css`); 16 tokenının 14'ü renkti, boşluk/tipografi/
 * gölge için token yoktu ve `@media` sorgusu hiç bulunmuyordu. Ayrıntılı
 * gerekçe: `styles/tokens.css`.
 *
 * Tema VARSAYILAN olarak devralınır: açık palet `:root`'ta, koyu palet
 * `prefers-color-scheme` altında tanımlıdır. Kullanıcı açıkça seçerse
 * `styles/tema.css` işletim sistemini ezer (bkz. `lib/tema.tsx`). Sunucu
 * çıktısı her hâlde aynıdır — seçim `:root` niteliğiyle, mount sonrası
 * uygulanır — yani hidrasyon uyuşmazlığı olmaz.
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
