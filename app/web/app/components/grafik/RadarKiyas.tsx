"use client";

/**
 * Radar kıyası — iki bankanın çok ölçütlü karşılaştırması.
 *
 * İlgili: ../../lib/api.ts (CompositeScore, WeightRow), ../../lib/grafikPaleti.ts,
 *         ../AdvantageousPanel.tsx, src/comparison/compare.py (DEFAULT_WEIGHTS)
 *         CLAUDE.md §17 (adil kıyas), §5.7 (beş kıyas ölçütü)
 *
 * ## Eksenler uydurulmuyor
 *
 * Radar grafiklerinin klasik kusuru, eksenlerin tasarımcı tarafından seçilmesi
 * ve seçimin hiçbir yerde savunulmamasıdır. Burada eksenler `/advantageous`
 * ucunun döndürdüğü ağırlık listesinden gelir ve her birinin **yazılı gerekçesi**
 * vardır (`WeightRow.rationale`) — örneğin kâr payı oranının 0,40 ağırlığı için
 * «100.000 TL / 36 ay sepetinde korpustaki oran aralığı ~75.850 TL fark
 * yaratıyor». Gerekçe ekranda, grafiğin altında durur.
 *
 * ## Neden İKİ banka, üç değil
 *
 * Radar üst üste binen çokgenlerle okunur; ikiden fazla seri okunmaz hâle gelir
 * ve renkleri ayırt etmek tek sinyale (renge) bağımlılık yaratır. İki seri,
 * toplantıda sorulan «iki bankayı karşılaştırsak» sorusunun tam karşılığıdır.
 *
 * ## Eksen değeri `normalized`, ham değer DEĞİL
 *
 * Ham değerler farklı birimlerde (oran %, tutar TL, vade ay) — aynı radara
 * konamaz. `ScoreComponent.normalized` grup içi rank tabanlı 0..1 değeridir,
 * yani «bu ölçütte grubun neresinde» demektir. Bu yüzden grafik başlığı ve alt
 * notu bunu açıkça yazar: okunan şey mutlak büyüklük değil, GRUP İÇİ konumdur.
 *
 * ## Kapsanmayan ölçüt sıfır DEĞİL
 *
 * `normalized === null` (o kampanyada o alan çıkarılamamış) bir eksende sıfır
 * olarak çizilirse, «veri yok» ile «en kötü» aynı görünür — projenin en çok
 * uyardığı hata (bkz. FairnessNotice «0 = ürün yok, ceza değil»). Bu yüzden
 * kapsanmayan eksen çizgiden KOPARILIR (`null` olarak geçilir, Chart.js orada
 * çizgiyi kesmez ama nokta koymaz) ve alt notta adıyla sayılır.
 */

import {
  Chart as ChartJS,
  Filler,
  LineElement,
  PointElement,
  RadialLinearScale,
  Tooltip,
  type ChartOptions,
} from "chart.js";
import { useMemo } from "react";
import { Radar } from "react-chartjs-2";
import type { CompositeScore, WeightRow } from "../../lib/api";
import { useGrafikPaleti } from "../../lib/grafikPaleti";

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip);

type Props = {
  /** Tam olarak iki kayıt; fazlası okunmaz, azı kıyas değildir. */
  skorlar: [CompositeScore, CompositeScore];
  agirliklar: WeightRow[];
  /** Kıyasın yapıldığı kampanya türü — başlıkta ZORUNLU görünür (§17). */
  tur: string;
  /** Alan adı → insan etiketi (`/fields`ten gelir). */
  etiketler?: Record<string, string>;
};

function eksenDegerleri(
  skor: CompositeScore,
  agirliklar: WeightRow[],
): (number | null)[] {
  const harita = new Map(skor.components.map((c) => [c.field_name, c.normalized]));
  return agirliklar.map((a) => harita.get(a.field_name) ?? null);
}

function kapsanmayanlar(
  skor: CompositeScore,
  agirliklar: WeightRow[],
  etiketler?: Record<string, string>,
): string[] {
  const harita = new Map(skor.components.map((c) => [c.field_name, c.normalized]));
  return agirliklar
    .filter((a) => harita.get(a.field_name) == null)
    .map((a) => etiketler?.[a.field_name] ?? a.field_name);
}

