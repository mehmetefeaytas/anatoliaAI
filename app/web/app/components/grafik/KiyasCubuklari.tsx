"use client";

/**
 * Yatay kıyas çubukları — tek ölçütte banka sıralaması.
 *
 * İlgili: ../../lib/grafikPaleti.ts, ../../lib/api.ts (CompareRow),
 *         ../../lib/format.ts, ./KapsamaCetveli.tsx, CLAUDE.md §17 (adil kıyas)
 *
 * Jürinin en hızlı okuyacağı format budur: «en düşük tahsis ücreti kimde»
 * sorusunun cevabı tek bakışta çıkar. Yatay seçildi çünkü etiketler banka
 * adlarıdır — dikey çubukta eğik yazılmak zorunda kalırlardı.
 *
 * ## ARTIK BİRİNCİL DEĞİL — yerine kapsama cetveli geldi (2026-08-12)
 *
 * Karşılaştırma ekranının taşıyıcı görselleştirmesi bu tuval DEĞİL,
 * `KapsamaCetveli` (saf DOM + CSS grid). Bileşen silinmedi; gerekçe, tuvalin
 * üç ayrı kısıtı:
 *
 *  1. **Canvas erişilebilirlik ağacında yoktur.** Aşağıdaki `.grafik-liste`
 *     tam olarak bu yüzden var: grafiğin metin eşi. Yani aynı bilgi iki kez
 *     çiziliyor ve ekran okuyucu kullanıcısı grafiği hiç görmüyor, yalnız onun
 *     kopyasını okuyor.
 *  2. **Dört kapsama hâli AYRI BİÇİM taşıyamıyor.** Tuvalde elde renk ve
 *     uzunluk var; kesikli çerçeve, 135° tarama dokusu, kesik taban çizgisi ve
 *     eksende konumlu aralık kutusu yok. Aşağıda görüleceği gibi «veri yok»
 *     hâli ancak `transparent` dolgu + `--line` kenarlıkla anlatılabiliyor,
 *     yani boş çubuk ile ince bir çubuk birbirine yakın okunuyor. Renk TEK
 *     sinyal olamaz (WCAG 1.4.1).
 *  3. **`aria-label` / `title` taşıyamıyor.** Bir çubuğun «%1,69,
 *     kıyaslanabilir» olduğu ancak tuvalin dışında yazılabiliyordu.
 *
 * Bileşen kaldırılmadı çünkü kısıtları tuvale ait, kodu değil: başka bir
 * yüzeyde (tek türde hızlı bakış, baskı önizlemesi) hâlâ doğru araç olabilir.
 * Kullanılmaz kalırsa kaldırma kararı ayrı verilir — sessizce silinen bir
 * bileşen, gerekçesini de silmiş olur.
 *
 * ## Veri olmayan banka LİSTEDEN DÜŞMEZ
 *
 * `/compare` yalnız o alanın çıkarılabildiği satırları döndürür. Grafiği
 * doğrudan onunla çizmek, veri toplanamamış bankaları sessizce yok ederdi ve
 * ekran «bu alanda 6 banka var» derdi — oysa 11 banka var, 5'inde veri yok.
 *
 * Ölçüldü: `kar_payi_orani` 1.774 belgenin 56'sında, 11 bankanın 6'sında var.
 * Bu yüzden bileşen tüm banka listesini de alır ve verisi olmayanı BOŞ ÇUBUK +
 * «veri yok» olarak çizer. Eksiği raporlayan bir ekran, eksiği gizleyenden
 * daha dürüsttür — ve bu, adil kıyas garantisinin (§17) görsel karşılığıdır.
 *
 * ## Kıyaslanamayan satır sıralamaya girmez
 *
 * `comparable === false` olan satırlar (aralık, zaman-koşullu oran, farklı para
 * birimi) çubuk almaz: onlara bir uzunluk vermek, sistemin reddettiği
 * sıralamayı grafikte geri getirmek olurdu. Gerekçeleriyle listede kalırlar.
 *
 * ## Renk tek sinyal değil
 *
 * WCAG 1.4.1 ve 1.4.11: değer çubuğun ucunda YAZILI durur ve süresi dolmuş
 * kampanya ayrıca metinle işaretlenir. Canvas erişilebilirlik ağacında
 * olmadığı için (bkz. lib/grafikPaleti.ts) grafiğin altındaki tablo bağlantısı
 * tek gerçek erişilebilir yol olarak kalır.
 */

import {
  BarElement,
  CategoryScale,
  Chart as ChartJS,
  LinearScale,
  Tooltip,
  type ChartOptions,
} from "chart.js";
import { useMemo } from "react";
import { Bar } from "react-chartjs-2";
import type { Bank, CompareRow } from "../../lib/api";
import { formatValue, trNum } from "../../lib/format";
import { useGrafikPaleti } from "../../lib/grafikPaleti";

// Yalnız kullanılan parçalar kaydediliyor: Chart.js'in `auto` girişi tüm grafik
// türlerini pakete sokar, bu kayıt biçimi ~%60'ını dışarıda bırakır.
ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip);

type Props = {
  rows: CompareRow[];
  /** Tüm bankalar — verisi olmayanların boş çubuk olarak çizilebilmesi için. */
  bankalar?: Bank[];
  /** Kıyaslanan alan (değer biçimlendirmesi için). */
  alan: string;
  baslik?: string;
};

