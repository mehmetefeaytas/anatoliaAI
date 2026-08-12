"use client";

/**
 * Banka İçi Delta — "bende ne eksik, rakipte ne var?"
 *
 * İlgili: src/api/main.py `GET /bank-delta`, src/comparison/compare.py
 *         `delta_between`, CLAUDE.md §17 (adil kıyas garantisi)
 *
 * Diğer paneller müşterinin sorusunu ("hangi banka daha ucuz?") yanıtlar. Bu
 * panel BANKANIN sorusunu yanıtlar: *«bu ürün bizde yok; Türkiye Finans'ta var
 * ve %10 daha avantajlı»*. Aynı çıkarım verisi, tersinden okunmuş hâli.
 *
 * ## Bu turda ne değişti (2026-08-09)
 *
 * Panel «geliştirilmeli» diye bildirildi. Beş somut kusur bulundu:
 *
 * 1. **Kampanya türü karışıyordu.** Delta 8 ayrı tür-filtresiz `/compare`
 *    çağrısının üstüne kuruluyordu; «Vade — rakip 84 ay önde» cümlesi bir
 *    ihtiyaç finansmanı ile bir konut finansmanı arasında üretilmiş
 *    olabiliyordu. Artık hesap sunucuda ve HER ZAMAN kampanya türü içinde.
 * 2. **Kampanya türü tabloda hiç görünmüyordu** — kullanıcı neyin neyle
 *    kıyaslandığını göremiyordu bile. Artık tür başlıklı bölümler var.
 * 3. **Kanıt çöpe gidiyordu.** API `confidence`, `extractor` ve
 *    `contradiction_count` taşıyordu; panel hiçbirini göstermiyordu. «%10 daha
 *    kötüsünüz» iddiasını, değerin hangi katmandan geldiği ve belgede çelişki
 *    olup olmadığı bilinmeden sunmak denetlenemez bir iddiadır.
 * 4. **«Eksik ürün» ile «eksik veri» karışıyordu.** İkisi de kırmızı «eksik
 *    ürün» etiketine düşüyordu; oysa biri bankanın o ürünü sunmadığını,
 *    diğeri çıkarımın alanı bulamadığını söyler. Ayrım artık sunucuda.
 * 5. **Rakip dayatılıyordu** ve banka listesi `/campaigns`'ten türetiliyordu,
 *    yani hiç kampanyası toplanmamış banka listede görünmüyordu — oysa
 *    «bende hiç ürün yok» tam da bu panelin cevaplaması gereken soru.
 *
 * Ayrıca dosya 505 satırdı ve yarısı kopyalanmış JSX ile üç paralel sabit
 * sözlüğüydü (`DELTA_UNITS` / `KIND_LABEL` / `KIND_CLASS`, aynı enum üç kez).
 * Tek `KINDS` kaydına indi; ölü `taksit_sayisi` birimi kalktı (alan
 * `unranked`, panele hiç girmiyordu).
 *
 * ## TEK TERİM (2026-08-09)
 *
 * Bu panel kavrama «ürün ailesi» diyordu, kıyas paneli ise aynı kavrama
 * «kampanya türü». İkisi de `campaign_type` alanıdır — §12'deki 8 sınıf.
 * Kullanıcı iki ayrı süzgeç sandığını bildirdi. Arayüzün tamamında tek ad
 * kullanılıyor: **kampanya türü**. Tanımı `FairnessNotice` içinde bir kez
 * yazılır ve bu panel de o şeridi basar.
 *
 * HESAPLANMAYAN DURUM korundu: taraflardan biri `comparable = false` ise
 * (aralık, zaman-koşullu oran, farklı para birimi) delta **boş bırakılır**.
 * Yaklaşık bir fark üretmek, tam da §17'nin yasakladığı uydurma sıralamadır.
 */

import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { DeltaField, DeltaKind, DeltaSide } from "../lib/api";
import { extractorClass, extractorLabel, formatValue, trNum } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import FairnessNotice from "./FairnessNotice";

type Props = {
  campaignTypes: string[];
  /** Belgeyi Jüri Audit Paneli'nde açar (page.tsx `inspect` deseni). */
  onInspect: (campaignId: number) => void;
};

/**
 * Delta durumları — TEK kayıt. Eskiden aynı enum üç ayrı `Record`'a
 * dağılmıştı ve biri güncellenip diğeri unutulabilirdi.
 */
