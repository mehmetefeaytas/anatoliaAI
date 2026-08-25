"use client";

/**
 * Bilgiler Paneli — korpusun genel bakışı.
 *
 * İlgili: ../lib/api.ts `Stats` (`GET /stats`), ../styles/bilgiler.css,
 *         ../styles/tokens.css (`--chart-1..7`, `--chart-neutral`)
 *
 * ## Neden bu sekme var
 *
 * `KorpusKunyesi` (page.tsx) her ekranda görünen ince bir çip şeridi — "kaç
 * belge, kaç banka" der ama "hangi türden" sorusuna cevap vermez. `Karşılaştırma`
 * sekmesi ise BİLEREK tek kampanya türü çizer (§17 adil kıyas — türler arası
 * sıralama yasak) ve bankaları konu alır. Bu ikisinin arasında boş bir soru
 * kalıyordu: "korpusta elimde ne var, hangi ürün ailesi ne kadar yer tutuyor" —
 * bir BANKA sorusu değil, bir KORPUS sorusu. Bu sekme onu yanıtlar.
 *
 * ## Pasta/donut, çubuk değil — bilinçli sapma
 *
 * Genel kural parça-bütün dağılımları için yığın çubuğu önerir (bkz. dataviz
 * becerisi, `choosing-a-form.md`). Burada donut BİLEREK seçildi: istek net bir
 * referans örnekle geldi (rakip bir panelin "Kampanya Türü Dağılımı" pastası,
 * gri dilim = "Belirtilmemiş") ve 7 gerçek tür + 1 "veri yok" kovası bu ölçekte
 * bir donutta okunaklı kalıyor (8 dilim, hiçbiri < %0,3 dışında küçük değil).
 *
 * ## Renkler — banka rengi DEĞİL
 *
 * `tokens.css`teki `--accent` yorumunun uyardığı şey burada geçerli DEĞİL: o
 * uyarı bankaları birbirinden ayıran bir BANKA KIYASI için ("hangi banka hangi
 * rengi giyer") — bu grafik bankaları değil ÜRÜN AİLESİNİ (banka-bağımsız bir
 * kategori) ayırıyor. Yedi renk `--chart-1..7`, dataviz becerisinin doğrulanmış
 * varsayılan paletinden (sırası CVD-güvenlik mekanizması, kozmetik değil).
 * "Belirtilmemiş" bu yedinin DIŞINDA, ayrı bir nötr gri (`--chart-neutral`)
 * alır — bir kategori değil, "kaynakta tür yok" sinyali.
 *
 * ## Erişilebilirlik — SVG dekoratif, gerçek metin YEDEK DEĞİL
 *
 * `grafik.css`teki eski not ("canvas erişilebilirlik ağacında yok, liste bir
 * yedek değil") burada da geçerli — ama farklı sebeple: SVG teknik olarak DOM
 * ağacındadır, ama her dilimi tek tek `aria-label`lamak "Mavi dilim, Kart,
 * yüz elli bir belge" gibi okunması zor bir gezinme üretirdi. Bunun yerine SVG
 * `aria-hidden` işaretlenir ve ekranın ASIL bilgisi zaten gerçek metin olan
 * lejantta durur (etiket + sayı + yüzde, sıralı bir liste).
 *
 * Dilim üstü doğrudan etiket YOK (dataviz "seçici doğrudan etiket" kuralının
 * bilinçli istisnası): metin her zaman `--fg`/`--fg-dim` taşımalı ("metin seri
 * rengini giymez") ve bunu değişken doygunluktaki 7 dolgunun ÜSTÜNE okunaklı
 * biçimde koymak garanti edilemezdi. Lejant + gezinme ipucu (`<title>`) aynı
 * bilgiyi garantili kontrastla taşıyor.
 */

import { useMemo, useState } from "react";
import type { Bank, FieldMeta, Stats } from "../lib/api";
import { trNum } from "../lib/format";
import GrafikIskeleti from "./grafik/GrafikIskeleti";

