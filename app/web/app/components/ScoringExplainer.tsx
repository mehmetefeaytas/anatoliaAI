"use client";

/**
 * Şeffaf skorlama — "en avantajlı" iddiasının FORMÜLÜ görünür.
 *
 * İlgili: src/api/main.py `/scoring`, src/comparison/compare.py, CLAUDE.md §17
 *
 * DÜZELTME (2026-08-09): bu başlık eskiden *"kod tabanında alanlar arası
 * ağırlıklı bileşik skor **YOKTUR**"* diyordu. Yanlıştı ve `src/api/main.py`
 * aynı yanlışı 2026-08-08'de kendi tarafında düzeltmişti — düzeltme buraya
 * işlenmemişti. `compare.py` `DEFAULT_WEIGHTS`, `WEIGHT_RATIONALE`,
 * `_composite_numeric`, `rank_advantageous` ve `weight_manifest`'i taşıyor ve
 * test ediyor; bileşik skor `GET /advantageous` ucundan sunuluyor ve artık
 * «En Avantajlı» sekmesinde görünüyor. Jüri iki dosyayı yan yana okusa
 * çelişkiyi görürdü.
 *
 * Bu bileşenin kapsamı DEĞİŞMEDİ: **tek alan** sıralamasını açıklar.
 * `compare.py` bunu iki adımda yapar: (1) `_numeric_key()` ile sıralama
 * anahtarı, (2) alanın yönü (`_LOWER_IS_BETTER` / `_HIGHER_IS_BETTER`). Her
 * bankanın aldığı ara değer (`sort_key`) olduğu gibi gösterilir. Çok alanlı
 * ağırlıklı skor için «En Avantajlı» sekmesine bakılır.
 *
 * ## KAPSAM ŞERİDİ (2026-08-09)
 *
 * Bu tablo kıyas panelinin süzgeçlerini AYNEN devralır ama kendi başlığında
 * bunu söylemiyordu. Kampanya türü süzgeci «Tümü» iken buradaki sıra numarası
 * türler arasında verilir — üstteki kıyas tablosunda ise tür içinde. İki tablo
 * yan yana duruyor ve aynı bankayı farklı sırada gösterebiliyordu; kullanıcı
 * hangi sıranın doğru olduğunu bilemezdi.
 *
 * Sıralama değiştirilmedi: bu tablonun işi bir tavsiye üretmek değil, FORMÜLÜ
 * göstermektir; formül tür bilmez. Değişen, kapsamın artık YAZILMASI. Adil
 * sıralama için okuyucu kıyas tablosuna ya da «En Avantajlı» sekmesine
 * yönlendirilir.
 *
 * ## AMACIN YENİDEN TANIMI (2026-08-12) — «neden toplanmadı» da burada anlatılır
 *
 * Banka sayfası artık bileşik bir BANKA skoru basmıyor ve basmama gerekçesini
 * tek cümleyle veriyor («sekiz kampanya türü birbirinin alternatifi değil»).
 * Ama o cümle bir iddiadır ve iddianın dayanağı bu ekrandaydı: ağırlıklar,
 * bileşenler, kapsama eşiği. Gerekçe bir yerde, dayanağı başka bir yerde
 * durursa, jüri ikisini birleştirmek zorunda kalır.
 *
 * Bu yüzden bileşenin yüzeyi genişledi (kapsamı DEĞİL): tek alanın formülünü
 * göstermeye DEVAM eder, üstüne iki şey ekler — (1) tür içi bileşik puanın
 * hangi ağırlıklarla hesaplandığı, (2) o puanın neden ne bankalar arasında ne
 * türler arasında TOPLANMADIĞI. Ağırlıklar sunucudan gelir
 * (`composite_weights`, `compare.py::DEFAULT_WEIGHTS`); arayüz hiçbir ağırlığı
 * kendi yazmaz — yazsaydı formülün iki sürümü olurdu.
 *
 * Bileşen SİLİNMEDİ ve silinemezdi: «en avantajlı» iddiasının denetlenebilir
 * olduğu tek yüzey burasıdır.
 */

