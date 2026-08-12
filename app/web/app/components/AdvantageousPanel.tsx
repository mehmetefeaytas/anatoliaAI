"use client";

/**
 * «En Avantajlı Kampanya» — çok alanlı, ağırlıklı bileşik skor.
 *
 * İlgili: src/api/main.py `GET /advantageous`,
 *         src/comparison/compare.py `rank_advantageous_by_type` (:477)
 *         CLAUDE.md §17 (adil kıyas), §5.7
 *
 * ## Bu panel neden var
 *
 * `compare.py`'deki bileşik skorlama (~420 satır) yazılı ve TESTLİYDİ;
 * `GET /advantageous` ucu da 2026-08-08'de açıldı. Ama arayüzde hiç
 * çağrılmıyordu — `web/` içinde `advantageous` geçen tek satır yoktu. Yani
 * kampanya türü İÇİNDE adil sıralama yapan tek kod yolu kullanıcıya kapalıydı.
 *
 * Bu, kıyas ekranındaki «elma ile armut» şikâyetinin köküne iner: `/compare`
 * tek alan üzerinden ve tür süzmesi opsiyonel çalışır; burada sıralama her
 * zaman tür içindedir ve türler arası karşılaştırma HİÇ yapılmaz.
 *
 * ## Üç kapı görünür kalır
 *
 * Küçük gruplar (`min_group_size` altı) sıralanmaz ve GİZLENMEZ — kaç
 * kampanya olduğu ve neden sıralanmadığı yazılır. Kapsama eşiğini geçemeyen
 * kampanya `comparable=false` döner ve nedeni `note`'ta durur. Sayıya
 * indirgenemeyen alan skorlanmaz; değer asla uydurulmaz (CLAUDE.md §19).
 *
 * ## RADAR KALKTI, YERİNE SKOR CETVELİ GELDİ (2026-08-12)
 *
 * Her kampanya türünün başında iki açılır liste ve bir radar çokgeni vardı:
 * aynı türden iki banka seçilir, ölçüt ölçüt profilleri üst üste çizilirdi.
 * Üç sebeple kaldırıldı ve gerekçenin tamamı `SkorCetveli` başlığında.
 *
 * Kısası: radar çok ölçütü tek şekle katlar ve ölçülemeyen ekseni MERKEZE —
 * yani sıfıra — çeker. Bu panelin sunucudan gelen `fairness_note`u tam tersini
 * söylüyor: «0 puan ürün yok demektir, kötü demek değil». Grafik, üstünde yazan
 * uyarıyı çürütüyordu.
 *
 * Ayrıca ÖLÇÜLDÜ: seçiciler yalnız `comparable` kayıtları listeliyordu ve o sayı
 * türe göre 0 ile 17 arasında geziniyor — «Yeni Müşteri»de 0, «Finansman»da 1
 * (radar hiç çizilmiyor), «Sınıflandırılamadı»nda 2. İki seçenekli bir açılır
 * liste arıza gibi okunuyordu; oysa veri gerçeğiydi.
 *
 * Yerine gelen cetvel o gerçeği gizlemiyor, basıyor: türün BÜTÜN satırları
 * çizilir, hiçbiri düşmez, üç hâl (dolu / kesikli+tarama / kesik taban çizgisi)
 * ayrı biçim taşır. Kıyas ekranıyla aynı görsel dil ve aynı CSS ailesi.
 *
 * Kıyas her zaman TÜR İÇİNDEDİR: cetvel bir türün bölümünde yaşar (§17).
 */

import { useMemo, useState } from "react";
import { api } from "../lib/api";
import type { AdvantageousGroup, CompositeScore, WeightRow } from "../lib/api";
import { formatValue, trNum } from "../lib/format";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";
import { useAsync } from "../lib/useAsync";

type Props = {
  campaignTypes: string[];
  /** Belgeyi Jüri Audit Paneli'nde açar (page.tsx `inspect` deseni). */
  onInspect?: (campaignId: number) => void;
};

/** 0..1 skoru yüzdeye çevirir. `null` = skorlanamadı, 0 ile karıştırılmaz. */
function yuzde(v: number | null): string {
  return v === null || Number.isNaN(v) ? "—" : `%${trNum(Math.round(v * 100))}`;
}

