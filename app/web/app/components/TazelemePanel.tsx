"use client";

/**
 * Veri Tazeleme — banka başına "Şimdi tazele" operatör eylemi.
 *
 * İlgili: src/api/main.py (`/refresh*`), src/scraping/tazeleme.py,
 *         ../lib/tazeleme.ts (saf yardımcılar), ../lib/juryMode.tsx
 *
 * ## Neden yalnız jüri modunda
 *
 * Sistem internetsiz çalışmak zorunda ve demo önceden hazırlanmış veri
 * tabanından okur; canlı toplamaya bağlanmış bir sunum donma riskidir. Bu
 * panel o kuralı bozmaz, tam tersine görünür kılar: ağa çıkan tek yol burasıdır
 * ve ayrı, açık bir onaya bağlıdır. Ürün ekranında yeri yoktur, denetim
 * ekranında vardır.
 *
 * ## Neden önce ön izleme, sonra başlatma
 *
 * Düğmeye basmak dakikalarca sürecek bir ağ işi başlatır. Bu yüzden ilk
 * tıklama hiçbir şey başlatmaz: kaç istek atılacağını, kabaca ne kadar
 * süreceğini, internet gerektiğini ve nereye yazılacağını gösterir. İkinci,
 * ayrı bir onay işi başlatır.
 *
 * ## Neden yoklama (polling)
 *
 * İş arka planda koşar; arayüz 1,5 saniyede bir durum sorar. Böylece ekran
 * donmaz, sekme değiştirilebilir ve "durdur" her an basılabilir.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api, toDisplayError } from "../lib/api";
import type { Bank, RefreshJob, RefreshPreview } from "../lib/api";
import {
  belgeDurumEtiketi,
  belgeDurumSinifi,
  durumBildirimSinifi,
  durumEtiketi,
  hataGerekcesi,
  ilerlemeOrani,
  sonucOzeti,
  sureMetni,
  tahminiIstek,
  tahminiSure,
} from "../lib/tazeleme";
import { ErrorNotice, Loading } from "./ErrorNotice";
import { useAsync } from "../lib/useAsync";

/** Durum yoklama aralığı. Daha sık sormak sunucuya değer katmıyor. */
const YOKLAMA_MS = 1500;

