"use client";

/**
 * Delta ekseni — TEK bankayı ortalayan, artı/eksi yönlü dikey çubuklar.
 *
 * İlgili: ../../lib/api.ts (DeltaField, DeltaKind), ../BankDeltaPanel.tsx,
 *         src/comparison/compare.py `delta_between`,
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
 *    zaten zorunluydu (bkz. KapsamaCetveli başlığı, WCAG 1.4.1).
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
 *  1. Satır içi SVG DOM'da yaşar; `fill="var(--accent)"` DOĞRUDAN çalışır. Canvas'ın
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
 * çizgi üstünde KESİK (dotted) bir taban çizgisiyle ve «eşit» yazısıyla
 * işaretlenir. Dolu bir tırnak, ölçüsü olmayan bir şeye ölçü verirdi.
 *
 * ## Renk tek sinyal değil
 *
 * WCAG 1.4.1: yön ayrıca KONUMLA (çizginin üstü/altı), OKLA (▲/▼) ve yazıyla
 * verilir; her çubuğun değeri ucuna basılır ve grafiğin altındaki liste aynı
 * bilgiyi metin olarak taşır.
 *
 * ## ÜÇ BİÇİM — ve `--warn` artık tek şey söylüyor
 *
 * Çubuklar eskiden yönü RENKLE anlatıyordu: `--ok` yeşil «daha iyi», `--warn`
 * turuncu «daha kötü». Panelin geri kalanında ise `--warn` başka bir şeyin
 * rengi: «ölçülemedi / doğrudan kıyaslanamaz» (§17). Aynı turuncu iki ayrı şeyi
 * söyleyince ikisi de okunmaz oluyordu — kapsama cetvelinde kesikli turuncu
 * «kıyaslanamaz» demek, burada dolu turuncu «geride» demek.
 *
 * Ayrım biçime taşındı ve renk tekilleşti:
 *
 *   dolu mürekkep (`--accent`)        ölçeklenmiş çubuk — yön belli, oran belli
 *   kesikli çerçeve + 135° tarama     yön belli, ORAN HESAPLANAMADI (`--warn`)
 *   kesik (dotted) taban çizgisi      gerçekten eşit — uzunluğu sıfır
 *
 * Yön kaybolmuyor: konumla (eksenin üstü/altı), her çubuğun ucundaki OKLA
 * (▲/▼) ve yazıyla üç kez veriliyor. Renkten çıkan tek şey, renge zaten
 * yüklenemeyecek olan ikinci anlamdı.
 */