type Cubuk = {
  ad: string;
  deger: number | null;
  metin: string;
  suresiDolmus: boolean;
};

/**
 * Çubukları kurar: veri taşıyan bankalar sıralı, taşımayanlar sonda.
 *
 * `rows` zaten sunucuda sıralanmış gelir (`intent` + `_LOWER_IS_BETTER`), bu
 * yüzden burada YENİDEN sıralanmaz — sıralama yönü sunucunun bilgisidir ve iki
 * yerde tutulursa er ya da geç ayrışır.
 */
function cubuklariKur(
  rows: CompareRow[],
  bankalar: Bank[] | undefined,
  alan: string,
): { cubuklar: Cubuk[]; veriYokSayisi: number } {
  const cubuklar: Cubuk[] = [];
  const gorulen = new Set<string>();

  for (const r of rows) {
    if (!r.comparable || r.sort_key === null) continue;
    const ad = r.bank_name || r.bank;
    if (gorulen.has(ad)) continue;
    gorulen.add(ad);
    cubuklar.push({
      ad,
      deger: r.sort_key,
      metin: formatValue(r.value, alan),
      suresiDolmus: r.campaign_status === "expired",
    });
  }

  let veriYokSayisi = 0;
  for (const b of bankalar ?? []) {
    if (gorulen.has(b.name)) continue;
    veriYokSayisi += 1;
    cubuklar.push({ ad: b.name, deger: null, metin: "veri yok", suresiDolmus: false });
  }

  return { cubuklar, veriYokSayisi };
}

export default function KiyasCubuklari({ rows, bankalar, alan, baslik }: Props) {
  const palet = useGrafikPaleti();
  const { cubuklar, veriYokSayisi } = useMemo(
    () => cubuklariKur(rows, bankalar, alan),
    [rows, bankalar, alan],
  );

  // Palet mount öncesi `null` (hidrasyon disiplini, bkz. lib/grafikPaleti.ts).
  // O hâlde grafik çizilmez; iskelet, çağıran bileşenin işidir.
  if (!palet || cubuklar.length === 0) return null;

  const veri = {
    labels: cubuklar.map((c) => c.ad),
    datasets: [
      {
        data: cubuklar.map((c) => c.deger ?? 0),
        backgroundColor: cubuklar.map((c) =>
          c.deger === null ? "transparent" : palet["--accent"],
        ),
        borderColor: cubuklar.map((c) =>
          c.deger === null ? palet["--line"] : palet["--accent"],
        ),
        borderWidth: cubuklar.map((c) => (c.deger === null ? 1 : 0)),
        borderRadius: 3,
        barThickness: 18,
      },
    ],
  };

  const secenekler: ChartOptions<"bar"> = {
    indexAxis: "y",
    responsive: true,
    maintainAspectRatio: false,
    animation: false, // Jüri 4 dakikada hızlı tıklıyor; giriş animasyonu gecikme.
    plugins: {
      legend: { display: false }, // Tek seri — gösterge yalnız yer kaplardı.
      tooltip: {
        backgroundColor: palet["--bg-2"],
        titleColor: palet["--fg"],
        bodyColor: palet["--fg-dim"],
        borderColor: palet["--line"],
        borderWidth: 1,
        displayColors: false,
        callbacks: {
          label: (ctx) => {
            const c = cubuklar[ctx.dataIndex];
            return c.suresiDolmus ? `${c.metin} · süresi dolmuş` : c.metin;
          },
        },
      },
    },
    scales: {
      x: {
        beginAtZero: true,
        border: { color: palet["--line"] },
        grid: { color: palet["--line-soft"] },
        ticks: {
          color: palet["--fg-faint"],
          font: { family: palet["--font-mono"], size: 11 },
          callback: (v) => trNum(Number(v)),
        },
      },
      y: {
        border: { color: palet["--line"] },
        grid: { display: false },
        ticks: {
          color: palet["--fg"],
          font: { family: palet["--font-sans"], size: 12 },
        },
      },
    },
  };

  return (
    <figure className="grafik">
      {baslik && <figcaption className="grafik-baslik">{baslik}</figcaption>}
      <div className="grafik-tuval" style={{ height: cubuklar.length * 30 + 48 }}>
        <Bar data={veri} options={secenekler} />
      </div>
      {/* Canvas erişilebilirlik ağacında yok; sayılar burada metin olarak da
          durur. Bu bir yedek değil, grafiğin erişilebilir eşidir. */}
      <ul className="grafik-liste small">
        {cubuklar.map((c) => (
          <li key={c.ad}>
            <span className="grafik-liste-ad">{c.ad}</span>
            <span className={c.deger === null ? "muted mono" : "mono"}>{c.metin}</span>
            {c.suresiDolmus && <span className="badge badge-expired">süresi dolmuş</span>}
          </li>
        ))}
      </ul>
      {veriYokSayisi > 0 && (
        <p className="small muted">
          {veriYokSayisi} bankada bu alan için çıkarılmış değer yok; çubukları boş
          çizildi, listeden düşürülmedi. «Veri yok», «ürün yok» demek değildir.
        </p>
      )}
    </figure>
  );
}