export default function RadarKiyas({ skorlar, agirliklar, tur, etiketler }: Props) {
  const palet = useGrafikPaleti();
  const [a, b] = skorlar;

  const veri = useMemo(() => {
    if (!palet) return null;
    return {
      labels: agirliklar.map(
        (w) => `${etiketler?.[w.field_name] ?? w.field_name} (${w.weight.toFixed(2)})`,
      ),
      datasets: [
        {
          label: a.bank_name || a.bank || "—",
          data: eksenDegerleri(a, agirliklar),
          borderColor: palet["--accent"],
          backgroundColor: palet["--accent-wash"],
          pointBackgroundColor: palet["--accent"],
          borderWidth: 2,
        },
        {
          label: b.bank_name || b.bank || "—",
          data: eksenDegerleri(b, agirliklar),
          borderColor: palet["--warn"],
          backgroundColor: "transparent",
          pointBackgroundColor: palet["--warn"],
          borderWidth: 2,
          // İkinci seri kesikli: renk körlüğünde iki çokgeni ayıran ikinci
          // sinyal. Renk asla tek başına ayırt edici olmamalı (WCAG 1.4.1).
          borderDash: [5, 4],
        },
      ],
    };
  }, [palet, a, b, agirliklar, etiketler]);

  if (!palet || !veri) return null;

  const secenekler: ChartOptions<"radar"> = {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    plugins: {
      legend: { display: false }, // Kendi göstergemizi metin olarak çiziyoruz.
      tooltip: {
        backgroundColor: palet["--bg-2"],
        titleColor: palet["--fg"],
        bodyColor: palet["--fg-dim"],
        borderColor: palet["--line"],
        borderWidth: 1,
        callbacks: {
          label: (ctx) =>
            ctx.parsed.r == null
              ? `${ctx.dataset.label}: veri yok`
              : `${ctx.dataset.label}: grup içi ${(ctx.parsed.r * 100).toFixed(0)}%`,
        },
      },
    },
    scales: {
      r: {
        min: 0,
        max: 1,
        angleLines: { color: palet["--line-soft"] },
        grid: { color: palet["--line-soft"] },
        pointLabels: {
          color: palet["--fg-dim"],
          font: { family: palet["--font-sans"], size: 11 },
        },
        ticks: {
          display: false, // 0..1 grup içi konum; sayısal kademe yanıltıcı olurdu.
        },
      },
    },
  };

  const aEksik = kapsanmayanlar(a, agirliklar, etiketler);
  const bEksik = kapsanmayanlar(b, agirliklar, etiketler);

  return (
    <figure className="grafik">
      <figcaption className="grafik-baslik">
        {a.bank_name || a.bank} · {b.bank_name || b.bank}
        <span className="small muted"> — {tur} içinde</span>
      </figcaption>

      <div className="grafik-tuval grafik-tuval-radar">
        <Radar data={veri} options={secenekler} />
      </div>

      {/* Gösterge metin olarak: canvas erişilebilirlik ağacında yok ve
          çokgenleri yalnız renkle ayırmak tek sinyale bağlamak olurdu. */}
      <ul className="grafik-liste small">
        <li>
          <span className="grafik-liste-ad">{a.bank_name || a.bank}</span>
          <span className="mono">düz çizgi</span>
        </li>
        <li>
          <span className="grafik-liste-ad">{b.bank_name || b.bank}</span>
          <span className="mono">kesikli çizgi</span>
        </li>
      </ul>

      <p className="small muted">
        Eksenler <b>{tur}</b> grubu içindeki konumu gösterir, mutlak büyüklüğü
        değil: ham değerler farklı birimlerdedir (oran, tutar, ay) ve aynı eksene
        konamaz. Parantez içindeki sayı o ölçütün ağırlığıdır; gerekçeleri
        aşağıda yazılıdır. Farklı kampanya türleri birbiriyle kıyaslanmaz.
      </p>

      {(aEksik.length > 0 || bEksik.length > 0) && (
        <p className="small muted">
          Kapsanmayan ölçüt <b>sıfır olarak çizilmez</b>, eksende nokta almaz —
          «veri yok» ile «en kötü» aynı şey değildir.
          {aEksik.length > 0 && ` ${a.bank_name || a.bank}: ${aEksik.join(", ")}.`}
          {bEksik.length > 0 && ` ${b.bank_name || b.bank}: ${bEksik.join(", ")}.`}
        </p>
      )}
    </figure>
  );
}