import { useId, useMemo } from "react";
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
  // Desen kimliği belge genelinde tekil olmalı: aynı sayfada iki delta ekseni
  // (iki farklı ürün ailesi) yan yana çizilebiliyor ve sabit bir `id` ikincisini
  // birincinin desenine bağlardı. `useId()` çıktısındaki iki nokta üst üste
  // temizleniyor — `url(#…)` başvurusunda tarayıcıya göre sorun çıkarabiliyor.
  const kimlik = useId().replace(/[^a-zA-Z0-9]/g, "");
  const desenId = `delta-tarama-${kimlik}`;

  if (cubuklar.length === 0 && notr.length === 0) return null;

  const enBuyuk = cubuklar.reduce(
    (m, c) => (c.oran !== null && c.oran > m ? c.oran : m),
    0,
  );

  const genislik = SOL + cubuklar.length * ALAN_W;
  const yukseklik = UST + ALT + ETIKET_H;
  const eksenY = UST;
  /**
   * Eğik alan etiketlerinin çapa noktası — etiket bandının ÜSTÜ, dibi değil.
   *
   * ÖLÇÜLDÜ (2026-08-12, tarayıcı): etiketler kırpılıyordu ve ekranda «Vade
   * (ay)» yerine yalnız «ay)», «Tahsis Ücreti» yerine «eti» görünüyordu.
   *
   * Sebep geometrik. Etiket `rotate(-38)` ve `textAnchor="end"` taşıyor; SVG'de
   * negatif açı saat yönünün TERSİ olduğu için yazının okuma yönü yukarı-sağa
   * bakar, `end` çapası ise yazıyı çapadan geriye, yani AŞAĞI-SOLA doğru
   * uzatır. Çapa `yukseklik - 8` ile bandın dibine konmuştu (y=308, band
   * 208–316), dolayısıyla yazının uzanacağı yer viewBox'ın ALTINDA kalıyor ve
   * kırpılıyordu; ayakta kalan tek şey çapaya en yakın son üç harfti.
   *
   * Çapa bandın üstüne alındı. En uzun etiket («Finansman Tutarı», 12px sans,
   * ~100px) 38°'de 0,616 × 100 ≈ 62px aşağı iniyor: 222 + 62 = 284 < 316.
   * Sola uzanma 0,788 × 100 ≈ 79px ve ilk çubuğun ortası 165, yani x ≈ 86 —
   * viewBox içinde. `ETIKET_H` (108) bu hesapla yeterli, büyütmeye gerek yok.
   */
  const etiketY = UST + ALT + 14;

  const ondekiler = cubuklar.filter((c) => c.yon === 1).length;
  const gerideler = cubuklar.filter((c) => c.yon === -1).length;

  return (
    <figure className="grafik">
      <figcaption className="grafik-baslik">
        {bankName} — nerede önde, nerede geride{" "}
        {/* Kampanya türü MAKİNE verisidir (§17: kıyas TÜR İÇİNDE yapılır), bir
            cümle değil — mono. Büyük harfe ÇIKMAZ: büyük harf «bu bir etiket»
            demektir, oysa «Konut Finansmanı» bir değerdir. */}
        <span className="grafik-fisilti">
          {tur ? `tür: ${tur}` : "türü belirlenemeyen belgeler"}
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
            {/* 135° tarama dokusu — «yön belli, oran hesaplanamadı» çubuğunun
                yüzeyi. Kapsama haritasındaki `kosullu` hücreyle AYNI doku ve
                aynı açı; iki ekranda aynı şeyi söylüyorlar. */}
            <defs>
              <pattern
                id={desenId}
                patternUnits="userSpaceOnUse"
                width="8"
                height="8"
                patternTransform="rotate(135)"
              >
                <rect width="8" height="8" fill="var(--bg-2)" />
                <rect width="4" height="8" fill="var(--warn-wash)" />
              </pattern>
            </defs>

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
            {/* Yön yazıyla ve okla veriliyor. Bu iki etiket artık RENK
                TAŞIMIYOR: yeşil/turuncu ayrımı çubuklardan kalktığı için
                göstergede kalması yanlış bir eşleme öğretirdi. */}
            <text
              x={SOL - 14}
              y={16}
              fontSize="12"
              fontFamily="var(--font-sans)"
              fill="var(--fg-dim)"
              textAnchor="end"
            >
              ▲ daha iyi
            </text>
            <text
              x={SOL - 14}
              y={UST + ALT - 6}
              fontSize="12"
              fontFamily="var(--font-sans)"
              fill="var(--fg-dim)"
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
              const y = c.yon === 1 ? eksenY - boy : eksenY;
              const yaziY = c.yon === 1 ? eksenY - boy - 7 : eksenY + boy + 15;
              const ok = c.yon === 1 ? "▲" : "▼";

              return (
                <g key={c.alan}>
                  {c.yon === 0 ? (
                    // Gerçekten eşit: eksende kalır, uzunluğu sıfırdır. Görünmez
                    // olmasın diye KESİK (dotted) bir taban çizgisi alır — dolu
                    // bir tırnak, ölçüsü olmayan bir şeye ölçü verirdi.
                    <line
                      x1={x}
                      y1={eksenY}
                      x2={x + CUBUK_W}
                      y2={eksenY}
                      stroke="var(--fg-faint)"
                      strokeWidth="2"
                      strokeLinecap="round"
                      strokeDasharray="1 3"
                    >
                      <title>{`${c.etiket}: eşit`}</title>
                    </line>
                  ) : (
                    <rect
                      x={x}
                      y={y}
                      width={CUBUK_W}
                      height={boy}
                      /* Köşe: mürekkep çubuğu bir işarettir, kart değil —
                         `--radius-sm` ölçüsünde (4px) kalır. */
                      rx="4"
                      /* Ölçeklenmiş çubuk DOLU MÜREKKEP; ölçeksiz çubuk
                         kesikli çerçeve + 135° tarama. Rakibin değeri 0 olduğu
                         için göreli fark hesaplanmadı: yön belli, büyüklük
                         değil — ve yüzey bunu söylüyor. */
                      fill={olceksiz ? `url(#${desenId})` : "var(--accent)"}
                      stroke={olceksiz ? "var(--warn)" : "none"}
                      strokeWidth={olceksiz ? 1 : 0}
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
                  {/* Değerin yanındaki ok: yön ARTIK RENKTE DEĞİL, o yüzden her
                      çubuk kendi yönünü kendi taşımalı — göstergeye bakmak
                      zorunda kalmadan. */}
                  <text
                    x={orta}
                    y={c.yon === 0 ? eksenY - 8 : yaziY}
                    fontSize="11"
                    fontFamily="var(--font-mono)"
                    fill="var(--fg-dim)"
                    textAnchor="middle"
                    aria-hidden="true"
                  >
                    {c.yon === 0 ? c.metin : `${ok} ${c.metin}`}
                  </text>
                  {/* Alan adları eğik: «Kâr Payı Oranı» 82px'e sığmıyor ve
                      kısaltmak jüriye tanımadığı bir kısaltma öğretmek olurdu.
                      Çapa etiket bandının ÜSTÜNDE: -38° döndürülmüş ve sonu
                      hizalanmış bir yazı çapadan AŞAĞI-SOLA uzanır (gerekçe
                      ve ölçüm `etiketY` tanımında). Eskiden çapa bandın
                      dibindeydi ve yazı viewBox'ın altına düşüp kırpılıyordu. */}
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
              <span className="grafik-liste-deger">{c.metin}</span>
            </li>
          ))}
        </ul>
      )}

      <p className="grafik-gerekce">
        Çubuğun boyu <b>göreli farktır</b> (%), mutlak fark değil: puan, ay ve TL
        aynı eksene konamaz. Mutlak farklar aşağıdaki tabloda alan alan durur.
        Dolu mürekkep çubuk ölçülmüş bir oranı gösterir; <b>kesikli ve taramalı</b>{" "}
        çubuk «yön belli, oran hesaplanamadı» demektir — rakibin değeri sıfır
        olduğunda göreli fark tanımsızdır. <b>Kesik taban çizgisi</b> ise gerçek
        bir eşitliktir: uzunluğu sıfırdır çünkü fark sıfırdır.
      </p>

      {notr.length > 0 && (
        <div className="delta-notr">
          <p className="grafik-gerekce">
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
