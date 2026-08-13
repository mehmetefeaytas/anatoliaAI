"use client";

/**
 * Karşılaştırma Paneli — bankalar arası tek alan kıyası.
 *
 * İlgili: src/api/main.py `/compare`, src/comparison/compare.py (adil kıyas),
 *         CLAUDE.md §17
 *
 * Eskiye göre ne değişti:
 *  - 3 sabit alan yerine 12 alanın tamamı (`GET /fields`).
 *  - Her satırda GÜVEN skoru + güven kaynağı + hangi KATMAN ürettiği görünür.
 *  - Değere tıklanınca kaynak metin açılır ve span vurgulanır (`SourceSpanView`).
 *  - `intent` (en düşük / en yüksek) artık gerçekten çalışır.
 *  - Çelişki taşıyan kampanyalar satırda işaretlenir.
 *  - Hata artık yutulmuyor; "veri yok" ile "API kapalı" ayrı gösteriliyor.
 *
 * GÜVEN SKORU burada JÜRİ MODUNA bağlıdır (bkz. ../lib/juryMode.tsx): bu tablo
 * ticari/bilgi arayan izleyicinin gördüğü tek yüzeydir ve kalibre edilmemiş bir
 * skoru orada kalite iddiası gibi göstermek yanıltıcıdır. Denetim yüzeyleri
 * (Audit / Canlı Çıkarım / Şeffaf Skorlama) skoru her hâlde gösterir.
 *
 * ## KAMPANYA TÜRÜ KAPISI (2026-08-09)
 *
 * Bu tablo «elma ile armut kıyaslıyor» diye bildirildi ve şikâyet yerindeydi.
 * Tür süzmesi VARDI ama varsayılanı «Tümü» idi ve `comparable` bayrağı yalnız
 * BİRİM uyumunu doğruluyordu, kampanya türünü değil. Sonuç: `vade_ay` alanında
 * 120 aylık bir **konut finansmanı** 1. sırada, 36 aylık bir **ihtiyaç
 * finansmanı** 2. sırada listeleniyordu — hiçbir uyarı olmadan.
 *
 * Çözüm süzmeyi zorunlu kılmak DEĞİL (o, veriyi gizlemek olurdu): «Tümü»
 * seçiliyken satırlar kampanya türüne göre BÖLÜMLENİYOR ve sıralama yalnız
 * bölüm içinde yapılıyor. Farklı türler hiçbir koşulda aynı sıralamaya
 * girmiyor. `compare.py:502-507` bu boşluğu kendi docstring'inde zaten
 * yazmıştı; burası onun kullanıcıya dönük karşılığı.
 *
 * ## TEK TERİM (2026-08-09)
 *
 * Yukarıdaki kapı ilk yazıldığında kavrama «ürün ailesi» deniyordu; oysa
 * ekrandaki süzgecin etiketi «Kampanya türü» idi ve kullanıcı ikisini iki
 * ayrı süzgeç sandı. Kavram tektir: `campaign_type`, 8 sınıf. Arayüzün
 * tamamında adı **kampanya türü**dür. Tanımı `FairnessNotice`'ta bir kez
 * yazılır; buradaki tablo notu ona atıf yapar, kavramı yeniden tanımlamaz.
 *
 * ## GRAFİK ÖNCE, TABLO SONRA (2026-08-12)
 *
 * Ekran grafik ağırlıklı hâle getirildi: kapsama cetveli tablonun ÜSTÜNDE,
 * tablo altında denetlenebilir ayrıntı olarak kalıyor. Cetvel `/banks`ten gelen
 * TAM banka listesini de alıyor; verisi olmayan banka kesik taban çizgisiyle
 * çizilip listede kalıyor (ölçüldü: `kar_payi_orani` 1.774 belgenin 56'sında,
 * 11 bankanın 6'sında var — grafiği yalnız `/compare` satırlarıyla çizmek beş
 * bankayı sessizce yok ederdi).
 *
 * **Grafik TEK kampanya türü çizer.** Türler arası sıralama yasak (§17) ve bir
 * ekseni paylaşan çubuklar tam da o sıralamayı ima eder. Seçenekler ikisiydi:
 * bölüm başına bir grafik, ya da seçili tür. Bölüm başına grafik seçilmedi —
 * «Tümü» hâlinde 8 tür × 11 banka ≈ 88 çubuk, yani ilk veri satırından önce
 * ~2.600 piksel; bu «grafik ağırlıklı» değil, grafik yığınıdır. Grafik seçili
 * türü çizer; «Tümü» seçiliyken EN ÇOK BANKANIN veri taşıdığı türü alır ve
 * hangi türü çizdiğini başlıkta yazar. Kalan türler tabloda bölüm bölüm durur.
 *
 * ## CANVAS ÇIKTI, KAPSAMA CETVELİ GİRDİ (2026-08-12)
 *
 * Birincil görselleştirme Chart.js tuvali değil,
 * `KapsamaCetveli` (saf DOM + CSS grid). Tuval üç şeyi birden yapamıyordu:
 * erişilebilirlik ağacında yoktu (altına ayrıca metin liste basılıyordu, yani
 * aynı bilgi iki kez), dört kapsama hâlini ayrı BİÇİMLERLE anlatamıyordu
 * (elde yalnız renk + uzunluk vardı; renk TEK sinyal olamaz, WCAG 1.4.1) ve
 * çubuk başına `aria-label` taşıyamıyordu. Cetvel üçünü de çözüyor.
 * Tuval bileşenleri (`KiyasCubuklari`, `RadarKiyas`) 2026-08-12'de silindi;
 * gerekçe `grafik/KapsamaCetveli.tsx` başlığında.
 *
 * ## EKRANIN TEK KESRİ: KAPSAMA SAYACI (2026-08-12)
 *
 * Başlığın sağında provenans şeridiyle (`.rail .rail-doktrin`) tek bir kesir
 * durur: «4 / 11 banka», altında kırılımı. Bu, ekranın iddiasını değiştiren
 * bir öğedir — soru «kim kazandı» değil, «neyi ne kadar biliyoruz». Kesir
 * GERÇEK veriden hesaplanır (`/compare` satırları + `/banks` kataloğu) ve
 * kırılımı cetvelin çubuk biçimleriyle AYNI kuraldan gelir
 * (`KapsamaCetveli.kapsamaOzeti`) — iki yerde hesaplanan bir sayı ayrışır.
 *
 * ## KAYNAK JESTİ TEK (2026-08-12)
 *
 * Satır içi kaynak çekmecesi (`openRow` + `SourceDrawer`) kaldırıldı; yerine
 * her yüzeyde aynı olan `KaynakDipnotu` geldi. Çekmece tabloyu iterek açılıyor
 * ve kullanıcı okuduğu satırı kaybediyordu; yan panel tabloyu yerinde bırakıp
 * iddia ile kanıtı aynı ekranda tutuyor. Gerekçenin tamamı KaynakDipnotu.tsx
 * başlığında.
 */

