"use client";

/**
 * Zor vaka tezgâhı — canlı çıkarım + altın küme karşılaştırması.
 *
 * İlgili: src/api/zor_vaka.py (vaka listesi ve karşılaştırma kararı),
 *         src/api/main.py (`GET /zor-vakalar`, `POST /extract`)
 *         ../styles/zorvaka.css
 *
 * ## Neden yeniden yazıldı — ölçülen kusur
 *
 * Bu ekran 313 satırlık bir GELİŞTİRİCİ formuydu: bir metin kutusu, aşağı
 * akışta hiçbir karşılığı olmayan serbest bir banka etiketi ve dört ADET ELLE
 * YAZILMIŞ örnek. O dört metin korpustan gelmiyordu, dolayısıyla ekran "sistem
 * çalışıyor" diyordu ama "sistem gerçek ve ZOR veride çalışıyor" demiyordu.
 * Kendi yazdığın metinden kendi çıkardığın değer hiçbir şeyin kanıtı değildir:
 * karşılaştırılacak bir referans yoktu.
 *
 * Şimdi malzeme korpusun kendisinden geliyor: altın kümedeki 40 ZOR belge,
 * gerçek banka metniyle, anotasyonlu altın değerleriyle ve her değerin
 * belgede birebir geçen dayanağıyla.
 *
 * ## Ekranın omurgası: SOL model, SAĞ altın küme
 *
 * Jüriye gösterilecek tek şey "model bir şeyler üretti" değil, "modelin
 * ürettiği şey doğru mu" olmalı. Bu yüzden tablo iki sütunludur ve karar
 * SUNUCUDA verilir (ölçüm koşusunun kullandığı eşleştiricilerle) — ekranda
 * ikinci bir "doğru" tanımı yazılsaydı, jüriye gösterilen tablo ile rapordaki
 * F1 sessizce ayrışabilirdi.
 *
 * ## Serbest metin yolu neden İKİNCİL
 *
 * Kaldırılmadı: jüri üyesi kendi metnini yapıştırmak isteyebilir ve bu yol
 * sistemin gerçekten canlı koştuğunun en doğrudan kanıtıdır. Ama varsayılan
 * olamaz, çünkü referanssızdır — doğruluğu hakkında hiçbir şey söylemez.
 */

import { useMemo, useState } from "react";
import { api, toDisplayError } from "../lib/api";
import type {
  ExtractField,
  ExtractResult,
  GoldAlan,
  GoldDurum,
  ZorVaka,
  ZorVakaListesi,
} from "../lib/api";
import {
  confidenceSourceLabel,
  contradictionLabel,
  extractorClass,
  extractorLabel,
  formatValue,
} from "../lib/format";
import ConfidenceBadge from "./ConfidenceBadge";
import { ErrorNotice, Loading } from "./ErrorNotice";
import SourceSpanView from "./SourceSpanView";
import { useAsync } from "../lib/useAsync";
import "../styles/zorvaka.css";

/**
 * Karşılaştırma durumlarının Türkçe karşılığı.
 *
 * Sunucu İngilizce ve SABİT kimlikler döndürür; sözel karşılık burada
 * üretilir — `extractor` ve güven kaynağı etiketlerinde olduğu gibi.
 * `uydurma` ayrı bir satır hak eder: altın küme "kontrol ettim, bu belgede
 * YOK" dediği bir alanda üretilen değer, yanlış bir değer değil uydurmadır.
 */
const DURUM: Record<GoldDurum, { ad: string; sinif: string; not: string }> = {
  match: {
    ad: "Eşleşti",
    sinif: "zv-durum zv-durum-match",
    not: "Kanonik biçimde birebir aynı.",
  },
  equivalent: {
    ad: "Anlamca eşdeğer",
    sinif: "zv-durum zv-durum-equivalent",
    not: "Biçim farklı, taşıdığı bilgi aynı.",
  },
  mismatch: {
    ad: "Uyuşmadı",
    sinif: "zv-durum zv-durum-mismatch",
    not: "İki ölçüm modunda da eşleşmedi.",
  },
  missed: {
    ad: "Model bulamadı",
    sinif: "zv-durum zv-durum-missed",
    not: "Altın kümede değer var, model üretmedi.",
  },
  fabricated: {
    ad: "Uydurma",
    sinif: "zv-durum zv-durum-fabricated",
    not: "Altın kümede bu alan yok; üretilen değerin dayanağı da yok.",
  },
  correct_absence: {
    ad: "Doğru boşluk",
    sinif: "zv-durum zv-durum-absence",
    not: "Altın kümede yok; model de değer uydurmadı.",
  },
  unclear: {
    ad: "Belirsiz",
    sinif: "zv-durum zv-durum-nazik",
    not: "Anotatör karar veremedi; ölçüm dışında.",
  },
  out_of_scope: {
    ad: "Referans yok",
    sinif: "zv-durum zv-durum-nazik",
    not: "Altın kümede bu alan değerlendirilmemiş.",
  },
};