export default function AdvantageousPanel({ campaignTypes, onInspect }: Props) {
  const [tur, setTur] = useState("");
  const veri = useAsync(() => api.advantageous(tur || undefined), [tur]);

  // Alan adlarının insan etiketleri `/fields`ten gelir; skor bileşenleri yalnız
  // alan ADINI taşır ve ekranda `kar_payi_orani` yazması jüriye kod okutmaktır.
  //
  // Bu eşleme radar eksenleri için kurulmuştu; radar kalktığında ÖLÜ SANILDI ama
  // asıl ihtiyaç duyan yer duruyordu: ölçüt dökümü (`SkorSatiri`, açılan satır)
  // ham alan adını basıyordu. Etiket oraya bağlandı.
  //
  // Uç okunamazsa etiket yerine alan adı görünür — döküm yine basılır.
  const alanlar = useAsync(() => api.fields(), []);
  const etiketler = useMemo(
    () =>
      Object.fromEntries((alanlar.data ?? []).map((f) => [f.field, f.label])),
    [alanlar.data],
  );

  return (
    <section className="card">
      <h2>En Avantajlı Kampanya</h2>
      {/* Kampanya türünün TANIMI (sekiz sınıfın sayılması + «birbirinin
          alternatifi değildir» gerekçesi) buradan çıkarıldı: tanım tek yerde,
          adil kıyas şeridinin açılan gövdesinde yaşıyor. Üç panelde üç kez
          yazılmış olması, ilk ekranı dolduran tekrarın kaynağıydı. Burada
          yalnız bu panele özgü olan kalıyor: skorun bileşik olduğu. */}
      <p className="lede">
        Tek alan değil, <b>ağırlıklı bileşik skor</b>. Sıralama her zaman{" "}
        <b>kampanya türü içinde</b> yapılır.
      </p>

      <div className="row" style={{ marginBottom: "var(--sp-4)" }}>
        <label className="small muted" htmlFor="avantaj-tur">
          Kampanya türü süzgeci
        </label>
        <select
          id="avantaj-tur"
          className="select"
          style={{ width: "auto" }}
          value={tur}
          onChange={(e) => setTur(e.target.value)}
        >
          <option value="">Tüm türler (ayrı ayrı sıralanır)</option>
          {campaignTypes.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      {veri.loading && <Loading label="Bileşik skorlar hesaplanıyor…" />}
      {!!veri.error && <ErrorNotice error={veri.error} />}

      {veri.data && (
        <>
          {/* Eskiden burada `FairnessNotice`'ın elle kopyalanmış bir varyantı
              vardı: aynı `.fairness` kabuğu, içinde yalnız sunucunun
              `fairness_note` metni. Üç yüzeyde üç ayrı adil-kıyas kutusu
              demekti bu. Artık ortak şerit basılıyor; sunucunun bu ekrana ÖZEL
              kuralı (kapsama eşiği, skorlanmayan alanın cezalandırılmaması)
              kaybolmuyor — şerit açıldığında genel kuralların sonunda
              görünüyor. */}
          <FairnessNotice varyant="serit" ek={veri.data.fairness_note} />

          <Agirliklar rows={veri.data.weights} />

          {Object.keys(veri.data.types).length === 0 ? (
            <EmptyNotice title="Sıralanacak kampanya bulunamadı">
              Seçilen türde skorlanabilir alan taşıyan kampanya yok.
            </EmptyNotice>
          ) : (
            Object.entries(veri.data.types).map(([ad, grup], i) => (
              <TurBolumu
                key={ad}
                ad={ad}
                sira={i}
                grup={grup}
                minGrup={veri.data!.min_group_size}
                etiketler={etiketler}
                onInspect={onInspect}
              />
            ))
          )}
        </>
      )}
    </section>
  );
}

/**
 * Ağırlıklar gerekçeleriyle. Jüri «neden bu ağırlık» diye sorduğunda cevap
 * kodun içinde gömülü kalmasın diye açıkça basılır; ağırlık bir ÜRÜN
 * KARARIDIR, ölçümden türetilmiş bir sabit değil.
 */
function Agirliklar({ rows }: { rows: WeightRow[] }) {
  const [acik, setAcik] = useState(false);
  if (!rows.length) return null;

  return (
    <div style={{ margin: "var(--sp-4) 0" }}>
      <button
        type="button"
        className="btn-link"
        aria-expanded={acik}
        onClick={() => setAcik((a) => !a)}
      >
        {acik ? "Ağırlıkları gizle" : `Ağırlıklar ve gerekçeleri (${rows.length})`}
      </button>
      {acik && (
        <div className="table-wrap" style={{ marginTop: "var(--sp-2)" }}>
          <table className="data stackable">
            <thead>
              <tr>
                <th scope="col">Alan</th>
                <th scope="col" className="num">
                  Ağırlık
                </th>
                <th scope="col">Yön</th>
                <th scope="col">Gerekçe</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((w) => (
                <tr key={w.field_name}>
                  <td data-label="Alan" className="mono">
                    {w.field_name}
                  </td>
                  <td data-label="Ağırlık" className="num">
                    {trNum(w.weight)}
                  </td>
                  <td data-label="Yön" className="small muted">
                    {w.direction === "dusuk_iyi" ? "düşük iyi" : "yüksek iyi"}
                  </td>
                  <td data-label="Gerekçe" className="small muted">
                    {w.rationale ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function TurBolumu({
  ad,
  sira,
  grup,
  minGrup,
  etiketler,
  onInspect,
}: {
  ad: string;
  /** Bölümün ekrandaki sırası — form alanı kimliklerini benzersiz kılar. */
  sira: number;
  grup: AdvantageousGroup;
  minGrup: number;
  /** Alan adı → insan etiketi; ölçüt dökümünde ham alan adı basılmasın. */
  etiketler: Record<string, string>;
  onInspect?: (campaignId: number) => void;
}) {
  return (
    <div style={{ marginTop: "var(--sp-5)" }}>
      <h3>
        Kampanya türü: {ad} · {grup.count} kampanya
      </h3>

      <SkorCetveli ranked={grup.ranked} />

      {/* Küçük grup GİZLENMEZ: kaç kampanya olduğu ve neden sıralanmadığı yazılır. */}
      {grup.note && (
        <div className="notice notice-warn">
          <strong>Doğrudan kıyaslanamaz</strong>
          <div className="notice-body">
            {grup.note} Eşik {minGrup} kampanyadır; altında sıralama tabanlı
            normalizasyon dejenere olur ve «en avantajlı» iddiası bilgi taşımaz.
          </div>
        </div>
      )}

      {grup.ranked.length > 0 && (
        <div className="table-wrap">
          <table className="data stackable">
            <thead>
              <tr>
                <th scope="col">#</th>
                <th scope="col">Banka</th>
                <th scope="col" className="num">
                  Skor
                </th>
                <th scope="col" className="num">
                  Kapsama
                </th>
                <th scope="col">Ölçütler</th>
                <th scope="col">Belge</th>
              </tr>
            </thead>
            <tbody>
              {grup.ranked.map((c, i) => (
                <SkorSatiri
                  key={`${c.campaign_id ?? i}`}
                  sira={i + 1}
                  skor={c}
                  etiketler={etiketler}
                  onInspect={onInspect}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/** `CompositeScore` üzerindeki görünür banka adı. */
function bankaAdi(c: CompositeScore): string {
  return c.bank_name ?? c.bank ?? "—";
}

/**
 * Bileşik skor cetveli — bir kampanya türü içinde ON BİR SATIRIN ON BİRİ.
 *
 * ## Radar neden kalktı
 *
 * Burada iki açılır liste ve bir radar çokgeni vardı. Üç sorun taşıyordu.
 *
 * Birincisi doktrinsel: radar çok ölçütü tek şekle katlıyor ve ölçülemeyen
 * ekseni MERKEZE, yani sıfıra çekiyor. Bu panelin tezi bunun tam tersi —
 * «0 puan ürün yok demektir, kötü demek değil» (`fairness_note`). Ölçülemeyeni
 * sıfır gibi çizen bir grafik, kartın üstünde yazan uyarıyı görselde çürütüyordu.
 *
 * İkincisi ölçüldü: seçiciler yalnız `comparable` kayıtları listeliyordu ve o
 * sayı türe göre 0 ile 17 arasında geziniyor — «Finansman»da 1 (radar hiç
 * çizilmiyor), «Sınıflandırılamadı»nda 2, «Yeni Müşteri»de 0. Kullanıcı iki
 * seçenekli bir açılır liste görüyor ve bunu arıza sanıyordu; oysa veri
 * gerçeğiydi. Cetvel o gerçeği gizlemek yerine BASIYOR.
 *
 * Üçüncüsü: iki banka seçmek zorunluluğu, sorulmayan bir soruyu soruyordu.
 * Ekranın adı «en avantajlı»; cevabı bir ikili kıyas değil, bir sıralama.
 *
 * ## Cetvel ne yapıyor
 *
 * Kapsama cetvelinin görsel dili (cetvel.css) burada da geçerli ve aynı
 * sınıfları kullanıyor — panelde tek bir çubuk dili olsun. Üç hâl:
 *
 *   dolu     `comparable` — skor çubuğu, sıralamaya girer
 *   koşullu  skor var ama kıyas dışı — kesikli çerçeve + tarama dokusu
 *   boş      skor yok — kesik taban çizgisi, satır DÜŞMEZ
 *
 * Skor 0–1 aralığında bir orandır, bir alan değeri değil; bu yüzden eksen
 * yüzde olarak basılıyor ve `--fs-xs` mono ile «bileşik skor» diye
 * etiketleniyor. Ölçü birimi belirsiz bırakılmıyor.
 */
function SkorCetveli({ ranked }: { ranked: CompositeScore[] }) {
  if (ranked.length === 0) return null;

  // Sıra numarası YALNIZ kıyaslanabilir satırlara verilir: kıyas dışı bir kayda
  // sıra vermek, onu sıralamaya sokmak olurdu.
  let sonSira = 0;

  return (
    <div className="cetvel" style={{ marginBottom: "var(--sp-4)" }}>
      <div className="cetvel-bas">
        <span className="cetvel-bas-etiket">banka</span>
        <div className="cetvel-eksen" aria-hidden="true">
          <span>0</span>
          <span>0,25</span>
          <span>0,50</span>
          <span>0,75</span>
          <span>1</span>
        </div>
        <span className="cetvel-bas-deger">bileşik skor</span>
      </div>

      <ul className="cetvel-liste" role="list">
        {ranked.map((c, i) => {
          const ad = bankaAdi(c);
          const kiyas = c.comparable && c.score !== null;
          if (kiyas) sonSira += 1;
          const sira = kiyas ? sonSira : null;
          // Skor bir oran; genişlik doğrudan yüzdesi.
          const genislik = c.score === null ? 0 : Math.max(c.score * 100, 0.8);

          const etiket = kiyas
            ? `${ad}: bileşik skor ${trNum(Number((c.score ?? 0).toFixed(3)))}, kıyaslanabilir`
            : c.score !== null
              ? `${ad}: skor var ama kıyas dışı — ${c.note ?? "gerekçe yazılmadı"}`
              : `${ad}: skor hesaplanamadı — ${c.note ?? "ölçülebilir alan yok"}`;

          return (
            <li
              className={c.score === null ? "cetvel-satir cetvel-satir-bos" : "cetvel-satir"}
              key={`${c.campaign_id ?? ad}-${i}`}
            >
              <div className="cetvel-banka">
                {sira !== null ? (
                  <span className="cetvel-alan">{sira}</span>
                ) : (
                  <span className="cetvel-banka-bos" aria-hidden="true">
                    —
                  </span>
                )}
                <span className="cetvel-banka-ad">{ad}</span>
              </div>

              {c.score === null ? (
                <div className="cetvel-ray-bos">
                  <span className="cetvel-cizgi" />
                </div>
              ) : (
                <div className="cetvel-ray" role="img" aria-label={etiket} title={etiket}>
                  <span
                    className={kiyas ? "cetvel-cubuk" : "cetvel-cubuk cetvel-cubuk-kosullu"}
                    style={{ width: `${genislik}%` }}
                  />
                </div>
              )}

              {c.score === null ? (
                <span className="cetvel-yok">skor yok</span>
              ) : (
                <div className="cetvel-deger">
                  <div className="cetvel-deger-satir">
                    <strong
                      className={kiyas ? "cetvel-deger-sayi" : "cetvel-deger-sayi-kisik"}
                    >
                      {trNum(Number(c.score.toFixed(3)))}
                    </strong>
                  </div>
                  <span
                    className={
                      kiyas ? "cetvel-durum cetvel-durum-ok" : "cetvel-durum cetvel-durum-uyari"
                    }
                  >
                    {kiyas ? "kıyaslanabilir" : "kıyas dışı"}
                  </span>
                </div>
              )}
            </li>
          );
        })}
      </ul>

      <p className="cetvel-not">
        Dolu çubuk sıralamaya girer. Kesikli çerçeve «skor hesaplandı ama bu
        kayıt kıyas dışı» der; kesik taban çizgisi «ölçülebilir alan yok» der —
        ikisi de <b>sıfır puan değil</b>. Satırların hiçbiri düşmüyor.
      </p>
    </div>
  );
}

function SkorSatiri({
  sira,
  skor,
  etiketler,
  onInspect,
}: {
  sira: number;
  skor: CompositeScore;
  /** Alan adı → insan etiketi (`/fields`). Eksikse alan adı basılır. */
  etiketler: Record<string, string>;
  onInspect?: (campaignId: number) => void;
}) {
  const [acik, setAcik] = useState(false);
  const skorlanan = skor.components.filter((c) => c.contribution !== null);

  return (
    <>
      <tr>
        <td data-label="Sıra">
          {/* Kıyas dışı satır sıra numarası ALMAZ — sıralamada yeri yoktur. */}
          {skor.comparable ? (
            <span className={`rank-pill${sira === 1 ? " first" : ""}`}>{sira}</span>
          ) : (
            <span className="faint">—</span>
          )}
        </td>
        <td data-label="Banka">
          {skor.bank_name ?? skor.bank ?? "—"}
          {!skor.comparable && (
            <div className="small">
              <span className="badge badge-warn">kıyas dışı</span>
            </div>
          )}
        </td>
        <td data-label="Skor" className="num">
          {yuzde(skor.score)}
        </td>
        <td data-label="Kapsama" className="num">
          {yuzde(skor.coverage)}
        </td>
        <td data-label="Ölçütler">
          <button
            type="button"
            className="btn-link"
            aria-expanded={acik}
            onClick={() => setAcik((a) => !a)}
          >
            {acik ? "gizle" : `${skorlanan.length}/${skor.components.length} ölçüt`}
          </button>
          {skor.note && <div className="small muted">{skor.note}</div>}
        </td>
        <td data-label="Belge">
          {skor.campaign_id !== null && onInspect ? (
            <button
              type="button"
              className="btn-link"
              onClick={() => onInspect(skor.campaign_id!)}
            >
              belgeye git (#{skor.campaign_id})
            </button>
          ) : (
            <span className="faint small">—</span>
          )}
        </td>
      </tr>

      {acik && (
        <tr>
          <td colSpan={6}>
            <dl className="kv">
              {skor.components.map((c) => (
                <div key={c.field_name} style={{ display: "contents" }}>
                  {/* İnsan etiketi SANS, alan adı MONO ve altında: ölçüt bir
                      ürün özelliği (sistemin sesi), alan adı ise makine
                      verisi. Kanıt ekranının künyesiyle aynı desen. Etiket
                      okunamazsa alan adı tek başına kalır — uydurma bir
                      Türkçe başlık üretilmez. */}
                  <dt>
                    {etiketler[c.field_name] ?? c.field_name}
                    {etiketler[c.field_name] && (
                      <div className="mono faint">{c.field_name}</div>
                    )}
                  </dt>
                  <dd>
                    {formatValue(c.value, c.field_name)}
                    {c.contribution === null ? (
                      // Skorlanamayan alan CEZALANDIRILMAZ, kıyas dışı bırakılır.
                      <span className="small muted">
                        {" "}
                        — skorlanmadı{c.note ? `: ${c.note}` : ""}
                      </span>
                    ) : (
                      <span className="small muted">
                        {" "}
                        — normalize {yuzde(c.normalized)} × ağırlık{" "}
                        {trNum(c.weight)} = {trNum(c.contribution)}
                      </span>
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </td>
        </tr>
      )}
    </>
  );
}
