"use client";

/**
 * Delta ekseni — TEK bankayı ortalayan, artı/eksi yönlü dikey çubuklar.
 *
 * İlgili: ../../lib/api.ts (DeltaField, DeltaKind), ../BankDeltaPanel.tsx,
 *         ./KiyasCubuklari.tsx, src/comparison/compare.py `delta_between`,
 *         CLAUDE.md §17 (adil kıyas garantisi)
 *
 * ## Kıyas YATAY, delta DİKEY — ve asıl mesele bu
 *
 * Toplantıda «iki ekran da çubuk gösteriyor, farkı ne» diye soruldu. İkisi aynı
 * veriyi okuyor ama iki ayrı soruya cevap veriyor ve bunu görsel dilbilgisiyle
 * söylemeleri gerekiyor:
 *
 *  - **Kıyas (yatay):** bankalar alt alta, hepsi eşit statüde, göz yukarıdan
 *    aşağı bir SIRALAMA okur. Etiketler banka adları olduğu için yatay çubuk
 *    zaten zorunluydu (bkz. KiyasCubuklari başlığı).
 *  - **Delta (dikey):** ekranda tek bir banka var, o da eksenin KENDİSİ. Sıfır
 *    çizgisi «bu banka»dır; yukarı çıkan alanlarda önde, aşağı inenlerde geride.
 *    Göz bir sıralama değil, bir DENGE okur.
 *
 * İki zihinsel model, tek veri kümesi. Jürinin iki ekranı birbirine
 * karıştırmaması buna bağlı.
 *
 * ## Neden elle SVG, Chart.js değil
 *
 * IsiHaritasi'ndaki gerekçenin aynısı (bkz. o dosyanın başlığı) burada da
 * geçerli ve bir tanesi ekleniyor:
 *
 *  1. Satır içi SVG DOM'da yaşar; `fill="var(--ok)"` DOĞRUDAN çalışır. Canvas'ın
 *     CSS özel niteliklerini okuyamaması sorunu (bkz. lib/grafikPaleti.ts)
 *     tümüyle ortadan kalkar — tema değişimi bedava, palet çözme adımı yok.
 *  2. `<title>` taşıyan `rect`'ler erişilebilirlik ağacında görünür.
 *  3. **Ölçeklenemeyen çubuk KESİKLİ çizilir.** Göreli fark rakibin değeri 0
 *     iken hesaplanmaz (`delta_between`), yani yön bellidir ama büyüklük
 *     değildir. Chart.js'te tek bir çubuğu «ölçeksiz» diye işaretlemenin temiz
 *     bir yolu yok; SVG'de tek nitelik.
 *
 * ## Çubuğun uzunluğu GÖRELİ farktır
 *
 * Mutlak farklar farklı birimlerdedir (puan, ay, TL) ve aynı eksene konamaz —
 * §17'nin «yalnız aynı birime normalize alanlar kıyaslanır» kuralı grafiğe de
 * aynen uygulanır. Bu yüzden uzunluk `rel_pct`'tir; mutlak fark yazıyla, alan
 * alan tabloda durur.
 *
 * ## Sıfır uzunluk «eşit» demek değildir
 *
 * `kiyaslanamaz`, `eksik_veri`, `eksik_urun` ve `rakip_yok` durumlarında bir
 * sayı YOKTUR. Bunları eksende sıfır uzunlukta çizmek, tam da projenin en çok
 * uyardığı yalanı söylerdi: «ölçemedik» ile «eşit» aynı görünürdü. Bu dört
 * durum kendi NÖTR ŞERİDİNE düşer, adıyla ve gerekçesiyle.
 *
 * `esit` ise gerçekten sıfırdır ve eksende kalır — ama görünmez olmasın diye
 * çizgi üstünde nötr renkli bir tırnakla ve «eşit» yazısıyla işaretlenir.
 *
 * ## Renk tek sinyal değil
 *
 * WCAG 1.4.1: yön ayrıca KONUMLA (çizginin üstü/altı), OKLA (▲/▼) ve yazıyla
 * verilir; her çubuğun değeri ucuna basılır ve grafiğin altındaki liste aynı
 * bilgiyi metin olarak taşır.
 */

import { useMemo } from "react";
import type { DeltaField, DeltaKind } from "../../lib/api";
import { trNum } from "../../lib/format";

type Props = {
  alanlar: DeltaField[];
  /** Eksenin ortasındaki banka — grafiğin öznesi. */
  bankName: string;
  /** Kıyasın yapıldığı kampanya türü; başlıkta görünür (§17). */
  tur: string | null;
  /**
   * Durum → etiket sözlüğü. Bilerek DIŞARIDAN geliyor: `BankDeltaPanel` aynı
   * enum'ı üç ayrı sözlüğe dağıtmaktan yeni kurtuldu, burada dördüncüsünü
   * açmak o düzeltmeyi geri almak olurdu.
   */
  durumlar: Record<DeltaKind, { label: string }>;
};