const KINDS: Record<DeltaKind, { label: string; cls: string; tone: string }> = {
  eksik_urun: { label: "ürün bulunamadı", cls: "badge badge-bad", tone: "headline-bad" },
  eksik_veri: { label: "veri çıkarılamadı", cls: "badge badge-warn", tone: "headline-warn" },
  daha_iyi: { label: "daha iyi", cls: "badge badge-ok", tone: "" },
  daha_kotu: { label: "daha kötü", cls: "badge badge-warn", tone: "headline-warn" },
  esit: { label: "eşit", cls: "badge", tone: "" },
  kiyaslanamaz: { label: "kıyaslanamaz", cls: "badge badge-warn", tone: "" },
  rakip_yok: { label: "rakip kaydı yok", cls: "badge", tone: "" },
};

/**
 * Farkın BİRİMİ değerin biriminden farklı olabilir: iki oranın farkı yüzde
 * değil YÜZDE PUANIDIR. `%1,89` ile `%2,49` arasındaki fark «%0,60» değil
 * «0,60 puan»dır; ikisini karıştırmak jüri önünde ölçü hatasıdır.
 */
const DELTA_UNITS: Record<string, string> = {
  kar_payi_orani: "puan",
  indirim_orani: "puan",
  vade_ay: "ay",
  finansman_tutari: "TL",
  odul_miktari: "TL",
  tahsis_ucreti: "TL",
  masraf_durumu: "TL",
  alisveris_puani: "TL",
};

function formatDelta(diff: number, field: string): string {
  const unit = DELTA_UNITS[field];
  const n = trNum(Math.abs(diff));
  return unit ? `${n} ${unit}` : n;
}