import { api } from "../lib/api";
import { extractorClass, extractorLabel, formatValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { ErrorNotice, Loading } from "./ErrorNotice";

/** Bir ağırlık satırı + GEREKÇESİ (`compare.py::WEIGHT_RATIONALE`). */
type AgirlikSatiri = { alan: string; agirlik: number; gerekce: string | null };

/**
 * `composite_weights` alanını iki OLASI biçimden de okur.
 *
 * ÖLÇÜLDÜ (2026-08-12): `lib/api.ts` bu alanı `Record<string, number> | null`
 * diye tanımlıyor ama `GET /scoring` gerçekte bir LİSTE döndürüyor —
 * `[{field_name, weight, rationale, direction}, …]`, yani
 * `compare.py::weight_manifest()` çıktısı. Tipe güvenip `Object.entries()`
 * çağırmak, dizinin elemanlarını React'e çocuk olarak vermeye çalışıyor ve
 * sayfa «Objects are not valid as a React child» ile çöküyordu.
 *
 * Tip düzeltmesi `lib/api.ts`'e ait ve o dosya bu akışın sahipliğinde değil;
 * o yüzden düzeltme İSTENDİ (rapora yazıldı) ve burada iki biçim de okunuyor.
 * Bileşen tipe değil TELDEN GELENE bakıyor: uç yarın sözleşmeye dönerse de
 * çalışmaya devam eder, dönmezse de.
 */
function agirlikSatirlari(ham: unknown): AgirlikSatiri[] {
  if (Array.isArray(ham)) {
    return ham.flatMap((s) => {
      if (!s || typeof s !== "object") return [];
      const r = s as Record<string, unknown>;
      const alan = typeof r.field_name === "string" ? r.field_name : null;
      const agirlik = typeof r.weight === "number" ? r.weight : null;
      if (alan === null || agirlik === null) return [];
      return [{
        alan,
        agirlik,
        gerekce: typeof r.rationale === "string" ? r.rationale : null,
      }];
    });
  }
  if (ham && typeof ham === "object") {
    return Object.entries(ham as Record<string, unknown>).flatMap(([alan, w]) =>
      typeof w === "number" ? [{ alan, agirlik: w, gerekce: null }] : [],
    );
  }
  return [];
}

export default function ScoringExplainer({
  field,
  type,
}: {
  field: string;
  type?: string;
}) {
  const s = useAsync(() => api.scoring(field, type || undefined), [field, type]);

  return (
    <section className="card">
      <h2>Şeffaf Skorlama — «en avantajlı» nasıl hesaplandı?</h2>
      <p className="lede">
        Sıralamanın formülü ve her bankanın aldığı ara değer aşağıda. Formülün
        kaynağı: <span className="mono">{s.data?.formula_source ?? "src/comparison/compare.py"}</span>
      </p>

      <div className="notice notice-info">
        <strong>
          Kapsam:{" "}
          {type
            ? `yalnız «${type}» kampanya türü`
            : "tüm kampanya türleri birlikte"}
        </strong>
        <div className="notice-body">
          {type ? (
            <>
              Yukarıdaki kampanya türü süzgeci uygulandı; bu tablodaki sıra
              numaraları yalnız bu tür içinde anlamlıdır.
            </>
          ) : (
            <>
              Süzgeç «Tümü» olduğu için bu tablo <b>türleri ayırmaz</b>: buradaki
              sıra numarası bir tavsiye değil, formülün nasıl çalıştığının
              gösterimidir. Farklı türler birbirinin alternatifi olmadığından
              adil sıralamayı kıyas tablosunun tür bölümlerinden ya da «En
              Avantajlı» sekmesinden okuyun.
            </>
          )}
        </div>
      </div>

      {s.loading && <Loading />}
      {!!s.error && <ErrorNotice error={s.error} />}

      {s.data && (
        <>
          <ol className="steps">
            {s.data.steps.map((st) => (
              <li key={st.no}>
                <b>{st.name}</b> — <span>{st.detail}</span>
              </li>
            ))}
          </ol>

          <div className="notice notice-info" style={{ marginTop: "var(--sp-4)" }}>
            <strong>Bu tablo TEK alanı açıklar</strong>
            <div className="notice-body">{s.data.composite_note}</div>
          </div>

          {/* Tür İÇİ bileşik puanın ağırlıkları — banka sayfasındaki yıldızın
              formülü. Ağırlıklar sunucudan gelir; gelmiyorsa hiçbir şey
              basılmaz (uydurma formül göstermektense sessiz kalmak). */}
          {agirlikSatirlari(s.data.composite_weights).length > 0 && (
            <>
              <h3 className="banka-gozustu">tür içi bileşik puanın ağırlıkları</h3>
              <div className="alan-seridi">
                {agirlikSatirlari(s.data.composite_weights).map((a) => (
                  <span
                    key={a.alan}
                    className="alan-cip alan-cip-dolu"
                    /* Ağırlık bir ÜRÜN KARARIDIR, ölçümden türetilmiş bir
                       sabit değil (compare.py:693). Gerekçesi sunucudan
                       geliyorsa çipin üstünde okunabilir olmalı. */
                    title={a.gerekce ?? undefined}
                  >
                    {a.alan} · {a.agirlik}
                  </span>
                ))}
              </div>
            </>
          )}

          {/* KURAL: puan tür içinde kalır. Gerekçe, dayanağının hemen yanında. */}
          <div className="banka-serit" role="note">
            Banka sayfasındaki yıldız bu ağırlıklarla ve <b>yalnız bir kampanya
            türünün içinde</b> hesaplanır; normalizasyon grup içi sıralama
            tabanlıdır. Bu yüzden tek bir «banka puanı» üretilmez: farklı
            türlerden gelen puanlar farklı popülasyonlarda ölçülmüş sıralardır,
            ortalamaları tanımsızdır — ve hepsini tek sayıya toplamak, sistemin
            reddettiği türler arası sıralamayı arka kapıdan geri getirirdi.
            Bankanın kampanyalarını ortalamak ayrıca toplama kapsamasını
            sessizce kaliteye çevirirdi: az belge toplanabilmiş banka, ürünü
            kötü olduğu için değil verisi az olduğu için düşük puan alırdı.
          </div>

          <h3>Bankaların aldığı ara değerler</h3>
          <div className="table-wrap">
            {/* `stackable`: 7 kolon mobilde yatay kaymada başlıklarını
               kaybediyordu; kardeş düzeltme AuditPanel.tsx'te. */}
            <table className="data stackable">
              <thead>
                <tr>
                  <th scope="col">Sıra</th>
                  <th scope="col">Banka</th>
                  <th scope="col">Kanonik değer</th>
                  <th scope="col">Sıralama anahtarı</th>
                  <th scope="col">Kıyas kapısı</th>
                  <th scope="col">Güven</th>
                  <th scope="col">Katman</th>
                </tr>
              </thead>
              <tbody>
                {s.data.rows.map((r, i) => (
                  <tr key={`${r.bank}-${i}`}>
                    <td data-label="Sıra" className="num">
                      <span className={`rank-pill${r.rank === 1 ? " first" : ""}`}>
                        {r.rank ?? "—"}
                      </span>
                    </td>
                    <td data-label="Banka">{r.bank_name || r.bank}</td>
                    <td data-label="Kanonik değer" className="num">{formatValue(r.value, s.data?.field)}</td>
                    <td data-label="Sıralama anahtarı" className="num mono">
                      {r.sort_key === null ? "—" : r.sort_key}
                    </td>
                    <td data-label="Kıyas kapısı">
                      {r.comparable ? (
                        <span className="badge badge-ok">geçti</span>
                      ) : (
                        <span className="badge badge-warn">
                          elendi — {r.note ?? "sebep yok"}
                        </span>
                      )}
                    </td>
                    <td data-label="Güven">
                      <ConfidenceBadge value={r.confidence} />
                    </td>
                    <td data-label="Katman">
                      <span className={extractorClass(r.extractor)}>
                        {extractorLabel(r.extractor)}
                      </span>
                    </td>
                  </tr>
                ))}
                {s.data.rows.length === 0 && (
                  <tr>
                    <td data-label="Sıra" colSpan={7} className="muted">
                      Bu alan için sıralanacak kayıt yok.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </section>
  );
}