import { Fragment, useEffect, useState } from "react";
import { api } from "../lib/api";
import type {
  Bank,
  BankaKapsami,
  CompareRow,
  FieldMeta,
  PerBank,
} from "../lib/api";
import {
  extractorClass,
  extractorLabel,
  formatValue,
  trNum,
} from "../lib/format";
import { useJuryMode } from "../lib/juryMode";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";
import FieldChips from "./FieldChips";
import GrafikIskeleti from "./grafik/GrafikIskeleti";
import KapsamaCetveli, {
  kapsamaOzeti,
  satirHali,
} from "./grafik/KapsamaCetveli";
import KaynakDipnotu from "./KaynakDipnotu";
import ScoringExplainer from "./ScoringExplainer";

type Intent = "" | "lowest" | "highest";

const INTENTS: { key: Intent; label: string }[] = [
  { key: "", label: "Alanın doğal yönü" },
  { key: "lowest", label: "En düşük önce" },
  { key: "highest", label: "En yüksek önce" },
];

type Props = {
  fields: FieldMeta[];
  campaignTypes: string[];
  /**
   * Dışarıdan gelen kampanya türü süzgeci — komut paletinden bir tür
   * seçildiğinde kullanılır.
   *
   * Tür bir EKRAN değil bir SÜZGEÇTİR: palette «Konut Finansmanı» seçen
   * kullanıcıyı ayrı bir sayfaya götürmek yerine, aradığı şeyin kıyaslandığı
   * yere bırakıp süzgeci onun adına ayarlamak doğru olan. Değer değişince
   * yerel duruma yazılır; sonrasında kullanıcı süzgeci serbestçe değiştirir.
   */
  baslangicTuru?: string | null;
  /**
   * Banka slug → belge/alan kapsamı (`/stats` → `banka_kapsami`).
   *
   * Cetveldeki «veri yok · 291 belge» etiketi bundan yazılır: belge sayısı
   * olmadan o satır «hiç bakmadık» diye okunurdu, oysa 291 belge tarandı ve
   * alan geçmedi. `BankaSayfasi` aynı veriyi aynı biçimde alıyor.
   *
   * `undefined` = çağıran bu veriyi HİÇ bağlamadı; bileşen `/stats`i kendisi
   * okur (yedek yol). `null` = çağıran bağladı ama veri henüz yok/alınamadı;
   * o hâlde sayı UYDURULMAZ, yalnız «veri yok» yazılır.
   */
  kapsam?: Record<string, BankaKapsami> | null;
};