/** Doğrulanmış kategorik palet — sıra CVD-güvenlik mekanizması (bkz. dosya başlığı). */
const DILIM_RENKLERI = [
  "var(--chart-1)",
  "var(--chart-2)",
  "var(--chart-3)",
  "var(--chart-4)",
  "var(--chart-5)",
  "var(--chart-6)",
  "var(--chart-7)",
] as const;

const BELIRTILMEMIS_ETIKET = "Belirtilmemiş";

type Dilim = {
  etiket: string;
  sayi: number;
  yuzde: number;
  renk: string;
  belirtilmemis: boolean;
};

/** Sayım sözlüğünden dilim listesi üretir: gerçek türler SAYIYA göre azalan,
 *  "Belirtilmemiş" (varsa) her zaman EN SONDA — bir kategori değil, bir
 *  eksiklik sinyali; sıralamaya girip büyük bir tür gibi öne çıkmamalı. */
function dilimleriHesapla(counts: Record<string, number>): Dilim[] {
  const toplam = Object.values(counts).reduce((a, b) => a + b, 0);
  if (toplam <= 0) return [];

  const belirtilmemisSayi = counts[BELIRTILMEMIS_ETIKET] ?? 0;
  const gercekTurler = Object.entries(counts)
    .filter(([etiket]) => etiket !== BELIRTILMEMIS_ETIKET)
    .sort((a, b) => b[1] - a[1]);

  const dilimler: Dilim[] = gercekTurler.map(([etiket, sayi], i) => ({
    etiket,
    sayi,
    yuzde: (sayi / toplam) * 100,
    renk: DILIM_RENKLERI[i % DILIM_RENKLERI.length],
    belirtilmemis: false,
  }));

  if (belirtilmemisSayi > 0) {
    dilimler.push({
      etiket: BELIRTILMEMIS_ETIKET,
      sayi: belirtilmemisSayi,
      yuzde: (belirtilmemisSayi / toplam) * 100,
      renk: "var(--chart-neutral)",
      belirtilmemis: true,
    });
  }
  return dilimler;
}

