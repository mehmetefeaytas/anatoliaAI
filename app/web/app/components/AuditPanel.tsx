"use client";

/**
 * Kanıt / denetim ekranı — bir sayı ve onu doğuran cümle, YAN YANA.
 *
 * İlgili: src/api/main.py `GET /campaigns/{id}/text`, ../styles/kanit.css,
 *         ./SourceSpanView.tsx, ./ConfidenceBadge.tsx, ./SummaryNotice.tsx
 *
 * Jürinin denetim ihtiyacı şu beş soruyu aynı anda sormaktır ve panel beşini de
 * tek ekranda yanıtlar:
 *   1. Değer nereden geldi?        → kaynak URL + belge no
 *   2. Metinde tam olarak nerede?  → karakter offset'i + vurgulama
 *   3. Ne kadar eminiz?            → güven skoru + güven KAYNAĞI
 *   4. Hangi katman üretti?        → rule / ner / llm
 *   5. Çelişki var mı?             → belge düzeyinde çelişki listesi
 *
 * ## Neden iki kolon, neden sağ kolon daha geniş
 *
 * Ekran eskiden üst üste iki karttı: önce tablo, sonra kaynak metin. Bir offset'e
 * basıldığında vurgulanan cümle EKRANIN ALTINDA kalıyordu ve kullanıcı iddia ile
 * kanıtı aynı anda göremiyordu — oysa bu ürünün tek iddiası ikisinin bağlı
 * olduğu. Künye solda, bankanın cümlesi sağda: göz ikisini birlikte görüyor.
 *
 * Sağ kolon KASITLI olarak geniş (`1fr` / `1.15fr`): bu ekranın öznesi çıkarılan
 * değer değil, değerin çıkarıldığı CÜMLEDİR. Sol kolon kısa satırlardan oluşan
 * bir künye, sağ kolon okunacak serif bir gövde.
 *
 * ## Etkin alan neden bir state DEĞİL de türetim
 *
 * `active` yalnız kullanıcının SEÇİMİNİ taşır. Seçim yoksa etkin alan, offset'i
 * olan ilk alandır: kanıt ekranının vurgusuz açılması, tezi ispatlayacak yüzeyi
 * boş bırakmak olurdu. Belge değişince seçim `useEffect` ile sıfırlanmaz —
 * türetim zaten yeni belgenin ilk alanına düşer; iki state'i senkron tutmaya
 * çalışan bir efekt, belge değişimiyle seçim değişimi arasında bir kare
 * boyunca yanlış vurgu basıyordu.
 *
 * ## Ölçülemeyen alan
 *
 * Künye satırları DÜŞMEZ. `sha256` içerik özeti API'de yoktur ve bu satır
 * «kaydedilmedi» diyerek durur: boşluğun kendisi bir bilgidir ve uydurulmuş bir
 * özet, panelin tamamını değersizleştirirdi (CLAUDE.md §19 — halüsinasyon
 * yasağı).
 */

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { CampaignFieldDetail, CampaignSummary, Extractor } from "../lib/api";
import {
  confidenceSourceLabel,
  contradictionLabel,
  extractorClass,
  extractorLabel,
  formatValue,
  trNum,
} from "../lib/format";
import { useAsync } from "../lib/useAsync";
import BelgeSecici from "./BelgeSecici";
import BelgeyiIndir from "./BelgeyiIndir";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import SourceSpanView from "./SourceSpanView";
import SourceText from "./SourceText";
import SummaryNotice from "./SummaryNotice";

type Props = {
  campaigns: CampaignSummary[];
  /** Dışarıdan (ör. çelişki listesinden) seçilen belge. */
  selectedId?: number | null;
};

/**
 * Rozetin YANINDAKİ cümle — «kural» ile «llm» arasındaki farkı rozet rengi
 * değil bu cümle anlatır (renk tek sinyal değil).
 *
 * `ner` bu teslimde ÜRETİLMİYOR (CLAUDE.md §3): `Extractor.NER` hiçbir kod
 * yolunda oluşmuyor. Karşılığı yine yazılı, çünkü şema onu hâlâ tanıyor ve
 * eksik bir eşleme, gelecekte sessiz bir boşluk bırakırdı.
 */