/** Türü boş gelen satırların bölüm başlığı. */
const TURSUZ = "Türü belirlenemedi";

/**
 * Satırları kampanya türüne böler ve her bölüm içinde SIRA NUMARASINI yeniden
 * verir.
 *
 * Sunucu `rank`'i tüm sonuç kümesi üzerinden hesaplar; tek tür seçiliyken bu
 * zaten bölüm-içi sıradır. «Tümü» seçiliyken ise bir bölümün başında «5»
 * yazması kafa karıştırıcı olurdu — ve daha kötüsü, türler arasında bir
 * sıralama varmış izlenimi verirdi. Sıra bölüm içinde yeniden numaralanır;
 * `rank === null` olan (kıyaslanamaz) satırlar numara ALMAZ.
 */
function turlereBol(
  rows: CompareRow[],
): { tur: string; satirlar: { row: CompareRow; sira: number | null }[] }[] {
  const bolumler = new Map<string, { row: CompareRow; sira: number | null }[]>();
  for (const row of rows) {
    const tur = row.campaign_type || TURSUZ;
    const liste = bolumler.get(tur) ?? [];
    liste.push({ row, sira: null });
    bolumler.set(tur, liste);
  }
  return Array.from(bolumler, ([tur, satirlar]) => {
    let konum = 0;
    return {
      tur,
      satirlar: satirlar.map(({ row }) => ({
        row,
        sira: row.rank === null ? null : ++konum,
      })),
    };
  });
}

/**
 * Bir bölümde değeri ÇIKARILAMAYAN bankalar.
 *
 * Cetvel bunları kesik taban çizgisiyle çiziyor; tablonun da aynı satırları
 * göstermesi gerekiyor, yoksa «aynı 11 satır» iddiası tabloda tutmaz.
 */
function eksikBankalar(
  satirlar: { row: CompareRow }[],
  bankalar: Bank[] | null,
): Bank[] {
  if (!bankalar) return [];
  const gorulen = new Set(satirlar.map(({ row }) => row.bank));
  return bankalar.filter((b) => !gorulen.has(b.slug));
}

