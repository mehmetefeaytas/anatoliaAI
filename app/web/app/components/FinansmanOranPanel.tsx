"use client";

/**
 * «Yayımlanan finansman oranları» — bankaların KENDİ yayınından, korpustan değil.
 *
 * İlgili: ../lib/api.ts (`finansmanOranlari`), ../../src/domain/yayimlanan_oran.py
 *         KatilmaPanel.tsx (kardeş yüzey, TERS yönlü büyüklük)
 *
 * ## Niçin bu yüzey var
 *
 * Kampanya korpusunda `kar_payi_orani` belgelerin yalnız **%6,1'inde** geçiyor
 * ve bu bir çıkarım kusuru değil — bilgi o metinlerde YOK. Ölçüldü
 * (2026-08-25): EVREN `llm-large` 60 aday belgede 0 kabul, yerel qwen2.5:7b
 * 30 belgede 0. Metnin kendisi üçüncü kanıt: yakalanmayan yüzdelerin çoğu
 * *gecikme kâr payı formülü*, kampanyanın oranı değil.
 *
 * Bankalar oranı hesaplama araçlarında yayımlıyor. Bu panel o kaynağı
 * gösteriyor ve kaynağın FARKLI olduğunu gizlemiyor.
 *
 * ## Yön SUNUCUDAN okunuyor
 *
 * Katılma hesabında yüksek oran iyiydi, finansmanda düşük oran iyi. İki yüzey
 * aynı kelimeyi kullandığı için yön arayüzde SABİT YAZILMIYOR; `yon_etiketi`
 * sunucudan geliyor ve ekrana o basılıyor. Sabit yazsaydık, sunucu yönü
 * değiştirdiği gün ekran sessizce yanlış olurdu.
 */

import { useState } from "react";
import type { FinansmanOrani } from "../lib/api";
import { api } from "../lib/api";
import { trNum } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";

const BANKA_ADI: Record<string, string> = {
  "kuveyt-turk": "Kuveyt Türk",
  albaraka: "Albaraka Türk",
  "turkiye-finans": "Türkiye Finans",
  "ziraat-katilim": "Ziraat Katılım",
  "vakif-katilim": "Vakıf Katılım",
  "turkiye-emlak-katilim": "Türkiye Emlak Katılım",
  "tom-katilim": "T.O.M. Katılım",
  "hayat-finans": "Hayat Finans",
  "dunya-katilim": "Dünya Katılım",
  "adil-katilim": "Adil Katılım",
};

function bankaAdi(slug: string | null): string {
  if (!slug) return "—";
  return BANKA_ADI[slug] ?? slug;
}

/** Ücret sözlüğünü okunur tek satıra çevirir; boşsa `null` (satır basılmaz). */
function ucretMetni(fees: Record<string, number> | null): string | null {
  if (!fees) return null;
  const kalemler = Object.entries(fees).filter(([, v]) => v !== null && v > 0);
  if (kalemler.length === 0) return null;
  return kalemler
    .map(([ad, v]) => `${ad}: ${trNum(v)} TL`)
    .join(" · ");
}

