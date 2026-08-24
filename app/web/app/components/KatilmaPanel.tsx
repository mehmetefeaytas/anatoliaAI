"use client";

/**
 * «Katılma Hesabı Oranları» — TKBB haftalık verisinin panel yüzeyi.
 *
 * İlgili: src/api/routers/katilma.py `GET /katilma-oranlari`
 *         src/chatbot/katilma_orani.py (aynı veriyi sohbette cevaplar)
 *         ../../../decisions/katilma-orani-iki-ayri-buyukluk.md
 *
 * ## Bu panel neden var
 *
 * Chatbot bu veriyi cevaplıyordu, panel görmüyordu: sohbette dokuz bankanın
 * katılma oranı sıralanırken ekranda hiçbir yerde yoktu. Senaryo dashboard ile
 * chatbot'u BİRLİKTE istiyor (CLAUDE.md §5); sohbette görünen bir sıralamanın
 * panelde bulunamaması doğrudan kapsam kaybıdır.
 *
 * ## İKİ BÜYÜKLÜK, İKİ AYRI LİSTE
 *
 * `getiri` gerçekleşen yıllık getiridir (%42,79), `pay` katılımcıya düşen
 * bölüşümdür (%90). İkisi tek listede yarışırsa "en iyi oran" sorusunun cevabı
 * en yüksek getiriyi veren bankayı değil en yüksek bölüşümü ilan edeni gösterir
 * — teknik olarak "en büyük sayı", pratikte yanlış. Bu yüzden büyüklük bir
 * SÜZGEÇ, kolon değil; ve `pay` seçildiğinde ek bir uyarı basılır.
 *
 * ## Veri neden `/compare`'de değil
 *
 * Katılma oranı bir kampanyaya bağlı değildir: banka düzeyinde, haftalık ve
 * kampanyasız. `extracted_fields`e yazmak olmayan bir kampanyaya alan
 * uydurmak olurdu (bkz. routers/katilma.py başlığı).
 *
 * ## Vade her satırda YAZILI
 *
 * Vade süzgeci boşken her banka kendi EN İYİ vadesiyle listelenir. Vade
 * gizlenirse 1 aylık bir oran 12 aylıkla aynı kolonda kıyaslanmış olur; bu
 * yüzden satır kendi vadesini taşır (CLAUDE.md §17 — adil kıyas).
 */

import { useState } from "react";
import { api } from "../lib/api";
import type { KatilmaOranlari } from "../lib/api";
import { trNum } from "../lib/format";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import { useAsync } from "../lib/useAsync";

/** Para birimi kodu → ekran adı. Kod basmak kullanıcıya bir şey söylemiyor. */
const PARA_ADI: Record<string, string> = {
  TRY: "Türk lirası",
  USD: "Dolar",
  EUR: "Euro",
  XAU: "Altın",
};

const VADE_ADI: Record<number, string> = {
  1: "1 ay",
  3: "3 ay",
  6: "6 ay",
  12: "1 yıl",
};

/** Oranı TR biçiminde basar. `null` gösterilmez — satır zaten süzülmüştür. */
function oran(v: number): string {
  return `%${trNum(Number(v.toFixed(2)))}`;
}