export default function TazelemePanel() {
  const banks = useAsync(() => api.banks(), []);
  const [onizleme, setOnizleme] = useState<RefreshPreview | null>(null);
  const [is, setIs] = useState<RefreshJob | null>(null);
  const [hata, setHata] = useState<unknown>(null);
  const [mesgul, setMesgul] = useState(false);

  // Yoklama zamanlayıcısı bileşen kaldırılınca mutlaka durmalı; aksi halde
  // sekme değiştikçe arka planda birikir.
  const zamanlayici = useRef<ReturnType<typeof setTimeout> | null>(null);
  const canli = useRef(true);

  useEffect(() => {
    canli.current = true;
    return () => {
      canli.current = false;
      if (zamanlayici.current) clearTimeout(zamanlayici.current);
    };
  }, []);

  const yokla = useCallback(async (jobId: string) => {
    try {
      const durum = await api.refreshStatus(jobId);
      if (!canli.current) return;
      setIs(durum);
      if (!durum.bitti) {
        zamanlayici.current = setTimeout(() => void yokla(jobId), YOKLAMA_MS);
      }
    } catch (e) {
      if (!canli.current) return;
      // Durum sorgusu düşerse iş yine de koşuyor olabilir; sonucu kaybetmemek
      // için yoklamayı bırakmıyoruz ama hatayı da gizlemiyoruz.
      setHata(e);
      zamanlayici.current = setTimeout(() => void yokla(jobId), YOKLAMA_MS * 2);
    }
  }, []);

  async function onizlemeAc(bank: Bank) {
    setHata(null);
    setOnizleme(null);
    setMesgul(true);
    try {
      setOnizleme(await api.refreshPreview(bank.slug));
    } catch (e) {
      setHata(e);
    } finally {
      setMesgul(false);
    }
  }

  async function baslat(slug: string) {
    setHata(null);
    setMesgul(true);
    try {
      const kayit = await api.refreshStart(slug);
      setOnizleme(null);
      setIs(kayit);
      void yokla(kayit.is_id);
    } catch (e) {
      setHata(e);
    } finally {
      setMesgul(false);
    }
  }

  async function durdur(jobId: string) {
    setHata(null);
    try {
      setIs(await api.refreshCancel(jobId));
    } catch (e) {
      setHata(e);
    }
  }

  const calisiyor = !!is && !is.bitti;
  const oran = is ? ilerlemeOrani(is) : null;
  const ozet = is ? sonucOzeti(is) : null;

  return (
    <div className="stack">
      <section className="card">
        <h2>Veri Tazeleme</h2>
        <p className="lede">
          Bankanın resmî sitesinden kampanya sayfalarını yeniden toplayan
          operatör eylemi. Sistemin ağa çıkabildiği tek yol burasıdır.
        </p>

        <div className="notice notice-warn">
          <strong>Bu eylem internet bağlantısı gerektirir</strong>
          <div className="notice-body">
            Karşılaştırma, çelişki tespiti ve sohbet ekranları internete{" "}
            <b>hiçbir koşulda çıkmaz</b>; önceden hazırlanmış veri tabanından
            okumaya devam ederler. Tazeleme yalnızca ham belge arşivine yazar,
            veri tabanına dokunmaz — bu yüzden yarıda kalan bir tazeleme
            gösterilen hiçbir sonucu bozamaz. Ağ yoksa ya da site istekleri
            reddederse işlem açık bir hata ile biter.
          </div>
        </div>

        <p className="small muted">
          Toplama, sitenin tarama kurallarına (robots.txt) uyar, alan başına
          birkaç saniye bekler, kendini tanıtan bir istemci adı kullanır ve her
          belgeyi kaynak adresi + zaman damgasıyla saklar.
        </p>
      </section>

      {!!hata && (
        <section className="card">
          <ErrorNotice error={hata} />
          <p className="small muted">{toDisplayError(hata).hint}</p>
        </section>
      )}

      {is && (
        <section className="card">
          <h2>
            {is.bank_name} — {durumEtiketi(is.durum)}
          </h2>

          <div className={durumBildirimSinifi(is.durum)}>
            <strong>{is.asama}</strong>
            {is.mesaj ? <div className="notice-body">{is.mesaj}</div> : null}
          </div>

          {calisiyor && (
            <div className="tazele-ilerleme" aria-live="polite">
              <div
                className="tazele-ilerleme-cubuk"
                role="progressbar"
                aria-valuemin={0}
                aria-valuemax={100}
                aria-valuenow={oran === null ? undefined : Math.round(oran * 100)}
                aria-label="Tazeleme ilerlemesi"
              >
                <span
                  className={`tazele-ilerleme-dolgu${oran === null ? " belirsiz" : ""}`}
                  style={oran === null ? undefined : { width: `${oran * 100}%` }}
                />
              </div>
              <div className="row">
                <span className="small muted">
                  {is.toplam
                    ? `${is.tamamlanan} / ${is.toplam} adres`
                    : "Adresler aranıyor…"}
                </span>
                <span className="grow" />
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => void durdur(is.is_id)}
                  disabled={is.iptal_istendi}
                >
                  {is.iptal_istendi ? "Durduruluyor…" : "Durdur"}
                </button>
              </div>
              <p className="small faint">
                Durdurmak güvenlidir: belgeler yalnızca toplama bittiğinde diske
                yazılır, yarım belge kalmaz.
              </p>
            </div>
          )}

          <div className="stats" style={{ marginTop: "var(--sp-4)" }}>
            <div className="stat">
              <div className="k">Çekilen belge</div>
              <div className="v">{is.cekilen}</div>
            </div>
            <div className="stat">
              <div className="k">Yeni</div>
              <div className="v">{is.yeni}</div>
            </div>
            <div className="stat">
              <div className="k">Değişen</div>
              <div className="v">{is.degisen}</div>
            </div>
            <div className="stat">
              <div className="k">Aynı kalan</div>
              <div className="v">{is.ayni}</div>
            </div>
            <div className="stat">
              <div className="k">Hata</div>
              <div
                className="v"
                style={{ color: is.hata ? "var(--bad)" : "var(--ok)" }}
              >
                {is.hata}
              </div>
            </div>
          </div>

          {ozet && <p className="small muted">{ozet}</p>}

          {is.robots_ozet && (
            <p className="small faint">
              Tarama kuralları: <span className="mono">{is.robots_ozet}</span>
            </p>
          )}

          {is.belgeler.length > 0 && (
            <>
              <h3>Belgeler ({is.belgeler.length})</h3>
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">Durum</th>
                      <th scope="col">Başlık</th>
                      <th scope="col">Adres</th>
                      <th scope="col">Karakter</th>
                    </tr>
                  </thead>
                  <tbody>
                    {is.belgeler.map((b) => (
                      <tr key={b.source_url}>
                        <td>
                          <span className={belgeDurumSinifi(b.durum)}>
                            {belgeDurumEtiketi(b.durum)}
                          </span>
                        </td>
                        <td>{b.title ?? "—"}</td>
                        <td className="mono small">
                          <a href={b.source_url} target="_blank" rel="noreferrer">
                            {b.source_url}
                          </a>
                        </td>
                        <td className="num">
                          {b.karakter}
                          {b.onceki_karakter !== null &&
                          b.onceki_karakter !== b.karakter ? (
                            <span className="small faint">
                              {" "}
                              (önce {b.onceki_karakter})
                            </span>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}

          {is.hatalar.length > 0 && (
            <>
              <h3>Alınamayan adresler ({is.hata_tamami})</h3>
              <div className="table-wrap">
                <table className="data">
                  <thead>
                    <tr>
                      <th scope="col">Adres</th>
                      <th scope="col">Gerekçe</th>
                    </tr>
                  </thead>
                  <tbody>
                    {is.hatalar.map((h, i) => (
                      <tr key={`${h.url}-${i}`}>
                        <td className="mono small">{h.url}</td>
                        <td>{hataGerekcesi(h.reason)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {is.hata_tamami > is.hatalar.length && (
                <p className="small faint">
                  Listede ilk {is.hatalar.length} kayıt gösteriliyor.
                </p>
              )}
            </>
          )}
        </section>
      )}

      {onizleme && (
        <section className="card">
          <h2>Başlatmadan önce: {onizleme.bank_name}</h2>
          <div className="notice notice-info">
            <strong>Bu düğmeye basınca ne olacak</strong>
            <div className="notice-body">
              {onizleme.bank_name} sitesine yaklaşık{" "}
              <b>{tahminiIstek(onizleme)}</b> gönderilecek ve işlem kabaca{" "}
              <b>{tahminiSure(onizleme)}</b> sürecek. Her istek arasında{" "}
              {sureMetni(onizleme.gecikme_sn)} beklenir; sitenin tarama
              kurallarına uyulur. En çok {onizleme.azami_belge} belge alınır.
            </div>
          </div>

          <div className="stats">
            <div className="stat">
              <div className="k">Başlangıç sayfası</div>
              <div className="v">{onizleme.giris_sayfasi}</div>
            </div>
            <div className="stat">
              <div className="k">Azami belge</div>
              <div className="v">{onizleme.azami_belge}</div>
            </div>
            <div className="stat">
              <div className="k">İstek arası bekleme</div>
              <div className="v">{sureMetni(onizleme.gecikme_sn)}</div>
            </div>
            <div className="stat">
              <div className="k">Arşivdeki belge</div>
              <div className="v">{onizleme.arsivdeki_belge}</div>
            </div>
          </div>

          <ul className="tazele-kosullar small">
            <li>İnternet bağlantısı gerekir.</li>
            <li>
              Yazım yeri yalnızca ham belge arşividir:{" "}
              <span className="mono">{onizleme.hedef_dizin}</span>
            </li>
            <li>Veri tabanı değişmez; kıyas ve sohbet sonuçları aynı kalır.</li>
            <li>
              İstemci adı: <span className="mono">{onizleme.user_agent}</span>
            </li>
          </ul>

          <div className="row">
            <button
              type="button"
              className="btn"
              disabled={mesgul || calisiyor}
              onClick={() => void baslat(onizleme.bank)}
            >
              Onayla ve tazelemeyi başlat
            </button>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => setOnizleme(null)}
            >
              Vazgeç
            </button>
          </div>
        </section>
      )}

      <section className="card">
        <h2>Bankalar</h2>
        {banks.loading ? (
          <Loading label="Banka listesi yükleniyor…" />
        ) : banks.error ? (
          <ErrorNotice error={banks.error} />
        ) : (
          <ul className="tazele-liste">
            {(banks.data ?? []).map((b) => (
              <li key={b.slug} className="tazele-satir">
                <div className="grow">
                  <div>
                    <b>{b.name}</b>
                  </div>
                  <div className="small faint mono">{b.website_url ?? "—"}</div>
                </div>
                <button
                  type="button"
                  className="btn btn-ghost"
                  disabled={mesgul || calisiyor}
                  onClick={() => void onizlemeAc(b)}
                >
                  Şimdi tazele
                </button>
              </li>
            ))}
          </ul>
        )}
        {calisiyor && (
          <p className="small muted">
            Bir tazeleme sürüyor. Aynı anda tek banka tazelenir; yenisini
            başlatmak için mevcut işin bitmesini bekleyin ya da durdurun.
          </p>
        )}
      </section>
    </div>
  );
}