export default function FinansmanOranPanel() {
  const [tur, setTur] = useState<string>("");
  const [vade, setVade] = useState<number | undefined>(undefined);

  const veri = useAsync(
    () => api.finansmanOranlari({
      urun_ailesi: tur || undefined,
      term_months: vade,
    }),
    [tur, vade],
  );

  if (veri.loading) return <Loading label="Yayımlanan oranlar yükleniyor…" />;
  if (veri.error) return <ErrorNotice error={veri.error} />;
  const d = veri.data;
  if (!d) return null;

  const satirlar: FinansmanOrani[] = d.rows;
  const enIyi = satirlar[0];

  return (
    <section className="card stack" aria-labelledby="finansman-oran-baslik">
      <h2 id="finansman-oran-baslik">Yayımlanan Finansman Oranları</h2>

      {/* Kaynak farkı BAŞLIKTAN HEMEN SONRA: okuyucu tabloyu görmeden önce
          bunun kampanya korpusundan gelmediğini bilmeli. */}
      <p className="muted" style={{ marginTop: 0 }}>{d.kaynak_notu}</p>

      <p className="badge badge-warn" style={{ display: "inline-block" }}>
        {d.yon_etiketi}
      </p>

      <div className="row-tight" role="group" aria-label="Süzgeçler">
        <label htmlFor="fo-tur">
          <span className="mono muted">kampanya türü</span>{" "}
          <select
            id="fo-tur"
            value={tur}
            onChange={(e) => setTur(e.target.value)}
          >
            <option value="">tümü</option>
            {d.urun_aileleri.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </label>
        <label htmlFor="fo-vade">
          <span className="mono muted">vade</span>{" "}
          <select
            id="fo-vade"
            value={vade ?? ""}
            onChange={(e) =>
              setVade(e.target.value === "" ? undefined : Number(e.target.value))
            }
          >
            <option value="">tümü</option>
            {d.vadeler.map((v) => (
              <option key={v} value={v}>{v} ay</option>
            ))}
          </select>
        </label>
      </div>

      {d.veri_yok ? (
        // «Veri yok» bir HATA DEĞİL: hasat henüz koşmamış olabilir. Boş tabloyu
        // "oran sıfır" gibi göstermek, olmayan bir ölçümü ölçülmüş saymaktı.
        <EmptyNotice title="Bu süzgeçle yayımlanmış oran yok">
          Oran hasadı henüz koşmamış
          olabilir: <span className="mono">
            python -m src.scraping.harvest_rates
          </span>
        </EmptyNotice>
      ) : (
        <>
          <p>
            En düşük oran: <b>{bankaAdi(enIyi.bank_slug)}</b> — %
            {trNum(enIyi.monthly_rate ?? 0)} aylık
            {enIyi.term_months ? ` (${enIyi.term_months} ay)` : ""}.
          </p>

          <div style={{ overflowX: "auto" }}>
            <table>
              <caption className="muted">
                Banka başına EN DÜŞÜK aylık oran. Aynı bankanın onlarca ürünü
                listeyi doldurup bankalar arası kıyası görünmez kılardı; hangi
                üründen geldiği satırda yazılı.
              </caption>
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Banka</th>
                  <th scope="col">Ürün</th>
                  <th scope="col">Aylık oran</th>
                  <th scope="col">Yıllık maliyet</th>
                  <th scope="col">Vade</th>
                  <th scope="col">Ücretler</th>
                  <th scope="col">Kaynak</th>
                </tr>
              </thead>
              <tbody>
                {satirlar.map((r, i) => (
                  <tr key={`${r.bank_slug}-${r.product_code}-${r.term_months}`}>
                    <td className="mono">{i + 1}</td>
                    <td>{bankaAdi(r.bank_slug)}</td>
                    <td>
                      {r.product_name ?? "—"}
                      <br />
                      <span className="mono muted">{r.urun_ailesi}</span>
                    </td>
                    <td className="mono">
                      <b>%{trNum(r.monthly_rate ?? 0)}</b>
                    </td>
                    {/* Yıllık maliyet UYDURULMAZ: banka yayımlamıyorsa
                        «yayımlanmadı» yazar, hesaplanmış bir sayı basmaz. */}
                    <td className="mono">
                      {r.annual_cost_rate === null ? (
                        <span className="muted">yayımlanmadı</span>
                      ) : (
                        `%${trNum(r.annual_cost_rate)}`
                      )}
                    </td>
                    <td className="mono">
                      {r.term_months ? `${r.term_months} ay` : "—"}
                    </td>
                    <td className="mono">
                      {ucretMetni(r.fees) ?? (
                        <span className="muted">yayımlanmadı</span>
                      )}
                    </td>
                    <td>
                      {r.source_url ? (
                        <a href={r.source_url} target="_blank"
                           rel="noopener noreferrer">banka yayını</a>
                      ) : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <details>
            <summary>Kapsam — hangi bankada kaç kayıt var</summary>
            <p className="muted">
              {d.kapsam.kayit} kayıt · {d.kapsam.banka} banka. Kalan bankalar
              gizlenmiyor: <b>Vakıf Katılım</b> finansman oranını yayımlamıyor
              (yalnız katılma hesabı PDF'i, o da robots ile engelli ve şartname
              §5.1 gereği elle indirildi), <b>Türkiye Finans</b> yalnız katılma
              hesabı tablosu yayımlıyor, <b>Adil Katılım</b> hiç oran
              yayımlamıyor.
            </p>
            <ul>
              {Object.entries(d.kapsam.banka_basina).map(([slug, n]) => (
                <li key={slug}>
                  {bankaAdi(slug)} — <span className="mono">{n}</span> kayıt
                </li>
              ))}
            </ul>
          </details>

          {enIyi.note && (
            <p className="muted">
              <b>Not:</b> {enIyi.note}
            </p>
          )}
        </>
      )}
    </section>
  );
}