const KATMAN_NOTU: Record<Extractor, string> = {
  rule: "Deterministik kural çıkardı; yerel model bu alana dokunmadı.",
  ner: "Varlık çıkarımı katmanı üretti (bu teslimde kullanılmıyor).",
  llm: "Kuralların bulamadığı alanı yerel model doldurdu.",
};

/**
 * Normalize değerin «sayı» değil «paragraf» olduğu eşik — ÖLÇÜLDÜ.
 *
 * `kampanya_kosullari` ve `hedef_kitle` liste döndürür ve birleşmiş metin 1.100
 * karaktere çıkabiliyor. 28px/600 ölçüsü o metni bir başlığa çeviriyor, sol
 * kolonu 1.400px'e uzatıyor ve iki kolonun üst hizasını kaybettiriyordu. 40
 * karakter, en uzun gerçek SAYISAL değerin («1.500,00 – 2.000,00 TL» + birim)
 * rahatça üstünde, en kısa liste değerinin ise altında.
 */
const UZUN_DEGER = 40;

/**
 * Belge künyesi: `banka-slug/yol`. Adres ayrıştırılamazsa yalnız banka slug'ı
 * yazılır — bozuk bir adresi olduğu gibi basmak künyeyi okunmaz kılardı.
 */
function belgeYolu(bank: string, url: string | null): string {
  if (!url) return bank;
  try {
    const yol = new URL(url).pathname.replace(/\/+$/, "");
    return yol && yol !== "/" ? `${bank}${yol}` : bank;
  } catch {
    return bank;
  }
}

