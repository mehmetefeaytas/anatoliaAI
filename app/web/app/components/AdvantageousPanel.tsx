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
 */

import { useState } from "react";
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
            Object.entries(veri.data.types).map(([ad, grup]) => (
              <TurBolumu
                key={ad}
                ad={ad}
                grup={grup}
                minGrup={veri.data!.min_group_size}
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
  grup,
  minGrup,
  onInspect,
}: {
  ad: string;
  grup: AdvantageousGroup;
  minGrup: number;
  onInspect?: (campaignId: number) => void;
}) {
  return (
    <div style={{ marginTop: "var(--sp-5)" }}>
      <h3>
        Kampanya türü: {ad} · {grup.count} kampanya
      </h3>

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

function SkorSatiri({
  sira,
  skor,
  onInspect,
}: {
  sira: number;
  skor: CompositeScore;
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
                  <dt className="mono">{c.field_name}</dt>
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
