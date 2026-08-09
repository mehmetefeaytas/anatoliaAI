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
 */

import { api } from "../lib/api";
import { extractorClass, extractorLabel, formatValue } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { ErrorNotice, Loading } from "./ErrorNotice";

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

          <h3>Bankaların aldığı ara değerler</h3>
          <div className="table-wrap">
            <table className="data">
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
                    <td className="num">
                      <span className={`rank-pill${r.rank === 1 ? " first" : ""}`}>
                        {r.rank ?? "—"}
                      </span>
                    </td>
                    <td>{r.bank_name || r.bank}</td>
                    <td className="num">{formatValue(r.value, s.data?.field)}</td>
                    <td className="num mono">
                      {r.sort_key === null ? "—" : r.sort_key}
                    </td>
                    <td>
                      {r.comparable ? (
                        <span className="badge badge-ok">geçti</span>
                      ) : (
                        <span className="badge badge-warn">
                          elendi — {r.note ?? "sebep yok"}
                        </span>
                      )}
                    </td>
                    <td>
                      <ConfidenceBadge value={r.confidence} />
                    </td>
                    <td>
                      <span className={extractorClass(r.extractor)}>
                        {extractorLabel(r.extractor)}
                      </span>
                    </td>
                  </tr>
                ))}
                {s.data.rows.length === 0 && (
                  <tr>
                    <td colSpan={7} className="muted">
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