/** Eksende yeri olan üç durum; gerisi nötr şeride düşer. */
const EKSENDE: ReadonlySet<DeltaKind> = new Set<DeltaKind>([
  "daha_iyi",
  "daha_kotu",
  "esit",
]);

type Cubuk = {
  alan: string;
  etiket: string;
  /** 1 = önde, -1 = geride, 0 = eşit. */
  yon: 1 | -1 | 0;
  /** Göreli fark (%). `null` = yön belli, büyüklük hesaplanamadı. */
  oran: number | null;
  metin: string;
};

/* --- ölçüler (SVG kullanıcı birimi; viewBox ile ölçeklenir) --- */
const SOL = 124;
const ALAN_W = 82;
const CUBUK_W = 28;
const UST = 104;
const ALT = 104;
const ETIKET_H = 108;
const EN_UZUN = 86;
/** Ölçeklenemeyen (kesikli) çubuğun sabit boyu. */
const OLCEKSIZ = 24;
/** Görünürlük tabanı: %0,3'lük bir fark da bir piksel almalı. */
const EN_KISA = 4;

function yonu(kind: DeltaKind): 1 | -1 | 0 {
  if (kind === "daha_iyi") return 1;
  if (kind === "daha_kotu") return -1;
  return 0;
}

function cubuklariKur(alanlar: DeltaField[]): {
  cubuklar: Cubuk[];
  notr: DeltaField[];
} {
  const cubuklar: Cubuk[] = [];
  const notr: DeltaField[] = [];

  for (const f of alanlar) {
    if (!EKSENDE.has(f.kind)) {
      notr.push(f);
      continue;
    }
    const yon = yonu(f.kind);
    const oran = f.rel_pct === null ? null : Math.abs(f.rel_pct);
    cubuklar.push({
      alan: f.field,
      etiket: f.label,
      yon,
      oran,
      metin:
        yon === 0
          ? "eşit"
          : oran === null
            ? "oran yok"
            : `%${trNum(oran)}`,
    });
  }

  return { cubuklar, notr };
}