export default function KatilmaPanel() {
  const [buyukluk, setBuyukluk] = useState<"getiri" | "pay">("getiri");
  const [currency, setCurrency] = useState<string>("TRY");
  // `null` = "vade süzgeci yok" ve 0'dan farklıdır: her banka kendi en iyi
  // vadesiyle listelenir.
  const [vade, setVade] = useState<number | null>(null);

  const { data, error, loading } = useAsync<KatilmaOranlari>(
    () => api.katilmaOranlari({ buyukluk, currency, term_months: vade }),
    [buyukluk, currency, vade],
  );

  if (loading) return <Loading label="Katılma hesabı oranları yükleniyor…" />;
  if (error) return <ErrorNotice error={error} />;
  if (!data) return null;

  const paralar = data.mevcut.para_birimleri.length
    ? data.mevcut.para_birimleri
    : ["TRY"];
  const vadeler = data.mevcut.vadeler;

  return (
    <section aria-labelledby="katilma-baslik">
      <h2 id="katilma-baslik">Katılma Hesabı Oranları</h2>
      <p className="small muted">
        {data.buyukluk_etiketi}
        {data.period_date ? ` · ${data.period_date} haftası` : ""}
        {vade === null
          ? " · her bankanın en yüksek vadesi"
          : ` · ${VADE_ADI[vade] ?? `${vade} ay`} vade`}
      </p>

      <div className="belge-secici-suzgecler" style={{ marginBottom: "var(--sp-2)" }}>
        <label className="belge-secici-satir">
          <span className="small muted">Büyüklük</span>
          <select
            value={buyukluk}
            onChange={(e) => setBuyukluk(e.target.value as "getiri" | "pay")}
          >
            <option value="getiri">Dağıtılan kâr payı (getiri)</option>
            <option value="pay">Kâr paylaşım oranı (pay)</option>
          </select>
        </label>

        <label className="belge-secici-satir">
          <span className="small muted">Para birimi</span>
          <select value={currency} onChange={(e) => setCurrency(e.target.value)}>
            {paralar.map((p) => (
              <option key={p} value={p}>
                {PARA_ADI[p] ?? p}
              </option>
            ))}
          </select>
        </label>

        <label className="belge-secici-satir">
          <span className="small muted">Vade</span>
          <select
            value={vade === null ? "" : String(vade)}
            onChange={(e) =>
              setVade(e.target.value === "" ? null : Number(e.target.value))
            }
          >
            <option value="">En iyi vade</option>
            {vadeler.map((v) => (
              <option key={v} value={String(v)}>
                {VADE_ADI[v] ?? `${v} ay`}
              </option>
            ))}
          </select>
        </label>
      </div>

      {data.veri_yok ? (
        /* Boş tablo "oran sıfır" gibi okunmamalı: hasat koşmamış olabilir. */
        <EmptyNotice title="Bu seçim için toplanmış oran yok">
          <p>
            Seçilen büyüklük, para birimi ve vade birleşimi için TKBB verisinde
            kayıt bulunamadı. Oran <b>sıfır değil</b>; veri toplanmamış.
            Hasat: <code className="mono">scripts/tkbb_guncel_hasat.py</code>
          </p>
        </EmptyNotice>
      ) : (
        <table className="tur-kirilim-tablo">
          <thead>
            <tr>
              <th scope="col">#</th>
              <th scope="col">Banka</th>
              <th scope="col">Oran</th>
              <th scope="col">Vade</th>
            </tr>
          </thead>
          <tbody>
            {data.rows.map((r, i) => (
              <tr key={r.bank_slug}>
                <td data-label="#" className="mono">
                  {i + 1}
                </td>
                <td data-label="Banka">{r.bank_name}</td>
                <td data-label="Oran" className="mono">
                  {i === 0 ? (
                    <b>{oran(r.annual_rate)}</b>
                  ) : (
                    oran(r.annual_rate)
                  )}
                </td>
                {/* Vade satırın KENDİ vadesi — süzgeç boşken bankalar farklı
                    vadelerde olabilir ve bu görünmek zorunda. */}
                <td data-label="Vade">{VADE_ADI[r.term_months] ?? `${r.term_months} ay`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {buyukluk === "pay" && !data.veri_yok && (
        <p className="small">
          <span className="badge badge-bad">dikkat</span> Bu oran bir{" "}
          <b>bölüşüm</b> oranıdır — kârın yüzde kaçının katılımcıya verildiğini
          gösterir, <b>kazancın kendisi değildir</b>. Gerçekleşen getiri için
          «Dağıtılan kâr payı» seçin.
        </p>
      )}

      <p className="small muted">{data.uyari}</p>

      <p className="small muted">
        Kaynak:{" "}
        <a href={data.source_url} target="_blank" rel="noopener noreferrer">
          {data.source_label}
        </a>
      </p>
    </section>
  );
}