export default function BankDeltaPanel({ campaignTypes, onInspect }: Props) {
  // Banka listesi kataloğundan gelir, kampanyalardan DEĞİL: hiç kampanyası
  // toplanmamış banka da seçilebilmeli.
  const banks = useAsync(() => api.banks(), []);
  const [bank, setBank] = useState("");
  const [type, setType] = useState("");
  const [rival, setRival] = useState("");

  const liste = banks.data ?? [];
  useEffect(() => {
    if (liste.length === 0) return;
    if (!bank || !liste.some((b) => b.slug === bank)) setBank(liste[0].slug);
  }, [liste, bank]);

  // Rakip seçimi seçilen bankanın kendisi olamaz.
  useEffect(() => {
    if (rival && rival === bank) setRival("");
  }, [bank, rival]);

  const delta = useAsync(
    () =>
      bank
        ? api.bankDelta(bank, type || undefined, rival || undefined)
        : Promise.resolve(null),
    [bank, type, rival],
  );

  const bankName = liste.find((b) => b.slug === bank)?.name ?? bank;

  if (!banks.loading && liste.length === 0) {
    return (
      <section className="card">
        <h2>Banka İçi Delta</h2>
        {banks.error ? (
          <ErrorNotice error={banks.error} />
        ) : (
          <EmptyNotice title="Kıyaslanacak banka yok">
            <span className="mono">/banks</span> ucundan hiçbir banka dönmedi;
            delta hesaplanamaz.
          </EmptyNotice>
        )}
      </section>
    );
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>Banka İçi Delta — bende ne eksik, rakipte ne var?</h2>
        <p className="lede">
          Bir banka seçin: her <b>kampanya türünde</b>, her alanda o bankanın en
          iyi kaydı ile rakip kayıt yan yana konur. Fark yalnız aynı kampanya
          türü içinde hesaplanır.
        </p>

        <div className="row">
          <div className="row-tight">
            <label className="small muted" htmlFor="delta-bank">
              Banka
            </label>
            <select
              id="delta-bank"
              className="select"
              style={{ width: "auto" }}
              value={bank}
              onChange={(e) => setBank(e.target.value)}
            >
              {liste.map((b) => (
                <option key={b.slug} value={b.slug}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
          <div className="row-tight">
            <label className="small muted" htmlFor="delta-rival">
              Rakip
            </label>
            <select
              id="delta-rival"
              className="select"
              style={{ width: "auto" }}
              value={rival}
              onChange={(e) => setRival(e.target.value)}
            >
              <option value="">En iyi rakip (otomatik)</option>
              {liste
                .filter((b) => b.slug !== bank)
                .map((b) => (
                  <option key={b.slug} value={b.slug}>
                    {b.name}
                  </option>
                ))}
            </select>
          </div>
          <div className="row-tight">
            <label className="small muted" htmlFor="delta-type">
              Kampanya türü süzgeci
            </label>
            <select
              id="delta-type"
              className="select"
              style={{ width: "auto" }}
              value={type}
              onChange={(e) => setType(e.target.value)}
            >
              <option value="">Tüm türler (ayrı ayrı)</option>
              {campaignTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Şerit varyantı (2026-08-11): tam metin bu panelde de basılıyordu ve
            kullanıcı aynı ~250 kelimeyi her sekmede yeniden görüyordu. Kural
            silinmedi, katlandı — özet satırı her hâlde ekranda. */}
        <FairnessNotice varyant="serit" />

        {(banks.loading || delta.loading) && (
          <Loading label="Kampanya türleri karşılaştırılıyor…" />
        )}
        {!!delta.error && <ErrorNotice error={delta.error} />}

        {delta.data && delta.data.families.length === 0 && (
          <EmptyNotice title={`${bankName} için kıyaslanacak kampanya türü yok`}>
            Seçilen filtrede ne bu bankaya ait belge var, ne de kıyaslanacak
            rakip kaydı. Veri eksikliği ile ürün eksikliği aynı şey değildir;
            bu ayrımı aşağıdaki tablolar satır satır verir.
          </EmptyNotice>
        )}
      </section>

      {delta.data?.families.map((tur) => (
        <TurBolumu
          key={tur.campaign_type ?? "__belirsiz__"}
          tur={tur.campaign_type}
          ownCampaigns={tur.own_campaigns}
          fields={tur.fields}
          bankName={bankName}
          onInspect={onInspect}
        />
      ))}
    </div>
  );
}

function TurBolumu({
  tur,
  ownCampaigns,
  fields,
  bankName,
  onInspect,
}: {
  tur: string | null;
  ownCampaigns: number;
  fields: DeltaField[];
  bankName: string;
  onInspect: (campaignId: number) => void;
}) {
  // Sayaçlar tek döngüde; eskiden beş birebir aynı JSX bloğu vardı.
  const sayim = fields.reduce<Partial<Record<DeltaKind, number>>>((acc, f) => {
    acc[f.kind] = (acc[f.kind] ?? 0) + 1;
    return acc;
  }, {});

  const mansetler = fields.filter(
    (f) => f.kind === "eksik_urun" || f.kind === "eksik_veri" || f.kind === "daha_kotu",
  );

  return (
    <section className="card">
      <h2>
        {tur ? `Kampanya türü: ${tur}` : "Türü belirlenemeyen belgeler"}
      </h2>
      <p className="lede">
        {bankName} bu türde <b>{ownCampaigns}</b> belge taşıyor.
        {ownCampaigns === 0 && (
          <>
            {" "}
            Bu türde hiç belgesi yok — aşağıdaki satırlar «ürün bulunamadı»
            der, «veri çıkarılamadı» demez. İkisi aynı şey değildir.
          </>
        )}
      </p>

      <div className="stats">
        {(["eksik_urun", "eksik_veri", "daha_kotu", "daha_iyi", "esit"] as const).map(
          (k) => (
            <div className="stat" key={k}>
              <div className="k">{KINDS[k].label}</div>
              <div className="v">{sayim[k] ?? 0}</div>
            </div>
          ),
        )}
      </div>

      {mansetler.length > 0 && (
        <div className="headlines">
          {mansetler.map((f) => (
            <p key={f.field} className={`headline ${KINDS[f.kind].tone}`}>
              <b>{f.label}</b>
              <span>
                <Manset f={f} bankName={bankName} />
              </span>
            </p>
          ))}
        </div>
      )}

      <h3>Alan alan delta</h3>
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
            Fark yalnız iki tarafın da kıyaslanabilir olduğu satırlarda
            hesaplanır; aksi hâlde hücre boş bırakılır (uydurma delta yok).
            Oran alanlarında fark yüzde değil <b>yüzde puanıdır</b>.
          </caption>
          <thead>
            <tr>
              <th scope="col">Alan</th>
              <th scope="col">{bankName}</th>
              <th scope="col">Rakip</th>
              <th scope="col">Fark</th>
              <th scope="col">Konum</th>
              <th scope="col">Durum</th>
            </tr>
          </thead>
          <tbody>
            {fields.map((f) => (
              <tr key={f.field}>
                <td data-label="Alan">
                  {f.label}
                  <div className="small faint">{f.direction_label}</div>
                </td>
                <td data-label="Bu banka" className="num">
                  <Taraf side={f.mine} field={f.field} onInspect={onInspect} />
                </td>
                <td data-label="Rakip" className="num">
                  <Taraf
                    side={f.rival}
                    field={f.field}
                    bankaAdiGoster
                    onInspect={onInspect}
                  />
                </td>
                <td data-label="Fark" className="num">
                  {f.abs_diff === null ? (
                    <span className="faint">—</span>
                  ) : (
                    <>
                      <strong>{formatDelta(f.abs_diff, f.field)}</strong>
                      {f.rel_pct !== null && (
                        <div className="small faint">
                          göreli %{trNum(f.rel_pct)}
                        </div>
                      )}
                    </>
                  )}
                </td>
                <td data-label="Konum" className="num">
                  {f.position === null ? (
                    <span className="faint">—</span>
                  ) : (
                    <>
                      <span className={`rank-pill${f.position === 1 ? " first" : ""}`}>
                        {f.position}
                      </span>
                      <div className="small faint">{f.bank_count} banka içinde</div>
                    </>
                  )}
                </td>
                <td data-label="Durum">
                  <span className={KINDS[f.kind].cls}>{KINDS[f.kind].label}</span>
                  {/* Gerekçe motordan gelir; arayüz yeniden yazmaz ki ikisi
                      aynı şeyi söylesin. */}
                  {f.kind === "kiyaslanamaz" && (
                    <div className="small faint">
                      {f.mine?.note ?? f.rival?.note ?? "aynı birime indirgenemiyor"}
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Manset({ f, bankName }: { f: DeltaField; bankName: string }) {
  const rakip = f.rival?.bank_name || f.rival?.bank;
  if (f.kind === "eksik_urun") {
    return (
      <>
        {bankName} bu türde bu alanda ürün taşımıyor; <b>{rakip}</b> tarafında
        var: <span className="mono">{formatValue(f.rival?.value, f.field)}</span>
      </>
    );
  }
  if (f.kind === "eksik_veri") {
    return (
      <>
        {bankName}&apos;in bu türde belgesi var ama bu alan <b>çıkarılamadı</b>.
        Bu bir ürün eksikliği değildir; rakipte değer:{" "}
        <span className="mono">{formatValue(f.rival?.value, f.field)}</span>
      </>
    );
  }
  return (
    <>
      <b>{rakip}</b> daha avantajlı:{" "}
      {f.abs_diff !== null ? formatDelta(f.abs_diff, f.field) : "—"} fark
      {f.rel_pct !== null ? ` (göreli %${trNum(f.rel_pct)})` : ""}
    </>
  );
}

/**
 * Deltanın bir tarafı — değer, ham ifade ve KANIT.
 *
 * Güven skoru, üreten katman ve çelişki sayısı burada gösterilir. Eskiden
 * hiçbiri gösterilmiyordu: «%10 daha kötüsünüz» iddiası, arkasındaki değerin
 * LLM'den mi kuraldan mı geldiği ve o belgede üç çelişki olup olmadığı
 * bilinmeden sunuluyordu.
 */
function Taraf({
  side,
  field,
  bankaAdiGoster,
  onInspect,
}: {
  side: DeltaSide | null;
  field: string;
  bankaAdiGoster?: boolean;
  onInspect: (campaignId: number) => void;
}) {
  if (!side) return <span className="faint">—</span>;

  return (
    <>
      <strong>{formatValue(side.value, field)}</strong>
      {bankaAdiGoster && (
        <div className="small muted">{side.bank_name || side.bank}</div>
      )}
      {side.raw_value && (
        <div className="small faint mono" title="Kaynak metindeki ham ifade">
          «{side.raw_value.trim()}»
        </div>
      )}
      <div className="row-tight" style={{ flexWrap: "wrap", marginTop: "var(--sp-1)" }}>
        <span className={extractorClass(side.extractor)}>
          {extractorLabel(side.extractor)}
        </span>
        <ConfidenceBadge value={side.confidence} source={side.confidence_source} />
        {side.contradiction_count > 0 && (
          <span className="badge badge-bad">
            {side.contradiction_count} çelişki
          </span>
        )}
      </div>
      <div className="row-tight" style={{ flexWrap: "wrap" }}>
        <button
          type="button"
          className="btn-link"
          onClick={() => onInspect(side.campaign_id)}
        >
          belgeye git (#{side.campaign_id})
        </button>
        {side.source_url && (
          <a
            className="btn-link"
            href={side.source_url}
            target="_blank"
            rel="noreferrer noopener"
            title={side.source_url}
          >
            banka sayfası ↗
          </a>
        )}
      </div>
    </>
  );
}