export default function DeltaEkseni({ alanlar, bankName, tur, durumlar }: Props) {
  const { cubuklar, notr } = useMemo(() => cubuklariKur(alanlar), [alanlar]);

  if (cubuklar.length === 0 && notr.length === 0) return null;

  const enBuyuk = cubuklar.reduce(
    (m, c) => (c.oran !== null && c.oran > m ? c.oran : m),
    0,
  );

  const genislik = SOL + cubuklar.length * ALAN_W;
  const yukseklik = UST + ALT + ETIKET_H;
  const eksenY = UST;
  const etiketY = yukseklik - 8;

  const ondekiler = cubuklar.filter((c) => c.yon === 1).length;
  const gerideler = cubuklar.filter((c) => c.yon === -1).length;

  return (
    <figure className="grafik">
      <figcaption className="grafik-baslik">
        {bankName} — nerede önde, nerede geride
        <span className="small muted">
          {" "}
          — {tur ? `kampanya türü: ${tur}` : "türü belirlenemeyen belgeler"}
        </span>
      </figcaption>

      {cubuklar.length > 0 && (
        <div className="table-wrap">
          <svg
            viewBox={`0 0 ${genislik} ${yukseklik}`}
            width="100%"
            role="img"
            aria-label={
              `${bankName} için artı/eksi delta ekseni. ` +
              `${ondekiler} alanda önde, ${gerideler} alanda geride, ` +
              `${cubuklar.length - ondekiler - gerideler} alanda eşit.`
            }
            style={{ maxWidth: genislik, height: "auto" }}
          >
            {/* Sıfır çizgisi = seçilen bankanın kendisi. Grafiğin öznesi bir
                çubuk değil, EKSENDİR. */}
            <line
              x1={SOL - 96}
              y1={eksenY}
              x2={genislik}
              y2={eksenY}
              stroke="var(--line)"
              strokeWidth="1"
            />
            <text
              x={SOL - 14}
              y={eksenY - 4}
              fontSize="12"
              fontFamily="var(--font-sans)"
              fill="var(--fg)"
              textAnchor="end"
            >
              {bankName}
            </text>
            {/* Yön yazıyla ve okla da veriliyor; renk tek sinyal değil. */}
            <text
              x={SOL - 14}
              y={16}
              fontSize="12"
              fontFamily="var(--font-sans)"
              fill="var(--ok)"
              textAnchor="end"
            >
              ▲ daha iyi
            </text>
            <text
              x={SOL - 14}
              y={UST + ALT - 6}
              fontSize="12"
              fontFamily="var(--font-sans)"
              fill="var(--warn)"
              textAnchor="end"
            >
              ▼ daha kötü
            </text>

            {cubuklar.map((c, i) => {
              const x = SOL + i * ALAN_W + (ALAN_W - CUBUK_W) / 2;
              const orta = x + CUBUK_W / 2;
              const olceksiz = c.yon !== 0 && c.oran === null;
              const boy = olceksiz
                ? OLCEKSIZ
                : c.oran === null || enBuyuk <= 0
                  ? EN_KISA
                  : Math.max(EN_KISA, (c.oran / enBuyuk) * EN_UZUN);
              const renk = c.yon === 1 ? "var(--ok)" : "var(--warn)";
              const y = c.yon === 1 ? eksenY - boy : eksenY;
              const yaziY = c.yon === 1 ? eksenY - boy - 7 : eksenY + boy + 15;

              return (
                <g key={c.alan}>
                  {c.yon === 0 ? (
                    // Gerçekten eşit: eksende kalır ama görünmez olmasın diye
                    // nötr bir tırnak alır. Ölçüsü sıfırdır, iddiası da.
                    <rect
                      x={x}
                      y={eksenY - 2}
                      width={CUBUK_W}
                      height="4"
                      rx="2"
                      fill="var(--line)"
                    >
                      <title>{`${c.etiket}: eşit`}</title>
                    </rect>
                  ) : (
                    <rect
                      x={x}
                      y={y}
                      width={CUBUK_W}
                      height={boy}
                      rx="2"
                      fill={olceksiz ? "none" : renk}
                      stroke={renk}
                      strokeWidth={olceksiz ? 1 : 0}
                      /* Kesikli = ölçeğe göre çizilmedi. Rakibin değeri 0
                         olduğu için göreli fark hesaplanmadı; yön belli,
                         büyüklük değil. */
                      strokeDasharray={olceksiz ? "3 3" : undefined}
                    >
                      <title>
                        {`${c.etiket}: ${c.yon === 1 ? "daha iyi" : "daha kötü"}` +
                          (olceksiz
                            ? " — göreli fark hesaplanamadı"
                            : `, göreli ${c.metin}`)}
                      </title>
                    </rect>
                  )}
                  <text
                    x={orta}
                    y={c.yon === 0 ? eksenY - 8 : yaziY}
                    fontSize="11"
                    fontFamily="var(--font-mono)"
                    fill="var(--fg-dim)"
                    textAnchor="middle"
                    aria-hidden="true"
                  >
                    {c.metin}
                  </text>
                  {/* Alan adları eğik: «Kâr payı oranı» 82px'e sığmıyor ve
                      kısaltmak jüriye tanımadığı bir kısaltma öğretmek olurdu.
                      Taban çizgisi etiket bandının EN ALTINDA: -38° döndürülmüş
                      ve sonu hizalanmış bir yazı yukarı-sola uzanır, yani
                      taban yukarıda olsaydı aşağı inen çubukların üstüne
                      binerdi. */}
                  <text
                    x={orta}
                    y={etiketY}
                    transform={`rotate(-38 ${orta} ${etiketY})`}
                    fontSize="12"
                    fontFamily="var(--font-sans)"
                    fill="var(--fg-dim)"
                    textAnchor="end"
                  >
                    {c.etiket}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      )}

      {/* Grafiğin erişilebilir eşi — bir yedek değil, aynı bilginin metin
          hâli. SVG `<title>`'ları bile okunmasa bu liste tek başına yeter. */}
      {cubuklar.length > 0 && (
        <ul className="grafik-liste small">
          {cubuklar.map((c) => (
            <li key={c.alan}>
              <span className="grafik-liste-ad">{c.etiket}</span>
              <span>
                {c.yon === 1 ? "daha iyi" : c.yon === -1 ? "daha kötü" : "eşit"}
              </span>
              <span className="mono">{c.metin}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="small muted">
        Çubuğun boyu <b>göreli farktır</b> (%), mutlak fark değil: puan, ay ve TL
        aynı eksene konamaz. Mutlak farklar aşağıdaki tabloda alan alan durur.
        Kesikli çubuk «yön belli, oran hesaplanamadı» demektir — rakibin değeri
        sıfır olduğunda göreli fark tanımsızdır.
      </p>

      {notr.length > 0 && (
        <div className="delta-notr">
          <p className="small muted">
            Aşağıdaki alanlar <b>eksene yerleştirilmez</b>. Sıfır uzunlukta bir
            çubuk «eşit» diye okunurdu; oysa burada söylenen «ölçülemedi».
          </p>
          <ul className="grafik-liste small">
            {notr.map((f) => (
              <li key={f.field}>
                <span className="grafik-liste-ad">{f.label}</span>
                <span>{durumlar[f.kind].label}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </figure>
  );
}