export default function AuditPanel({ campaigns, selectedId }: Props) {
  const [id, setId] = useState<number | null>(selectedId ?? campaigns[0]?.id ?? null);
  const [active, setActive] = useState<string | null>(null);

  useEffect(() => {
    if (selectedId != null) {
      setId(selectedId);
      setActive(null);
    }
  }, [selectedId]);

  const doc = useAsync(
    () => (id === null ? Promise.resolve(null) : api.campaignText(id)),
    [id],
  );

  /* Şema alan sayısı: boş hâlin KESRİ («2 / 12 alan») için. Sayı istemcide
   * sabitlenmiyor — `/fields` uzunluğu neyse o. Uç gelmezse kesir hiç
   * basılmaz; uydurulmuş bir payda, boşluğun ölçüsünü yalanlardı. */
  const alanMeta = useAsync(() => api.fields(), []);

  if (campaigns.length === 0) {
    return (
      <section className="card">
        <h2>Kanıt defteri</h2>
        <EmptyNotice title="Denetlenecek belge yok">
          Veritabanı boş görünüyor. Pipeline fixture modunda çalıştı mı?
        </EmptyNotice>
      </section>
    );
  }

  const alanlar: CampaignFieldDetail[] = doc.data?.fields ?? [];
  /* Seçim yoksa: offset'i olan ilk alan. Hiçbirinde offset yoksa ilk alan —
   * vurgulanamayan bir değer de denetlenebilir bir değerdir. */
  const varsayilan =
    alanlar.find((f) => f.span_start !== null) ?? alanlar[0] ?? null;
  const activeField =
    (active === null ? null : alanlar.find((f) => f.field === active) ?? null) ??
    varsayilan;
  const alanKesri = alanMeta.data
    ? `${alanlar.length} / ${alanMeta.data.length} alan`
    : undefined;
  /** Etkin alanın Türkçeleşmiş normalize değeri — ölçüsü uzunluğuna bağlı. */
  const aktifDeger = activeField
    ? formatValue(activeField.canonical_value, activeField.field)
    : "";

  return (
    <div className="stack">
      <section className="card">
        <h2>Kanıt defteri</h2>
        <p className="lede">
          Her değer için tek ekranda: kaynak URL, kaynak span, güven skoru ve
          kaynağı, hangi katmanın ürettiği ve çelişki durumu.
        </p>

        {/* Belge seçimi 1.774 seçenekli çıplak bir <select>'ti — arayüzdeki en
            büyük gezinme boşluğu. Aranamayan bir liste, içindeki 126 sözleşmeyi
            ve 458 süresi dolmuş belgeyi de bulunamaz kılıyordu. Seçici artık
            arama ve yön çipleri taşıyor; süzme sunucuda.

            SARMALAYICI KALDIRILDI. Seçici bir `.row-tight` içindeydi ve o sınıf
            SARMALANMAYAN bir flex satırı — küçük satır içi denetimler (etiket +
            açılır liste) için. Blok genişliğinde bir panel oraya konduğunda
            flex öğesi oluyor, `min-width: auto` ile min-içerik genişliğinin
            altına inemiyor ve içindeki `auto-fit` süzgeç ızgarası belirsiz
            genişlikte her süzgeç için ayrı bir 220px kolon açıyordu.

            ÖLÇÜLDÜ (2026-08-12, tarayıcı): seçici 1.900px'e çıkıyor, kabuk
            1.148px ve sayfa 638px yatay taşıyordu — sıralama listesi ve
            süzgeçler sağa doğru ekrandan çıkıyordu. Seçici artık kartın
            doğrudan blok çocuğu. */}
        <BelgeSecici
          seciliId={id}
          onSec={(yeni) => {
            setId(yeni);
            setActive(null);
          }}
        />

        {doc.loading && <Loading />}
        {!!doc.error && (
          <div style={{ marginTop: "var(--sp-3)" }}>
            <ErrorNotice error={doc.error} />
          </div>
        )}

        {doc.data && (
          <>
            <dl className="kv" style={{ marginTop: "var(--sp-4)" }}>
              <dt>Banka</dt>
              <dd>{doc.data.bank_name || doc.data.bank}</dd>
              <dt>Kampanya türü</dt>
              <dd>{doc.data.campaign_type ?? "—"}</dd>
              <dt>Kaynak URL</dt>
              <dd className="mono">
                {doc.data.source_url ? (
                  // Sınıf baskı içindir: kâğıtta bağlantının nereye gittiği
                  // görünmez, `baski.css` adresi metne açar. Belge kaynağı bu
                  // projenin tezi olduğu için çıktıda da izlenebilir kalmalı.
                  <a
                    className="kaynak-baglanti"
                    href={doc.data.source_url}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    {doc.data.source_url}
                  </a>
                ) : (
                  "—"
                )}
              </dd>
              <dt>Toplanma zamanı</dt>
              <dd className="mono">{doc.data.scraped_at ?? "kaydedilmedi"}</dd>
              <dt>Belge uzunluğu</dt>
              <dd className="mono">{trNum(doc.data.text_length)} karakter</dd>
              <dt>Çelişki</dt>
              <dd>
                {doc.data.contradictions.length === 0 ? (
                  <span className="badge badge-ok">yok</span>
                ) : (
                  <span className="badge badge-bad">
                    {doc.data.contradictions.length} bulgu
                  </span>
                )}
              </dd>
            </dl>

            {doc.data.contradictions.length > 0 && (
              <div style={{ marginTop: "var(--sp-4)", display: "grid", gap: "var(--sp-2)" }}>
                {doc.data.contradictions.map((c, i) => (
                  <div key={i} className="notice notice-error">
                    <strong>{contradictionLabel(c.kind)}</strong>
                    {c.detail}
                  </div>
                ))}
              </div>
            )}

            <h3>Çıkarılan alanlar ({alanlar.length})</h3>
            {alanlar.length === 0 ? (
              /* Kesir boşluğun ÖLÇÜSÜDÜR: «0 / 12 alan» hem satırın durduğunu
                 hem neyin ölçülmediğini söyler. `alan` propu verilmiyor —
                 burada tek bir alan yok, hepsi boş; `%0` ≠ `null` ayrımı
                 alan düzeyinde anlamlıdır, belge düzeyinde değil. */
              <EmptyNotice
                title="Bu belgeden hiçbir alan çıkarılamadı"
                kesir={alanKesri}
              >
                Metin çıkarım kurallarının hiçbirine uymuyor. Değer uydurulmadı.
              </EmptyNotice>
            ) : (
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">Alan</th>
                      <th scope="col">Değer</th>
                      <th scope="col">Ham ifade</th>
                      <th scope="col">Güven</th>
                      <th scope="col">Güven kaynağı</th>
                      <th scope="col">Katman</th>
                      <th scope="col">Kaynak span</th>
                    </tr>
                  </thead>
                  <tbody>
                    {alanlar.map((f) => (
                      <tr
                        key={f.field}
                        className={
                          activeField?.field === f.field ? "selected" : undefined
                        }
                      >
                        <td>{f.label}</td>
                        <td className="num">
                          <strong>{formatValue(f.canonical_value, f.field)}</strong>
                        </td>
                        <td className="mono">
                          {f.raw_value ? `«${f.raw_value.trim()}»` : "—"}
                        </td>
                        <td>
                          <ConfidenceBadge value={f.confidence} source={f.confidence_source} />
                        </td>
                        <td className="small muted">
                          {confidenceSourceLabel(f.confidence_source)}
                        </td>
                        <td>
                          <span className={extractorClass(f.extractor)}>
                            {extractorLabel(f.extractor)}
                          </span>
                        </td>
                        <td>
                          {f.span_start === null ? (
                            <span className="badge badge-warn">offset yok</span>
                          ) : (
                            <button
                              type="button"
                              className="btn-link mono"
                              aria-expanded={activeField?.field === f.field}
                              title="Bu aralığı sağdaki kaynak metinde vurgula"
                              onClick={() => setActive(f.field)}
                            >
                              [{f.span_start}, {f.span_end}){" "}
                              {f.span_verified ? "✓" : "?"}
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </section>

      {doc.data && (
        <div className="kanit-ikili">
          {/* ---------------- SOL: çıkarılan değer künyesi ---------------- */}
          <section className="card kanit-kunye">
            <div>
              <h2>Çıkarılan değer</h2>
              <span className="kanit-belge-kunye">
                belge #{doc.data.campaign_id ?? id} ·{" "}
                {belgeYolu(doc.data.bank, doc.data.source_url)}
              </span>
            </div>

            {activeField === null ? (
              <EmptyNotice title="Künyesi çizilecek alan yok" kesir={alanKesri}>
                Bu belgeden hiçbir alan çıkarılamadı; sağda belgenin ham metni
                olduğu gibi duruyor.
              </EmptyNotice>
            ) : (
              <dl className="kanit-alan">
                <dt>alan</dt>
                <dd className="kanit-alan-adi">{activeField.field}</dd>

                <dt>normalize değer</dt>
                {/* Sayı ölçüsü SAYIYA aittir: paragraf uzunluğundaki bir değer
                    (koşul listesi, hedef kitle) gövde ölçüsüne düşer ve kendi
                    kaydırma kutusunda kalır — gerekçesi `UZUN_DEGER`de. */}
                <dd
                  className={
                    aktifDeger.length > UZUN_DEGER
                      ? "kanit-deger kanit-deger-uzun"
                      : "kanit-deger"
                  }
                >
                  {aktifDeger}
                </dd>

                {/* Ham ifade BANKANIN sesidir; yoksa satır uydurulmaz ama
                    düşmez de — «çıkarılan değer normalize edildi, ham karşılığı
                    kaydedilmedi» de bir bilgidir. */}
                <dt>ham ifade</dt>
                <dd className="kanit-ham">
                  {activeField.raw_value ? (
                    `«${activeField.raw_value.trim()}»`
                  ) : (
                    <span className="kanit-yok">ham ifade kaydedilmedi</span>
                  )}
                </dd>

                <dt>üreten katman</dt>
                <dd className="kanit-katman">
                  <span className={extractorClass(activeField.extractor)}>
                    {extractorLabel(activeField.extractor)}
                  </span>
                  <span className="kanit-katman-not">
                    {activeField.extractor
                      ? KATMAN_NOTU[activeField.extractor]
                      : "Üreten katman kaydedilmedi."}
                  </span>
                </dd>

                <dt>güven</dt>
                <dd>
                  <ConfidenceBadge
                    value={activeField.confidence}
                    source={activeField.confidence_source}
                    showSource
                  />
                </dd>

                <dt>karakter aralığı</dt>
                <dd className="kanit-aralik">
                  {activeField.span_start === null ||
                  activeField.span_end === null ? (
                    <span className="badge badge-warn">
                      offset kaydedilmedi
                    </span>
                  ) : (
                    <>
                      <span className="kanit-aralik-no">
                        [{activeField.span_start}, {activeField.span_end})
                      </span>
                      <span
                        className={
                          activeField.span_verified
                            ? "badge badge-ok"
                            : "badge badge-warn"
                        }
                      >
                        {activeField.span_verified
                          ? "doğrulandı"
                          : "doğrulanamadı"}
                      </span>
                    </>
                  )}
                </dd>

                {/* İçerik özeti (sha256) API'de YOK. Satır düşmüyor: ölçülemeyen
                    alanın adı ekranda kalır, değeri uydurulmaz. */}
                <dt>içerik özeti</dt>
                <dd className="kanit-yok">
                  içerik özeti (sha256) API yanıtında yok
                  {doc.data.scraped_at
                    ? ` · toplanma: ${doc.data.scraped_at}`
                    : ""}
                </dd>
              </dl>
            )}

            {/* ÜRETİLMİŞ içerik: kesikli `--llm` şeridi + `üretilmiş` rozeti.
                `--warn` KULLANILMAZ — «yerel model bu alanı doldurdu» bir uyarı
                değildir, kendi rengi vardır (bkz. tokens.css `--llm`). */}
            <SummaryNotice
              ozet={doc.data.ozet}
              ozetKaynak={doc.data.ozet_kaynak}
            />
          </section>

          {/* ---------------- SAĞ: kaynak metin ---------------- */}
          <section className="card kanit-kaynak">
            <div className="kanit-kaynak-bas">
              <h3>kaynak metin · bankanın kendi cümlesi</h3>
              <span className="kanit-sayac">
                {trNum(doc.data.text_length)} karakter
              </span>
            </div>

            {activeField ? (
              /* `rawValue` BİLEREK geçilmiyor: ham ifade iki kolon soldaki
                 künyede zaten tam hâliyle duruyor ve metnin üstünde ikinci kez
                 basıldığında 1.100 karakterlik koşul listelerinde kaynak metni
                 ekranın altına itiyordu (ölçüldü, belge #1). Yan panelde
                 (KaynakDipnotu) künye YOK, o yüzden prop kaldırılmadı. */
              <SourceSpanView
                text={doc.data.text}
                span={activeField}
                defaultFullText
                blocks={doc.data.bloklar}
              />
            ) : (
              <SourceText text={doc.data.text} blocks={doc.data.bloklar} />
            )}

            {/* Provenans şeridi: belge nereden geldi, ne zaman toplandı, kâğıda
                nasıl döker. Hepsi mono — bunlar cümle değil, koordinat. */}
            <div className="kanit-provenans">
              {doc.data.source_url ? (
                <a
                  className="kanit-cip kaynak-baglanti"
                  href={doc.data.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  title={doc.data.source_url}
                >
                  source_url ↗
                </a>
              ) : (
                <span className="kanit-cip">source_url: kaydedilmedi</span>
              )}

              {/* Düğme dosya İNDİRMEZ, tarayıcının yazdırma yolunu açar;
                  etiketi «indir» yapmak tek tıkta dosya bekleyen kullanıcıyı
                  yanıltırdı (gerekçesi BelgeyiIndir.tsx başlığında). */}
              <BelgeyiIndir
                ad={`belge-${doc.data.campaign_id ?? id}`}
                etiket="ham belgeyi yazdır · PDF"
              />

              <span className="kanit-cip">
                scraped_at: {doc.data.scraped_at ?? "kaydedilmedi"}
              </span>
            </div>
          </section>
        </div>
      )}
    </div>
  );
}
