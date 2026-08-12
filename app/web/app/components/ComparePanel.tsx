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
 * Ekran grafik ağırlıklı hâle getirildi: `KiyasCubuklari` tablonun ÜSTÜNDE,
 * tablo altında denetlenebilir ayrıntı olarak kalıyor. Grafik `/banks`ten gelen
 * TAM banka listesini de alıyor; verisi olmayan banka boş çubuk olarak çizilip
 * listede kalıyor (ölçüldü: `kar_payi_orani` 1.774 belgenin 56'sında, 11
 * bankanın 6'sında var — grafiği yalnız `/compare` satırlarıyla çizmek beş
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
 * ## KAYNAK JESTİ TEK (2026-08-12)
 *
 * Satır içi kaynak çekmecesi (`openRow` + `SourceDrawer`) kaldırıldı; yerine
 * her yüzeyde aynı olan `KaynakDipnotu` geldi. Çekmece tabloyu iterek açılıyor
 * ve kullanıcı okuduğu satırı kaybediyordu; yan panel tabloyu yerinde bırakıp
 * iddia ile kanıtı aynı ekranda tutuyor. Gerekçenin tamamı KaynakDipnotu.tsx
 * başlığında.
 */

import { Fragment, useState } from "react";
import { api } from "../lib/api";
import type { CompareRow, FieldMeta, PerBank } from "../lib/api";
import { extractorClass, extractorLabel, formatValue } from "../lib/format";
import { useJuryMode } from "../lib/juryMode";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";
import FieldChips from "./FieldChips";
import GrafikIskeleti from "./grafik/GrafikIskeleti";
import KiyasCubuklari from "./grafik/KiyasCubuklari";
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

export default function ComparePanel({ fields, campaignTypes }: Props) {
  const [field, setField] = useState(fields[0]?.field ?? "kar_payi_orani");
  const [intent, setIntent] = useState<Intent>("");
  const [type, setType] = useState("");
  const [perBank, setPerBank] = useState<PerBank>("best");
  const { jury } = useJuryMode();

  const rows = useAsync(
    () => api.compare(field, intent || undefined, type || undefined, perBank),
    [field, intent, type, perBank],
  );
  // Banka kataloğu grafiğin «veri yok» çubukları için; `/compare` yalnız değer
  // TAŞIYAN satırları döndürdüğü için eksik bankalar ancak buradan bilinir.
  const banks = useAsync(() => api.banks(), []);
  const meta = fields.find((f) => f.field === field);
  const bolumler = turlereBol(rows.data ?? []);
  // Sütun sayısı: Sıra, Banka, Kampanya türü, Değer, [Güven], Katman, Durum,
  // Kaynak.
  const sutunSayisi = jury ? 8 : 7;

  // Grafiğe giden bölüm: tek tür seçiliyse o, «Tümü» ise en çok bankanın veri
  // taşıdığı tür (gerekçe dosya başlığında). Eşitlikte ilk gelen kazanır —
  // sunucunun sırası korunur, burada yeniden sıralama yapılmaz.
  const grafikBolumu =
    bolumler.length === 0
      ? null
      : bolumler.reduce((en, b) => (b.satirlar.length > en.satirlar.length ? b : en));

  return (
    <div className="stack">
      <section className="card">
        <h2>Karşılaştırma Paneli</h2>
        {/* Buradaki `lede` KALDIRILDI (2026-08-11). İki cümlesi de — «yalnız
            aynı birime normalize edilmiş değerler kıyaslanır» ve
            «kıyaslanamayan değer silinmez» — adil kıyas şeridinin ilk
            satırında zaten yazıyor. Ölçüm: ilk veri satırından önce basılan
            ~400 kelimeyi düşürmek için önce TEKRARLAR atıldı; aynı kuralı iki
            kez okumak kimseye bir şey öğretmiyordu. */}

        <FairnessNotice varyant="serit" />

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
          {meta && (
            <span className="badge" title="Kaynak: compare.py _LOWER_IS_BETTER / _HIGHER_IS_BETTER">
              {meta.direction_label}
            </span>
          )}
        </div>

        <div style={{ marginTop: "var(--sp-4)" }}>
          {rows.loading && <Loading />}
          {!!rows.error && <ErrorNotice error={rows.error} />}
          {!rows.loading && !rows.error && rows.data?.length === 0 && (
            <EmptyNotice title="Bu alan için kayıt bulunamadı">
              API çalışıyor ve yanıt verdi, ancak seçilen alan
              {type ? ` ve «${type}» türü` : ""} için çıkarılmış değer yok. Bu bir
              hata değil: alan metinlerde geçmiyorsa sistem değer UYDURMAZ.
            </EmptyNotice>
          )}
          {/* GRAFİK ÖNCE — ekranın taşıyıcı öğesi bu. Tablo altında kalır ve
              denetlenebilir ayrıntıyı verir. */}
          {rows.data && rows.data.length > 0 && grafikBolumu && (
            <>
              <GrafikIskeleti
                yukseklik={
                  Math.max(
                    banks.data?.length ?? 0,
                    grafikBolumu.satirlar.length,
                  ) *
                    30 +
                  48
                }
              />
              <KiyasCubuklari
                rows={grafikBolumu.satirlar.map((s) => s.row)}
                bankalar={banks.data ?? undefined}
                alan={field}
                baslik={`${meta?.label ?? field} — kampanya türü: ${grafikBolumu.tur}`}
              />
              {bolumler.length > 1 && (
                <p className="small muted">
                  Grafik yalnız <b>{grafikBolumu.tur}</b> türünü çizer: en çok
                  bankanın bu alanda veri taşıdığı tür. Farklı türler tek eksene
                  konmaz — yan yana duran çubuklar, sistemin reddettiği türler
                  arası sıralamayı ima ederdi. Diğer {bolumler.length - 1} tür
                  aşağıdaki tabloda bölüm bölüm durur; grafiği başka bir türe
                  almak için üstteki «Kampanya türü süzgeci»ni kullanın.
                </p>
              )}
              {!!banks.error && (
                <p className="small muted">
                  Banka kataloğu (<span className="mono">/banks</span>)
                  okunamadı; grafikte yalnız değer taşıyan bankalar var. Verisi
                  olmayan bankaların boş çubukları bu turda çizilemedi.
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
                      söylüyor. Kalan iki bilgi şeritte yok ve tabloya özgü —
                      bağlantının ne yaptığı, ve sütun ile süzgecin aynı adı
                      taşıyıp farklı iş yapması. */}
                  Kaynak sütunundaki ¶ rozetine basınca belge yandan açılır ve
                  değerin kaynak metindeki karakter aralığı vurgulanır; tablo
                  yerinde kalır. Sıra numaraları tür içinde verilir; «Kampanya
                  türü» sütunu satırın türünü gösterir, üstteki aynı adlı süzgeç
                  ise listeyi tek türe indirir.
                </caption>
                <thead>
                  <tr>
                    <th scope="col">Sıra</th>
                    <th scope="col">Banka</th>
                    <th scope="col">Kampanya türü</th>
                    <th scope="col">Değer</th>
                    {jury && <th scope="col">Güven</th>}
                    <th scope="col">Katman</th>
                    <th scope="col">Durum</th>
                    <th scope="col">Kaynak</th>
                  </tr>
                </thead>
                <tbody>
                  {bolumler.map((bolum) => (
                    <Fragment key={bolum.tur}>
                      {/* Bölüm başlığı yalnız birden fazla tür varsa gerekli;
                          tek tür seçiliyken gereksiz bir katman olurdu.
                          «Kampanya türü:» öneki bilinçli: başlıkta çıplak bir
                          ürün adı görünce kullanıcı onu bir banka ürünü
                          zannediyordu, oysa bir SINIF adıdır. */}
                      {bolumler.length > 1 && (
                        <tr className="group-head">
                          <td colSpan={sutunSayisi}>
                            Kampanya türü: {bolum.tur} · {bolum.satirlar.length}{" "}
                            banka
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
                    </Fragment>
                  ))}
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
        <td data-label="Kampanya türü" className="small muted">
          {row.campaign_type || <span className="faint">belirlenemedi</span>}
        </td>
        <td data-label="Değer" className="num">
          <strong>{formatValue(row.value, field)}</strong>
          {row.raw_value && (
            <div className="small faint mono" title="Kaynak metindeki ham ifade">
              «{row.raw_value.trim()}»
            </div>
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
            <span className="badge badge-warn" title={row.note ?? ""}>
              {row.note ?? "kıyaslanamaz"}
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