export default function ComparePanel({
  fields,
  campaignTypes,
  baslangicTuru,
  kapsam,
}: Props) {
  const [field, setField] = useState(fields[0]?.field ?? "kar_payi_orani");
  const [intent, setIntent] = useState<Intent>("");
  const [type, setType] = useState(baslangicTuru ?? "");

  // Palet açıkken kullanıcı ikinci kez tür seçebilir; o zaman bileşen zaten
  // takılı olduğu için `useState` başlangıcı yeniden çalışmaz. Değer
  // değiştiğinde süzgeç güncellenir — sonrası yine kullanıcının.
  useEffect(() => {
    if (baslangicTuru) setType(baslangicTuru);
  }, [baslangicTuru]);
  const [perBank, setPerBank] = useState<PerBank>("best");
  const { jury } = useJuryMode();

  const rows = useAsync(
    () => api.compare(field, intent || undefined, type || undefined, perBank),
    [field, intent, type, perBank],
  );
  // Banka kataloğu cetvelin «veri yok» satırları için; `/compare` yalnız değer
  // TAŞIYAN satırları döndürdüğü için eksik bankalar ancak buradan bilinir.
  const banks = useAsync(() => api.banks(), []);
  // Belge sayaçları için YEDEK yol: `kapsam` propu hiç bağlanmadıysa (undefined)
  // `/stats` buradan okunur. Prop bağlıysa istek HİÇ atılmaz — sayfa o çağrıyı
  // zaten yapıyor ve ikinci bir tur boşuna olurdu (bkz. `Props.kapsam`).
  const kapsamYok = kapsam === undefined;
  const stats = useAsync(
    () => (kapsamYok ? api.stats() : Promise.resolve(null)),
    [kapsamYok],
  );
  const bankaKapsami = kapsam ?? stats.data?.banka_kapsami ?? null;
  const meta = fields.find((f) => f.field === field);
  const bolumler = turlereBol(rows.data ?? []);
  // Sütun sayısı: Sıra, Banka, Değer, Ham ifade, [Güven], Katman, Durum,
  // Kaynak.
  const sutunSayisi = jury ? 8 : 7;

  // Grafiğe giden bölüm: tek tür seçiliyse o, «Tümü» ise en çok bankanın veri
  // taşıdığı tür (gerekçe dosya başlığında). Eşitlikte ilk gelen kazanır —
  // sunucunun sırası korunur, burada yeniden sıralama yapılmaz.
  const grafikBolumu =
    bolumler.length === 0
      ? null
      : bolumler.reduce((en, b) => (b.satirlar.length > en.satirlar.length ? b : en));

  // Kapsama kesri GERÇEK veriden gelir, sabit yazılmaz: pay `/compare`
  // satırlarındaki tekrarsız banka sayısı, payda `/banks` kataloğunun boyu.
  // Katalog okunamadıysa payda UYDURULMAZ — kesir hiç basılmaz.
  const ozet = grafikBolumu ? kapsamaOzeti(grafikBolumu.satirlar) : null;
  const toplamBanka = banks.data?.length ?? null;

  return (
    <div className="stack">
      <section className="card">
        {/* Başlık artık «Karşılaştırma Paneli» değil: sekme adı bunu zaten
            söylüyordu ve başlığın taşıyabileceği en değerli iki bilgi —
            HANGİ ALAN ve HANGİ TÜR kıyaslanıyor — hiçbir yerde yazmıyordu. */}
        <div className="cetvel-kabuk">
          <div className="cetvel-ust">
            <h2>
              {meta?.label ?? field}
              {grafikBolumu ? ` · ${grafikBolumu.tur}` : ""}
            </h2>
            {/* Alan adı ve sıralama yönü MAKİNE verisidir: birincisi
                `extracted_fields.field_name` sütununun değeri, ikincisi
                `compare.py`nin `_LOWER_IS_BETTER` / `_HIGHER_IS_BETTER`
                kümelerinden geliyor. Türkçe bir cümle değil, bir etiket. */}
            <span
              className="cetvel-alan"
              title="Kaynak: compare.py _LOWER_IS_BETTER / _HIGHER_IS_BETTER"
            >
              alan: {field}
              {meta ? ` · yön: ${meta.direction_label}` : ""}
            </span>
          </div>

          {ozet && toplamBanka !== null && (
            <div className="kapsama-sayaci rail rail-doktrin">
              <span className="kapsama-etiket">kapsama</span>
              <span className="kapsama-kesir">
                {trNum(ozet.kapsanan)} / {trNum(toplamBanka)} banka
              </span>
              {/* Kapsanan 4 bankanın hepsi aynı şey değildir: biri sıralamaya
                  girer, üçü gerekçesiyle listede kalır. Kesir tek başına bu
                  ayrımı gizlerdi. */}
              <span className="kapsama-kirilim">
                kıyaslanabilir: {trNum(ozet.kiyaslanabilir)} · aralık:{" "}
                {trNum(ozet.aralik)} · koşullu: {trNum(ozet.kosullu)}
              </span>
            </div>
          )}
        </div>

        {/* Buradaki `lede` KALDIRILDI (2026-08-11). İki cümlesi de — «yalnız
            aynı birime normalize edilmiş değerler kıyaslanır» ve
            «kıyaslanamayan değer silinmez» — adil kıyas şeridinin ilk
            satırında zaten yazıyor. Ölçüm: ilk veri satırından önce basılan
            ~400 kelimeyi düşürmek için önce TEKRARLAR atıldı; aynı kuralı iki
            kez okumak kimseye bir şey öğretmiyordu.

            Aynı gerekçeyle, cetvelin «adil kıyas gerekçesi» katlaması AYRI bir
            `<details>` olarak yazılmadı: v2 tasarımının üç paragrafından ikisi
            (%0 ceza değil / türler arası sıralama üretilmez) bu şeridin
            açılınca gösterdiği metnin ta kendisi. Üçüncüsü — verisi olmayan
            banka listeden düşmez — şeritte YOKTU ve bu yüzeye özgü; `ek`
            olarak eklendi. Kural cetvelde ayrıca GÖRÜNÜR biçimde de
            duruyor: «ölçülemedi · N banka» ayırıcı satırı. */}
        <FairnessNotice
          varyant="serit"
          ek={
            <>
              <b>Verisi olmayan banka listeden düşmez.</b> Onbir satırın onbiri
              her zaman çizilir; ölçülemeyen satır kesik taban çizgisi ve{" "}
              <span className="mono">veri yok</span> etiketiyle yerini korur.
              Boşluk gizlenmiyor, sayılıyor — cetvelin başındaki kapsama kesri
              tam olarak bunu ölçer.
            </>
          }
        />

        <FieldChips fields={fields} value={field} onChange={setField} />

        <div className="row" style={{ marginTop: 12 }}>
          <div className="row-tight">
            <label className="small muted" htmlFor="cmp-intent">
              Sıralama
            </label>
            <select
              id="cmp-intent"
              className="select"
              style={{ width: "auto" }}
              value={intent}
              onChange={(e) => setIntent(e.target.value as Intent)}
            >
              {INTENTS.map((i) => (
                <option key={i.key} value={i.key}>
                  {i.label}
                </option>
              ))}
            </select>
          </div>
          <div className="row-tight">
            {/* Etiket bilinçli olarak «süzgeci» ile bitiyor: hemen üstündeki
                alan çipleriyle karıştırılıyordu. Çipler NEYİN kıyaslanacağını
                seçer, bu süzgeç KİMİN kıyaslanacağını daraltır. */}
            <label className="small muted" htmlFor="cmp-type">
              Kampanya türü süzgeci
            </label>
            <select
              id="cmp-type"
              className="select"
              style={{ width: "auto" }}
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="">Tümü (türe göre bölümlenir)</option>
              {campaignTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="row-tight">
            <label className="small muted" htmlFor="cmp-perbank">
              Banka başına
            </label>
            <select
              id="cmp-perbank"
              className="select"
              style={{ width: "auto" }}
              value={perBank}
              onChange={(e) => setPerBank(e.target.value as PerBank)}
            >
              <option value="best">En iyi kampanya (tek satır)</option>
              <option value="all">Tüm kampanyaları göster</option>
            </select>
          </div>
          {/* Yön rozeti KALDIRILDI: aynı bilgi başlığın altındaki makine
              satırında («yön: düşük daha avantajlı») zaten yazıyor ve süzgeç
              şeridinin sonunda ikinci kez basılması, süzgeç gibi görünen ama
              tıklanmayan bir öğe üretiyordu. */}
        </div>

        <div style={{ marginTop: "var(--sp-4)" }}>
          {/* YÜKLENİYOR: banka adları ve satır sayısı hemen basılır, yalnız
              çubuklar bekler. Hiçbir sayı, hiçbir sıra numarası, hiçbir
              animasyonlu sayaç görünmez — gerekçe GrafikIskeleti başlığında. */}
          {rows.loading && (
            <>
              <Loading label="Kıyas satırları yükleniyor…" />
              <GrafikIskeleti
                bankalar={banks.data?.map((b) => b.name)}
                yukseklik={(banks.data?.length ?? 8) * 32 + 32}
              />
            </>
          )}
          {!!rows.error && <ErrorNotice error={rows.error} />}
          {!rows.loading && !rows.error && rows.data?.length === 0 && (
            <EmptyNotice title="Bu alan için kayıt bulunamadı">
              API çalışıyor ve yanıt verdi, ancak seçilen alan
              {type ? ` ve «${type}» türü` : ""} için çıkarılmış değer yok. Bu bir
              hata değil: alan metinlerde geçmiyorsa sistem değer UYDURMAZ.
            </EmptyNotice>
          )}
          {/* CETVEL ÖNCE — ekranın taşıyıcı öğesi bu. Tablo altında kalır ve
              denetlenebilir ayrıntıyı verir. */}
          {rows.data && rows.data.length > 0 && grafikBolumu && (
            <>
              <KapsamaCetveli
                satirlar={grafikBolumu.satirlar}
                bankalar={banks.data ?? undefined}
                alan={field}
                kapsam={bankaKapsami}
              />
              {bolumler.length > 1 && (
                <p className="small muted">
                  Cetvel yalnız <b>{grafikBolumu.tur}</b> türünü çizer: en çok
                  bankanın bu alanda veri taşıdığı tür. Farklı türler tek eksene
                  konmaz — yan yana duran çubuklar, sistemin reddettiği türler
                  arası sıralamayı ima ederdi. Diğer {bolumler.length - 1} tür
                  aşağıdaki tabloda bölüm bölüm durur; cetveli başka bir türe
                  almak için üstteki «Kampanya türü süzgeci»ni kullanın.
                </p>
              )}
              {!!banks.error && (
                <p className="small muted">
                  Banka kataloğu (<span className="mono">/banks</span>)
                  okunamadı; cetvelde yalnız değer taşıyan bankalar var. Verisi
                  olmayan bankaların satırları ve kapsama kesri bu turda
                  çizilemedi — kesir uydurulmuyor, hiç basılmıyor.
                </p>
              )}
            </>
          )}

          {rows.data && rows.data.length > 0 && (
            <div className="table-wrap">
              <table className="data stackable">
                <caption
                  className="small muted"
                  style={{
                    captionSide: "bottom",
                    textAlign: "left",
                    paddingTop: "var(--sp-2)",
                  }}
                >
                  {/* «Türler arasında sıralama yapılmaz» cümlesi buradan
                      çıkarıldı: adil kıyas şeridi onu tablodan ÖNCE zaten
                      söylüyor. Kalan bilgiler şeritte yok ve tabloya özgü. */}
                  Cetveldeki AYNI satırlar, denetlenebilir hâlde.{" "}
                  <span className="mono">¶</span> rozetine basınca belge yandan
                  açılır ve değerin kaynak metindeki karakter aralığı
                  vurgulanır; tablo yerinde kalır. Rozetteki sayı o aralığın
                  kendisidir. «Ham ifade» sütunu bankanın kendi yazdığı metni
                  tırnaklı yazıyla verir — normalize edilmiş değerin nereden
                  geldiği orada okunur. Satırın kampanya türü bölüm başlığında
                  yazar; üstteki «Kampanya türü süzgeci» listeyi tek türe
                  indirir.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Sıra</th>
                    <th scope="col">Banka</th>
                    <th scope="col">Değer</th>
                    <th scope="col">Ham ifade</th>
                    {jury && <th scope="col">Güven</th>}
                    <th scope="col">Katman</th>
                    <th scope="col">Durum</th>
                    <th scope="col">Kaynak</th>
                  </tr>
                </thead>
                <tbody>
                  {bolumler.map((bolum) => {
                    const eksik = eksikBankalar(bolum.satirlar, banks.data);
                    return (
                      <Fragment key={bolum.tur}>
                        {/* Bölüm başlığı yalnız birden fazla tür varsa gerekli;
                            tek tür seçiliyken gereksiz bir katman olurdu.
                            «Kampanya türü:» öneki bilinçli: başlıkta çıplak bir
                            ürün adı görünce kullanıcı onu bir banka ürünü
                            zannediyordu, oysa bir SINIF adıdır. */}
                        {bolumler.length > 1 && (
                          <tr className="group-head">
                            <td colSpan={sutunSayisi}>
                              Kampanya türü: {bolum.tur} ·{" "}
                              {bolum.satirlar.length} banka
                            </td>
                          </tr>
                        )}
                        {bolum.satirlar.map(({ row, sira }, i) => (
                          <Satir
                            key={`${row.campaign_id}-${bolum.tur}-${i}`}
                            row={row}
                            sira={sira}
                            field={field}
                            jury={jury}
                          />
                        ))}
                        {/* Değer çıkarılamayan bankalar TABLODA da durur.
                            Cetvel onları kesik taban çizgisiyle çiziyor; tablo
                            atlarsa «aynı 11 satır» iddiası tabloda tutmaz.
                            Toplu tek satır seçildi çünkü onbir satırın yedisi
                            aynı şeyi söylüyor ve yedi kez boş satır basmak
                            tablonun okunabilirliğini bilgi eklemeden düşürür —
                            satır SAYISI değil, satırların KENDİSİ korunuyor. */}
                        {eksik.length > 0 && (
                          <>
                            <tr>
                              <td
                                colSpan={sutunSayisi}
                                className="cetvel-tablo-ayirici"
                              >
                                değer çıkarılamadı · {eksik.length} banka ·
                                satırlar silinmedi
                              </td>
                            </tr>
                            <tr>
                              <td data-label="Sıra" className="faint">
                                —
                              </td>
                              <td data-label="Banka" className="muted">
                                {eksik.map((b) => b.name).join(" · ")}
                              </td>
                              <td data-label="Değer" className="mono faint">
                                null
                              </td>
                              <td data-label="Ham ifade" className="mono faint">
                                —
                              </td>
                              {jury && (
                                <td data-label="Güven" className="mono faint">
                                  —
                                </td>
                              )}
                              <td data-label="Katman" className="mono faint">
                                —
                              </td>
                              <td data-label="Durum">
                                {/* Kesikli çerçeve: bu bir uyarı DEĞİL, bir
                                    yokluk bildirimi. `.pill` tam bunun için
                                    tanımlı (mono + kesik + nötr renk). */}
                                <span className="pill">
                                  alan metinde geçmiyor
                                </span>
                              </td>
                              <td data-label="Kaynak" className="mono faint">
                                dipnot yok
                              </td>
                            </tr>
                          </>
                        )}
                      </Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>

      <ScoringExplainer field={field} type={type} />
    </div>
  );
}

function Satir({
  row,
  sira,
  field,
  jury,
}: {
  row: CompareRow;
  /** Kampanya türü İÇİNDEKİ sıra; kıyaslanamaz satırlarda null. */
  sira: number | null;
  field: string;
  /** Jüri modu — güven sütunu yalnız açıkken basılır. */
  jury: boolean;
}) {
  return (
    <>
      <tr>
        <td data-label="Sıra" className="num">
          <span className={`rank-pill${sira === 1 ? " first" : ""}`}>
            {sira ?? "—"}
          </span>
        </td>
        <td data-label="Banka">
          {row.bank_name || row.bank}
          {/* Elenen kampanyalar gizlenmiyor, SAYILIYOR. Tamamı «Tüm
              kampanyaları göster» ile alınabilir. */}
          {row.other_count > 0 && (
            <div className="small faint">
              +{row.other_count} kampanya daha
            </div>
          )}
        </td>
        <td data-label="Değer" className="num">
          <strong>{formatValue(row.value, field)}</strong>
        </td>
        {/* HAM İFADE kendi sütununa çıktı ve TIRNAKLI yazıya geçti.
            Önceden değerin altında mono fısıltı olarak duruyordu, yani
            bankanın kendi cümlesi makine verisiyle aynı sesle basılıyordu.
            Oysa üç sesin ayrımı bu ürünün tezinin görsel karşılığı: mono
            makine, tırnaklı yazı BANKA (bkz. tokens.css, "ÜÇ SES"). Sütun
            olması ayrıca kıyası mümkün kılıyor — «Vade Kar Oranı» ile
            «vade ve kar oranı» aynı alanı doldurup farklı yazılmış. */}
        <td data-label="Ham ifade" className="cetvel-ham">
          {row.raw_value ? (
            `«${row.raw_value.trim()}»`
          ) : (
            <span className="mono faint">ham ifade kaydedilmemiş</span>
          )}
        </td>
        {jury && (
          <td data-label="Güven">
            <ConfidenceBadge value={row.confidence} source={row.confidence_source} />
            <div className="conf-src">{row.confidence_source ? `kaynak: ${labelOf(row.confidence_source)}` : "kaynak: kaydedilmedi"}</div>
          </td>
        )}
        <td data-label="Katman">
          <span className={extractorClass(row.extractor)}>
            {extractorLabel(row.extractor)}
          </span>
        </td>
        <td data-label="Durum">
          {row.comparable ? (
            <span className="badge badge-ok">kıyaslanabilir</span>
          ) : (
            /* Gerekçe SUNUCUNUN sözüdür (`compare.py` → `note`); istemci onu
               yeniden yazmaz. Yalnız `note` hiç gelmediğinde satırın hâline
               göre bir gerekçe basılır — «kıyaslanamaz» tek başına neden
               kıyaslanamadığını söylemiyordu. */
            <span className="badge badge-warn" title={row.note ?? ""}>
              {row.note ??
                (satirHali(row) === "aralik"
                  ? "aralık — doğrudan kıyaslanamaz"
                  : "koşullu oran (kanal/müşteri/taban)")}
            </span>
          )}
          {row.campaign_status === "expired" && (
            <div style={{ marginTop: "var(--sp-1)" }}>
              <span
                className="badge badge-expired"
                title="Kampanya sayfası kendi bitişini ilan ediyor ya da arşivde. Değer görünür kalır, sıralamaya girmez."
              >
                süresi dolmuş
              </span>
            </div>
          )}
          {row.contradiction_count > 0 && (
            <div style={{ marginTop: "var(--sp-1)" }}>
              <span className="badge badge-bad">
                {row.contradiction_count} çelişki
              </span>
            </div>
          )}
        </td>
        <td data-label="Kaynak">
          {/* Her yüzeydeki AYNI jest: rozete bas, belge yandan açılsın, değerin
              aralığı vurgulu olsun. `CompareRow` zaten `SpanInfo`'yu taşıdığı
              için satırın kendisi span olarak geçilebiliyor. */}
          <KaynakDipnotu
            campaignId={row.campaign_id}
            span={row}
            rawValue={row.raw_value}
          />
          {/* Karakter aralığı rozetin YÜZÜNDE zaten yazıyor (`¶ 1284–1298`):
              `KaynakDipnotu` etiket verilmediğinde span'i basıyor. Buraya
              ikinci bir ofset satırı eklemek aynı sayıyı iki kez basmaktı. */}
        </td>
      </tr>
    </>
  );
}

function labelOf(src: string): string {
  // format.ts'deki sözlüğün kısa hali; tabloda satır yüksekliği korunsun diye.
  const map: Record<string, string> = {
    rule_heuristic: "kanıt tabanlı",
    constant: "sabit (kalibre değil)",
    logprob: "logprob",
    self_reported: "model beyanı",
  };
  return map[src] ?? src;
}