/** Özet kutularında gösterilecek durumlar ve sırası. */
const OZET_SIRASI: GoldDurum[] = [
  "match",
  "equivalent",
  "mismatch",
  "missed",
  "fabricated",
  "correct_absence",
];

/** Tabloda birleştirilmiş satır: solda model, sağda altın küme. */
type Satir = {
  field: string;
  label: string;
  model: ExtractField | null;
  gold: GoldAlan | null;
};

/** Serbest metin yolunda kullanılan banka etiketi — hiçbir kayda yazılmaz. */
const SERBEST_BANKA = "serbest-metin";

export default function ExtractLive() {
  const liste = useAsync<ZorVakaListesi>(() => api.zorVakalar(), []);

  const [etiket, setEtiket] = useState<string | null>(null);
  const [seciliId, setSeciliId] = useState<string | null>(null);
  const [sonuc, setSonuc] = useState<ExtractResult | null>(null);
  const [hata, setHata] = useState<unknown>(null);
  const [mesgul, setMesgul] = useState(false);
  const [aktifAlan, setAktifAlan] = useState<string | null>(null);
  const [serbestMetin, setSerbestMetin] = useState("");

  const vakalar = useMemo(() => liste.data?.vakalar ?? [], [liste.data]);
  const suzulmus = useMemo(
    () =>
      etiket === null
        ? vakalar
        : vakalar.filter((v) => v.zor_etiketler.includes(etiket)),
    [vakalar, etiket],
  );
  const secili: ZorVaka | null =
    vakalar.find((v) => v.id === seciliId) ?? null;

  async function calistir(metin: string, banka: string, goldId?: string) {
    if (!metin.trim()) {
      setHata(new Error("Çıkarım için bir metin gerekiyor."));
      return;
    }
    setMesgul(true);
    setHata(null);
    setAktifAlan(null);
    try {
      setSonuc(await api.extract(metin, banka, goldId));
    } catch (e) {
      setHata(e);
      setSonuc(null);
    } finally {
      setMesgul(false);
    }
  }

  const modelAlanlari = useMemo(
    () => new Map((sonuc?.fields ?? []).map((f) => [f.field, f])),
    [sonuc],
  );
  const satirlar: Satir[] = useMemo(() => {
    if (!sonuc) return [];
    if (sonuc.gold) {
      return sonuc.gold.fields.map((g) => ({
        field: g.field,
        label: g.label,
        model: modelAlanlari.get(g.field) ?? null,
        gold: g,
      }));
    }
    return sonuc.fields.map((f) => ({
      field: f.field,
      label: f.label,
      model: f,
      gold: null,
    }));
  }, [sonuc, modelAlanlari]);

  const vurgulanan: ExtractField | null =
    sonuc?.fields.find((f) => f.field === aktifAlan) ?? null;

  return (
    <div className="stack">
      <section className="card">
        <h2>Zor Vaka Tezgâhı</h2>
        <p className="lede">
          Panelin geri kalanı önceden hazırlanmış veri tabanından okur (demo
          güvenliği). Burası canlı yol — ve boş bir metin kutusu değil: altın
          kümenin <b>zor</b> işaretli belgeleri, gerçek banka metniyle.
          Soldaki her şey siz düğmeye bastığınızda üretilir; sağdaki değerler
          önceden elle anotasyonlanmış referanstır.
        </p>
        <p className="small muted">
          Kaynak doğrulaması da o anda hesaplanır: çıkarılan değerin metindeki
          karakter aralığı yeniden ölçülür, kayıtlı bir işaretten okunmaz.
          Aralık gerçekten o değeri gösteriyorsa alan <b>doğrulandı</b> damgası
          alır.
        </p>

        {liste.loading && <Loading label="Zor vakalar yükleniyor…" />}
        {!!liste.error && <ErrorNotice error={liste.error} />}

        {liste.data && !liste.data.kaynak_var && (
          <div className="notice notice-warn">
            <strong>Zor vaka kümesi bu kurulumda yok</strong>
            Anotasyonlu altın küme dosyası bulunamadı. Aşağıdaki serbest metin
            yolu çalışmaya devam eder, ama karşılaştırılacak bir referans
            olmaz.
          </div>
        )}

        {liste.data && liste.data.kaynak_var && (
          <>
            <div className="stats zv-ozet">
              <div className="stat">
                <div className="k">Zor belge</div>
                <div className="v">
                  {liste.data.zor_belge}
                  <span className="small muted"> / {liste.data.toplam_belge}</span>
                </div>
              </div>
              {liste.data.etiketler
                .filter((e) => e.adet > 0)
                .map((e) => (
                  <div key={e.etiket} className="stat">
                    <div className="k">{e.ad}</div>
                    <div className="v">{e.adet}</div>
                  </div>
                ))}
            </div>

            <div className="chip-group">
              <span className="chip-group-label" id="zv-zorluk-basligi">
                Zorluk türü
              </span>
              <div className="row" aria-labelledby="zv-zorluk-basligi">
                <button
                  type="button"
                  className="chip"
                  aria-pressed={etiket === null}
                  onClick={() => setEtiket(null)}
                >
                  Tümü ({vakalar.length})
                </button>
                {liste.data.etiketler
                  .filter((e) => e.adet > 0)
                  .map((e) => (
                    <button
                      key={e.etiket}
                      type="button"
                      className="chip"
                      aria-pressed={etiket === e.etiket}
                      title={e.aciklama}
                      onClick={() =>
                        setEtiket(etiket === e.etiket ? null : e.etiket)
                      }
                    >
                      {e.ad} ({e.adet})
                    </button>
                  ))}
              </div>
            </div>

            {etiket !== null && (
              <p className="small muted zv-etiket-aciklama">
                {liste.data.etiketler.find((e) => e.etiket === etiket)?.aciklama}
              </p>
            )}

            <div className="zv-liste">
              {suzulmus.map((v) => (
                <button
                  key={v.id}
                  type="button"
                  className="zv-vaka"
                  aria-pressed={seciliId === v.id}
                  onClick={() => {
                    setSeciliId(v.id);
                    setSonuc(null);
                    setHata(null);
                    setAktifAlan(null);
                  }}
                >
                  <span className="zv-vaka-ust">
                    <b>{v.banka_adi}</b>
                    <span className="small muted">
                      {v.kampanya_turu ?? "tür belirsiz"}
                    </span>
                  </span>
                  <span className="zv-vaka-etiketler">
                    {v.zor_etiketler.map((t) => (
                      <span key={t} className="pill">
                        {liste.data?.etiketler.find((e) => e.etiket === t)?.ad ?? t}
                      </span>
                    ))}
                  </span>
                  <span className="zv-vaka-onizleme">{v.onizleme}</span>
                  <span className="small faint">
                    {v.metin_uzunlugu} karakter · altında {v.altin_alan_sayisi}{" "}
                    değer, {v.altinda_yok_sayisi} “yok” kaydı
                  </span>
                </button>
              ))}
            </div>
          </>
        )}
      </section>

      {secili && (
        <section className="card">
          <h3>{secili.banka_adi} — seçili vaka</h3>
          <p className="small muted">
            {secili.kaynak_adresi ? (
              <a href={secili.kaynak_adresi} target="_blank" rel="noreferrer">
                Kaynak sayfa
              </a>
            ) : (
              "Kaynak adresi kayıtlı değil"
            )}
            {" · "}
            {secili.zor_etiketler
              .map(
                (t) =>
                  liste.data?.etiketler.find((e) => e.etiket === t)?.ad ?? t,
              )
              .join(", ")}
          </p>

          <div className="zv-metin">{secili.metin}</div>

          <div className="row zv-eylem">
            <button
              type="button"
              className="btn"
              onClick={() => calistir(secili.metin, secili.banka, secili.id)}
              disabled={mesgul}
            >
              {mesgul ? "Çıkarım koşuyor…" : "Çıkarımı çalıştır"}
            </button>
            <span className="small faint">
              Metin olduğu gibi gönderilir; sonuç altın değerlerle yan yana
              çizilir.
            </span>
          </div>

          {!!hata && (
            <div className="zv-hata">
              <ErrorNotice error={hata} />
              <p className="small muted">{toDisplayError(hata).hint}</p>
            </div>
          )}
        </section>
      )}

      {sonuc && (
        <>
          {sonuc.gold && (
            <section className="card">
              <h2>Model çıktısı ↔ altın küme</h2>
              {!sonuc.gold.text_matches && (
                <div className="notice notice-warn">
                  <strong>Metin değiştirilmiş</strong>
                  Çıkarım altın belgenin metniyle birebir aynı olmayan bir
                  metin üzerinde koştu. Karşılaştırma yine çizilir, ama artık
                  aynı belgenin ölçümü değildir.
                </div>
              )}
              <div className="stats">
                {OZET_SIRASI.map((d) => (
                  <div
                    key={d}
                    className={
                      d === "fabricated" && sonuc.gold!.summary[d] > 0
                        ? "stat zv-stat-uyari"
                        : "stat"
                    }
                  >
                    <div className="k">{DURUM[d].ad}</div>
                    <div className="v">{sonuc.gold!.summary[d]}</div>
                  </div>
                ))}
              </div>
              <p className="small muted">
                <b>Uydurma</b> sayacı bu ekranın en önemli sayısıdır: altın
                küme “bu belgede bu alan yok” dediği hâlde model bir değer
                üretmişse orada sayılır. <b>Doğru boşluk</b> ise tersidir —
                model olmayan bilgiyi uydurmadan geçmiştir.
                {sonuc.gold.summary.unclear + sonuc.gold.summary.out_of_scope >
                  0 && (
                  <>
                    {" "}
                    {sonuc.gold.summary.unclear +
                      sonuc.gold.summary.out_of_scope}{" "}
                    alan ölçüm dışında: anotatör kararsız kalmış ya da o alan
                    hiç değerlendirilmemiş. Referans olmayan yerde doğru/yanlış
                    denmez.
                  </>
                )}
              </p>
            </section>
          )}

          <section className="card">
            <h2>Sonuç</h2>
            <div className="stats zv-ozet">
              <div className="stat">
                <div className="k">Kampanya türü</div>
                <div className="v zv-v-orta">{sonuc.campaign_type ?? "—"}</div>
              </div>
              <div className="stat">
                <div className="k">Tür güveni</div>
                <div className="v zv-v-orta">
                  {sonuc.campaign_type_confidence === null
                    ? "—"
                    : sonuc.campaign_type_confidence.toFixed(2).replace(".", ",")}
                </div>
              </div>
              <div className="stat">
                <div className="k">Bulunan alan</div>
                <div className="v">
                  {sonuc.fields.length}
                  <span className="small muted">
                    {" "}
                    / {sonuc.fields.length + sonuc.missing_fields.length}
                  </span>
                </div>
              </div>
              <div className="stat">
                <div className="k">Çelişki</div>
                <div
                  className={
                    sonuc.contradictions.length ? "v zv-kotu" : "v zv-iyi"
                  }
                >
                  {sonuc.contradictions.length}
                </div>
              </div>
              <div className="stat">
                <div className="k">Yerel dil modeli</div>
                <div className="v zv-v-orta">
                  {sonuc.llm_available ? "açık" : "kapalı"}
                </div>
              </div>
            </div>

            {!sonuc.llm_available && (
              <div className="notice notice-info">
                <strong>Yerel dil modeli kapalı — sonuçlar kural katmanından</strong>
                Hibrit mimaride kurallar birincildir; dil modeli yalnızca
                kuralların kaçırdığı örtük ifadeler için devreye girer. Model
                servisi ayakta değilken sistem çalışmaya devam eder.
              </div>
            )}

            {sonuc.contradictions.length > 0 && (
              <div className="zv-celiskiler">
                {sonuc.contradictions.map((c, i) => (
                  <div key={i} className="notice notice-error">
                    <strong>{contradictionLabel(c.kind)}</strong>
                    {c.detail}
                    <div className="small mono zv-celiski-alan">
                      {c.fields.join(", ")}
                    </div>
                  </div>
                ))}
              </div>
            )}

            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th scope="col">Alan</th>
                    <th scope="col">Model çıktısı (canlı)</th>
                    {sonuc.gold && <th scope="col">Altın küme (referans)</th>}
                    {sonuc.gold && <th scope="col">Karar</th>}
                  </tr>
                </thead>
                <tbody>
                  {satirlar.map((s) => (
                    <tr
                      key={s.field}
                      className={aktifAlan === s.field ? "selected" : undefined}
                    >
                      <td>{s.label}</td>
                      <td className="zv-model">
                        {s.model ? (
                          <>
                            <div className="zv-deger">
                              {formatValue(s.model.value, s.field)}
                            </div>
                            {s.model.raw_value && (
                              <div className="small mono zv-ham">
                                «{s.model.raw_value.trim()}»
                              </div>
                            )}
                            <div className="zv-rozetler">
                              <ConfidenceBadge
                                value={s.model.confidence}
                                source={s.model.confidence_source}
                              />
                              <span className={extractorClass(s.model.extractor)}>
                                {extractorLabel(s.model.extractor)}
                              </span>
                              {s.model.span_start === null ? (
                                <span className="badge badge-warn">
                                  kaynak yok
                                </span>
                              ) : (
                                <>
                                  <button
                                    type="button"
                                    className="btn-link mono"
                                    onClick={() =>
                                      setAktifAlan(
                                        aktifAlan === s.field ? null : s.field,
                                      )
                                    }
                                  >
                                    [{s.model.span_start}, {s.model.span_end})
                                  </button>
                                  <span
                                    className={
                                      s.model.span_verified
                                        ? "badge badge-ok"
                                        : "badge badge-warn"
                                    }
                                  >
                                    {s.model.span_verified
                                      ? "doğrulandı"
                                      : "doğrulanamadı"}
                                  </span>
                                </>
                              )}
                            </div>
                            <div className="small faint">
                              {confidenceSourceLabel(s.model.confidence_source)}
                            </div>
                          </>
                        ) : (
                          <span className="muted">değer üretilmedi</span>
                        )}
                      </td>
                      {sonuc.gold && (
                        <td className="zv-altin">{altinHucre(s.gold)}</td>
                      )}
                      {sonuc.gold && s.gold && (
                        <td>
                          <span className={DURUM[s.gold.status].sinif}>
                            {DURUM[s.gold.status].ad}
                          </span>
                          <div className="small muted zv-gerekce">
                            {s.gold.reason || DURUM[s.gold.status].not}
                          </div>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {!sonuc.gold && sonuc.missing_fields.length > 0 && (
              <>
                <h3>Bulunamayan alanlar ({sonuc.missing_fields.length})</h3>
                <p className="small muted zv-sikis">
                  Bu alanlar metinde geçmiyor. Sistem boş bırakır —{" "}
                  <b>değer uydurmaz</b>.
                </p>
                <div className="field-list">
                  {sonuc.missing_fields.map((m) => (
                    <span key={m.field} className="pill">
                      {m.label}
                    </span>
                  ))}
                </div>
              </>
            )}
          </section>

          {vurgulanan && (
            <section className="card">
              <h2>Kaynak vurgulaması — {vurgulanan.label}</h2>
              <SourceSpanView
                text={sonuc.text}
                span={vurgulanan}
                rawValue={vurgulanan.raw_value}
                defaultFullText
              />
            </section>
          )}
        </>
      )}

      <section className="card">
        <details className="zv-serbest">
          <summary>Kendi metninizi deneyin (referanssız)</summary>
          <p className="small muted">
            Bu yol sistemin canlı koştuğunun en doğrudan kanıtıdır, ama
            karşılaştırılacak bir altın değeri yoktur: sonuç doğruluk hakkında
            bir şey söylemez, yalnız sistemin ne ürettiğini gösterir.
          </p>
          <label className="small muted" htmlFor="zv-serbest-metin">
            Kampanya metni
          </label>
          <textarea
            id="zv-serbest-metin"
            className="textarea"
            value={serbestMetin}
            onChange={(e) => setSerbestMetin(e.target.value)}
            placeholder="Bir katılım bankası kampanya metnini buraya yapıştırın…"
          />
          <div className="row zv-eylem">
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setSeciliId(null);
                calistir(serbestMetin, SERBEST_BANKA);
              }}
              disabled={mesgul}
            >
              {mesgul ? "Çıkarım koşuyor…" : "Serbest metinde çalıştır"}
            </button>
            <span className="small faint">{serbestMetin.length} karakter</span>
          </div>
        </details>
      </section>
    </div>
  );
}

/**
 * Altın küme hücresi.
 *
 * Boş bırakmak YASAK: boş bir hücre uyuşmazlık gibi okunur. Alanın altın
 * kümede olmama sebebi ("kontrol edildi, yok" / "hiç değerlendirilmedi" /
 * "anotatör kararsız") açıkça yazılır.
 */
function altinHucre(g: GoldAlan | null) {
  if (!g) return <span className="muted">—</span>;
  if (g.gold_present) {
    return (
      <>
        <div className="zv-deger">{formatValue(g.gold_value, g.field)}</div>
        {g.gold_span && <div className="zv-kanit">«{g.gold_span.trim()}»</div>}
      </>
    );
  }
  if (g.gold_absent) return <span className="zv-yok">altında yok</span>;
  if (g.status === "unclear")
    return <span className="muted">anotatör kararsız</span>;
  return <span className="muted">değerlendirilmemiş</span>;
}