/** Açıyı SVG koordinatına çevirir. 0° = 12 yönü (saat başı), saat yönünde artar. */
function kutupselKoordinat(
  cx: number,
  cy: number,
  r: number,
  aciDerece: number,
): { x: number; y: number } {
  const aciRad = ((aciDerece - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(aciRad), y: cy + r * Math.sin(aciRad) };
}

/** Bir donut diliminin path'i — dış yay + iç yay, ikisi arasında düz kenar. */
function dilimYolu(
  cx: number,
  cy: number,
  rDis: number,
  rIc: number,
  baslangicDerece: number,
  bitisDerece: number,
): string {
  const buyukYay = bitisDerece - baslangicDerece <= 180 ? 0 : 1;
  const disBaslangic = kutupselKoordinat(cx, cy, rDis, bitisDerece);
  const disBitis = kutupselKoordinat(cx, cy, rDis, baslangicDerece);
  const icBaslangic = kutupselKoordinat(cx, cy, rIc, baslangicDerece);
  const icBitis = kutupselKoordinat(cx, cy, rIc, bitisDerece);
  return [
    `M ${disBaslangic.x} ${disBaslangic.y}`,
    `A ${rDis} ${rDis} 0 ${buyukYay} 0 ${disBitis.x} ${disBitis.y}`,
    `L ${icBaslangic.x} ${icBaslangic.y}`,
    `A ${rIc} ${rIc} 0 ${buyukYay} 1 ${icBitis.x} ${icBitis.y}`,
    "Z",
  ].join(" ");
}

/** `%1,9` gibi TR biçimli yüzde — `Intl.NumberFormat` yerine `toLocaleString`:
 *  ikisi eşdeğer, tercih saf stilistik. */
function yuzdeYaz(yuzde: number): string {
  const yazi = yuzde.toLocaleString("tr-TR", {
    minimumFractionDigits: 1,
    maximumFractionDigits: 1,
  });
  return `%${yazi}`;
}

const R_DIS = 42;
const R_IC = 26;
/** Dilimler arası boşluk (derece). Çok küçük dilimde boşluk dilimi yutmasın diye
 *  dilim genişliğinin dörtte biriyle sınırlanır. */
const BOSLUK_DERECE = 1.4;

function KampanyaTuruDonut({
  counts,
}: {
  counts: Record<string, number>;
}) {
  const [aktifDilim, setAktifDilim] = useState<number | null>(null);
  const dilimler = useMemo(() => dilimleriHesapla(counts), [counts]);
  const toplam = useMemo(
    () => dilimler.reduce((a, d) => a + d.sayi, 0),
    [dilimler],
  );

  if (dilimler.length === 0) return null;

  let birikenDerece = 0;
  const yaylar = dilimler.map((d) => {
    const genislik = (d.yuzde / 100) * 360;
    const bosluk = Math.min(BOSLUK_DERECE, genislik / 4);
    const baslangic = birikenDerece + bosluk / 2;
    const bitis = birikenDerece + genislik - bosluk / 2;
    birikenDerece += genislik;
    return { ...d, baslangic, bitis: Math.max(bitis, baslangic) };
  });

  return (
    <div className="donut-satir">
      <div className="donut-govde">
        <svg
          viewBox="0 0 100 100"
          className="donut-svg"
          aria-hidden="true"
          role="presentation"
        >
          <circle
            cx="50"
            cy="50"
            r={(R_DIS + R_IC) / 2}
            fill="none"
            stroke="var(--line-soft)"
            strokeWidth={R_DIS - R_IC}
          />
          {yaylar.map((a, i) => (
            <path
              key={a.etiket}
              d={dilimYolu(50, 50, R_DIS, R_IC, a.baslangic, a.bitis)}
              fill={a.renk}
              className={
                aktifDilim === null || aktifDilim === i
                  ? "donut-dilim"
                  : "donut-dilim donut-dilim-soluk"
              }
              onMouseEnter={() => setAktifDilim(i)}
              onMouseLeave={() => setAktifDilim(null)}
            >
              <title>
                {`${a.etiket}: ${trNum(a.sayi)} kampanya (${yuzdeYaz(a.yuzde)})`}
              </title>
            </path>
          ))}
        </svg>
        <div className="donut-merkez" aria-hidden="true">
          <span className="donut-merkez-sayi">{trNum(toplam)}</span>
          <span className="donut-merkez-etiket">kampanya</span>
        </div>
      </div>

      {/* Lejant — grafiğin ASIL erişilebilir hâli (bkz. dosya başlığı). Her
          satır kendi diliminin üstüne gelince (`onMouseEnter`) grafikte o
          dilimi vurgular; fare/klavye dinlemesi iki yönlü çalışır. */}
      <ul className="donut-lejant" aria-label="Kampanya türü dağılımı">
        {dilimler.map((d, i) => (
          <li
            key={d.etiket}
            className={
              aktifDilim === null || aktifDilim === i
                ? "donut-lejant-satir"
                : "donut-lejant-satir donut-lejant-satir-soluk"
            }
            onMouseEnter={() => setAktifDilim(i)}
            onMouseLeave={() => setAktifDilim(null)}
          >
            <span
              className="donut-renk-ornegi"
              style={{ background: d.renk }}
              aria-hidden="true"
            />
            <span className="donut-lejant-etiket">
              {d.etiket}
              {d.belirtilmemis && (
                <span className="donut-lejant-not">
                  {" "}
                  — kampanya türü kaynakta belirtilmemiş
                </span>
              )}
            </span>
            <span className="donut-lejant-sayi mono">{trNum(d.sayi)}</span>
            <span className="donut-lejant-yuzde mono">{yuzdeYaz(d.yuzde)}</span>
          </li>
        ))}
      </ul>
      <p className="small muted" style={{ margin: "var(--sp-2) 0 0" }}>
        Yalnız kampanya belgeleri sayılır (sözleşmeler hariç — kampanya türü
        onlarda tanımsızdır). Kaynak: <span className="mono">GET /stats</span>{" "}
        → <span className="mono">campaign_type_counts</span>.
      </p>
    </div>
  );
}

/** Sayaç grid'i — mevcut `.stats`/`.stat` sınıfını (components.css) kullanır;
 *  bu ekrana özel yeni bir "kart" ailesi icat edilmedi. */
function SayacGrubu({
  baslik,
  girdiler,
}: {
  baslik: string;
  girdiler: readonly [etiket: string, deger: number | null][];
}) {
  return (
    <div className="bilgiler-blok">
      <h3>{baslik}</h3>
      <div className="stats">
        {girdiler.map(([etiket, deger]) => (
          <div className="stat" key={etiket}>
            <div className="k">{etiket}</div>
            <div className="v">{deger === null ? "—" : trNum(deger)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

type AlanSatiri = { field: string; label: string; sayi: number; yuzde: number };

/** `alan_kapsami` sözlüğünü sıralı satırlara çevirir — SAYIYA göre azalan.
 *  `/stats` 12 alanın TÜMÜNÜ (sıfır dahil) döndürür, o yüzden bir alan
 *  eksik görünmez. Etiket `/fields`ten gelir; liste henüz yüklenmediyse ham
 *  alan adı gösterilir — uydurma etiket YOK. Yüzde `toplamKampanya`
 *  (`korpus.campaigns`) üzerindendir, kampanya türü sayısı değil. */
function alanKapsamiSiraliHesapla(
  alanKapsami: Record<string, number>,
  fieldLabels: Record<string, string>,
  toplamKampanya: number,
): AlanSatiri[] {
  return Object.entries(alanKapsami)
    .map(([field, sayi]) => ({
      field,
      label: fieldLabels[field] ?? field,
      sayi,
      yuzde: toplamKampanya > 0 ? (sayi / toplamKampanya) * 100 : 0,
    }))
    .sort((a, b) => b.sayi - a.sayi);
}

/** Alan kapsamı tablosu — 12 alanın TÜMÜ, büyükten küçüğe. Mevcut
 *  `table.data`/`table-wrap` deseni yeniden kullanılır (bkz.
 *  UrunTablosuPanel.tsx) — bu ekrana özel yeni bir tablo ailesi icat
 *  edilmedi. */
function AlanKapsamiTablosu({
  satirlar,
  toplamKampanya,
}: {
  satirlar: AlanSatiri[];
  toplamKampanya: number;
}) {
  if (satirlar.length === 0) return null;
  return (
    <div className="bilgiler-blok">
      <h3>Alan Kapsamı</h3>
      <p className="small muted" style={{ marginTop: 0 }}>
        Şartnamenin 12 alanının her biri kaç kampanyada çıkarılabildi —
        yüzde {trNum(toplamKampanya)} kampanya üzerinden.
      </p>
      <div className="table-wrap">
        <table className="data stackable">
          <thead>
            <tr>
              <th scope="col">Alan</th>
              <th scope="col" className="num">
                Belge
              </th>
              <th scope="col" className="num">
                Kapsam
              </th>
            </tr>
          </thead>
          <tbody>
            {satirlar.map((s) => (
              <tr key={s.field}>
                <td>{s.label}</td>
                <td className="num mono">{trNum(s.sayi)}</td>
                <td className="num mono">{yuzdeYaz(s.yuzde)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted" style={{ margin: "var(--sp-2) 0 0" }}>
        Kaynak: <span className="mono">GET /stats</span> →{" "}
        <span className="mono">alan_kapsami</span>; etiketler{" "}
        <span className="mono">GET /fields</span>&apos;ten.
      </p>
    </div>
  );
}

/** Yapılandırılmış kapsam oranı — tek bir stat-tile, mevcut `.stats`/`.stat`
 *  sınıfını (components.css) kullanır. Ham sayılar da altında yazılır: tek
 *  bir yüzdeye indirmek "en az bir alan çıkarılan kampanya" ile "tam
 *  doldurulmuş kampanya"yı karıştırma riskini taşır, o yüzden cümle açık. */
function YapilandirilmisKapsam({
  campaigns,
  campaignsWithFields,
}: {
  campaigns: number;
  campaignsWithFields: number;
}) {
  const oran = campaigns > 0 ? (campaignsWithFields / campaigns) * 100 : null;
  return (
    <div className="bilgiler-blok">
      <h3>Yapılandırılmış Kapsam</h3>
      <div className="stats">
        <div className="stat">
          <div className="k">en az bir alan çıkarılan kampanya</div>
          <div className="v">{oran === null ? "—" : yuzdeYaz(oran)}</div>
        </div>
      </div>
      <p className="small muted" style={{ margin: "var(--sp-2) 0 0" }}>
        {trNum(campaignsWithFields)} / {trNum(campaigns)} kampanyadan en az
        bir alan çıkarılabildi. Kaynak: <span className="mono">GET /stats</span>{" "}
        → <span className="mono">korpus.campaigns_with_fields</span> /{" "}
        <span className="mono">korpus.campaigns</span>.
      </p>
    </div>
  );
}

type BankaSatiri = { slug: string; ad: string; sayi: number };

/** `banka_basina` sözlüğünü sıralı satırlara çevirir. Ad `/banks`ten gelir;
 *  banka kataloğunda karşılığı yoksa slug ham gösterilir. */
function bankaBasinaSiraliHesapla(
  bankaBasina: Record<string, number>,
  bankaAdlari: Record<string, string>,
): BankaSatiri[] {
  return Object.entries(bankaBasina)
    .map(([slug, sayi]) => ({ slug, ad: bankaAdlari[slug] ?? slug, sayi }))
    .sort((a, b) => b.sayi - a.sayi);
}

/** Banka başına belge mini özeti — aynı `table.data` deseni. */
function BankaBasinaTablosu({ satirlar }: { satirlar: BankaSatiri[] }) {
  if (satirlar.length === 0) return null;
  return (
    <div className="bilgiler-blok">
      <h3>Banka Başına Belge</h3>
      <div className="table-wrap">
        <table className="data stackable">
          <thead>
            <tr>
              <th scope="col">Banka</th>
              <th scope="col" className="num">
                Kampanya
              </th>
            </tr>
          </thead>
          <tbody>
            {satirlar.map((s) => (
              <tr key={s.slug}>
                <td>{s.ad}</td>
                <td className="num mono">{trNum(s.sayi)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="small muted" style={{ margin: "var(--sp-2) 0 0" }}>
        Kaynak: <span className="mono">GET /stats</span> →{" "}
        <span className="mono">banka_basina</span>; banka adları{" "}
        <span className="mono">GET /banks</span>&apos;ten.
      </p>
    </div>
  );
}

/** Kapsam tablosunda gösterilecek üç alan — şartnamenin sık aranan
 *  oran/tutar/vade alanlarının ÖTESİNDEKİ üç alan. Sayılar `alan_kapsami`
 *  ile TAMAMEN aynı kaynaktan gelir; burada iddia edilen tek şey korpusun bu
 *  üç alanı da çıkarabildiği — başka bir takımla kıyas YAPILMAZ (kaynaksız
 *  iddia yasak, bkz. CLAUDE.md). */
const EK_ALAN_ADLARI = ["tahsis_ucreti", "hedef_kitle", "taksit_sayisi"] as const;

function EkVeriAlanlariKutusu({ satirlar }: { satirlar: AlanSatiri[] }) {
  const sozluk = useMemo(
    () => new Map(satirlar.map((s) => [s.field, s])),
    [satirlar],
  );
  const secili = EK_ALAN_ADLARI.map((field) => sozluk.get(field)).filter(
    (s): s is AlanSatiri => s !== undefined,
  );
  if (secili.length === 0) return null;
  return (
    <div className="bilgiler-blok">
      <h3>Ek Veri Alanları</h3>
      <p className="small muted" style={{ marginTop: 0 }}>
        Şartnamenin sık aranan oran/tutar/vade alanlarının ötesinde, korpus
        bu üç alanı da çıkarabiliyor — sayılar yukarıdaki alan kapsamı
        tablosuyla aynı kaynaktan.
      </p>
      <div className="stats">
        {secili.map((s) => (
          <div className="stat" key={s.field}>
            <div className="k">{s.label}</div>
            <div className="v">{trNum(s.sayi)}</div>
            <div className="small muted" style={{ marginTop: "var(--sp-1)" }}>
              {yuzdeYaz(s.yuzde)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

type Props = {
  stats: Stats | null;
  yukleniyor: boolean;
  /** `/fields` — alan Türkçe etiketleri. Yoksa (henüz yüklenmedi/hata) alan
   *  kapsamı tablosu ham alan adını gösterir; uydurma etiket YOK. */
  fields?: FieldMeta[] | null;
  /** `/banks` — banka adları. Yoksa banka başına tablo slug gösterir. */
  banks?: Bank[] | null;
};

export default function BilgilerPanel({
  stats,
  yukleniyor,
  fields,
  banks,
}: Props) {
  if (yukleniyor && !stats) {
    return (
      <section className="card">
        <h2>Bilgiler</h2>
        <GrafikIskeleti yukseklik={280} />
      </section>
    );
  }
  if (!stats) return null;

  const belgeTuru = stats.belge_turu ?? {};
  const durum = stats.campaign_status ?? {};
  const katman = stats.katman ?? {};
  const toplamKampanya = Object.values(
    stats.campaign_type_counts ?? {},
  ).reduce((a, b) => a + b, 0);

  // Alan Türkçe etiketleri — `/fields`ten. Liste henüz gelmediyse boş kalır
  // ve tablo ham alan adını gösterir (uydurma etiket YOK, bkz. bileşen üstü).
  const alanEtiketleri: Record<string, string> = {};
  for (const f of fields ?? []) alanEtiketleri[f.field] = f.label;

  // Banka adları — `/banks`ten. Katalogda karşılığı yoksa slug ham gösterilir.
  const bankaAdlari: Record<string, string> = {};
  for (const b of banks ?? []) bankaAdlari[b.slug] = b.name;

  const alanKapsamiSatirlari = alanKapsamiSiraliHesapla(
    stats.alan_kapsami ?? {},
    alanEtiketleri,
    stats.korpus.campaigns,
  );
  const bankaBasinaSatirlari = bankaBasinaSiraliHesapla(
    stats.banka_basina ?? {},
    bankaAdlari,
  );

  return (
    <section className="card">
      <h2>Bilgiler</h2>
      <p className="lede">
        Korpusun tamamına dair genel bakış — banka kıyaslamaz, elimizdeki
        belgeleri tarif eder. Banka arası karşılaştırma için{" "}
        <span className="mono">Karşılaştırma</span> sekmesine bakın.
      </p>

      <h3>Kampanya Türü Dağılımı</h3>
      <p className="small muted" style={{ marginTop: 0 }}>
        {trNum(toplamKampanya)} kampanyanın kampanya türüne göre dağılımı.
      </p>
      <KampanyaTuruDonut counts={stats.campaign_type_counts ?? {}} />

      <SayacGrubu
        baslik="Belge Türü"
        girdiler={[
          ["kampanya", belgeTuru.kampanya ?? null],
          ["sözleşme", belgeTuru.sozlesme ?? null],
          ["bilinmeyen", belgeTuru.bilinmeyen ?? null],
        ]}
      />

      <SayacGrubu
        baslik="Kampanya Durumu"
        girdiler={[
          ["aktif", durum.active ?? null],
          ["süresi dolmuş", durum.expired ?? null],
          ["damgasız (doğrulanmamış)", durum.damgasiz ?? null],
        ]}
      />

      <SayacGrubu
        baslik="Çıkarım Katmanı"
        girdiler={[
          ["kural", katman.rule ?? null],
          ["NER", katman.ner ?? null],
          ["LLM", katman.llm ?? null],
        ]}
      />

      <AlanKapsamiTablosu
        satirlar={alanKapsamiSatirlari}
        toplamKampanya={stats.korpus.campaigns}
      />

      <YapilandirilmisKapsam
        campaigns={stats.korpus.campaigns}
        campaignsWithFields={stats.korpus.campaigns_with_fields}
      />

      <BankaBasinaTablosu satirlar={bankaBasinaSatirlari} />

      <EkVeriAlanlariKutusu satirlar={alanKapsamiSatirlari} />

      <p className="small muted" style={{ marginTop: "var(--sp-4)" }}>
        Yerel LLM:{" "}
        <span className="mono">{stats.llm.acik ? "açık" : "kapalı"}</span>
        {" · "}Depo: <span className="mono">{stats.backend}</span>
      </p>
    </section>
  );
}
