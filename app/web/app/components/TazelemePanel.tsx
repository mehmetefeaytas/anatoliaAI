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
 *
 * ## v2 «kanıt defteri» görsel dili — bu ekranda ne değişti
 *
 * Tasarım dosyasında bu yüzeyin birebir karşılığı yok; dilinin ÜÇ deseni
 * taşındı:
 *
 *  1. **Provenans şeridi** (`.tz-etik`, sol kenarda 3px). Eskiden burada
 *     `.notice-warn` vardı — on ekranda geçen genel bir uyarı kutusu, yani
 *     "bir şey ters gitti" diyen bir biçim. Bu blok ters giden bir şey
 *     bildirmiyor, bir SINIRI bildiriyor: ağa çıkan tek yüzey burasıdır.
 *  2. **Tek sakin bant** (`.durum-bant`, durum.css'ten ödünç). Eskiden iş
 *     durumu bir bildirim kutusu, ilerleme başka bir kutu, sayaçlar üçüncü
 *     bir küme, yoklama uyarısı dördüncü bir kutuydu — dört kutu, tek olay.
 *     Artık nokta + başlık cümlesi + mono durum listesi aynı bandın içinde ve
 *     renk TEK sinyal değil.
 *  3. **Yazılı oran.** İlerleme çubuğunun yanında mono `tabular-nums` bir
 *     sayı durur ve TOPLAM BİLİNMESE BİLE bir cümle basar. Bir çubuğun
 *     uzunluğu okunabilir bir sayı değildir.
 *
 * Ayrıca etik kısıt (CLAUDE.md §14) artık ön izlemenin içinde saklı değil:
 * `.tz-taahhut` listesi robots.txt uyumunu, domain başına bekleme süresini ve
 * provenans kaydını ekranın üstünde, her hâlde yazar. Etik kısıt bir ayar
 * değil, okunan bir taahhüttür.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "../lib/api";
import type { Bank, RefreshDurum, RefreshJob, RefreshPreview } from "../lib/api";
import {
  belgeDurumEtiketi,
  belgeDurumSinifi,
  durumEtiketi,
  hataGerekcesi,
  hataTekrarlanabilir,
  ilerlemeOrani,
  isCikmazi,
  sonucOzeti,
  sureMetni,
  tahminiIstek,
  tahminiSure,
  yoklamaBirakmaNotu,
} from "../lib/tazeleme";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import { useAsync } from "../lib/useAsync";
import "../styles/zorvaka.css";

/** Durum yoklama aralığı. Daha sık sormak sunucuya değer katmıyor. */
const YOKLAMA_MS = 1500;

/**
 * Durum sorgusu üst üste bu kadar düşerse yoklama BIRAKILIR.
 *
 * Sınırsız yoklama gerçek bir kusurdu: 404 almış bir iş kimliği (sunucu
 * yeniden başlamış, kayıt düşmüş) hiçbir denemede geri gelmez, oysa arayüz
 * 3 saniyede bir aynı hatayı tazeleyip kapatılamayan bir bildirim üretiyordu.
 * Beş deneme, geçici bir sunucu sarsıntısını atlatmaya yeter; kalıcı bir
 * yokluğu ise ısrar etmeden görünür kılar.
 */
const YOKLAMA_AZAMI_HATA = 5;

/** Ekrandaki hata + yalnız GERÇEKTEN geçiciyse bir tekrar deneme yolu. */
type EkranHatasi = {
  hata: unknown;
  /** `null` = bu hata için tekrar dene düğmesi BASILMAZ. */
  tekrar: (() => void) | null;
  /** Hatanın yanına eklenen ek açıklama (ör. yoklama neden bırakıldı). */
  not: string | null;
  /**
   * Hatayı kimin ürettiği. Başarılı bir yoklama YALNIZ kendi bildirimini
   * siler: aksi halde düşen bir «durdur» isteğinin hatası, 1,5 saniye sonra
   * gelen ilk sağlıklı durum cevabıyla ekrandan silinirdi.
   */
  kaynak: "yoklama" | "eylem";
};

/** Hatanın HTTP durumu — ApiError değilse 0 (bilinmiyor = tekrarlanabilir). */
function hataDurumu(e: unknown): number {
  return e instanceof ApiError ? e.status : 0;
}

/**
 * İş durumunun BANT rengi sınıfı.
 *
 * `lib/tazeleme.ts`'teki `durumBildirimSinifi` bildirim KUTUSU sınıfı döndürür
 * (`notice notice-ok`); bant ayrı bir yerleşimdir ve yalnız durum rengini
 * ödünç alır, kutu çerçevesini almaz. İki eşleme bilerek ayrı: kutu dili bu
 * ekranda artık kullanılmıyor ama fonksiyon başka bir yüzeyde işe yarayabilir
 * ve silme kararı bu akışa ait değil.
 */
function bantSinifi(durum: RefreshDurum): string {
  if (durum === "tamam") return "tz-bant-ok";
  if (durum === "hata") return "tz-bant-hata";
  if (durum === "iptal") return "tz-bant-durdu";
  return "tz-bant-calisiyor";
}

/**
 * Bandın sağındaki MONO durum listesi — rengin üçüncü yedeği.
 *
 * Tasarımın durum bandı (`api · depo ✓ · yerel model ✓`) ile aynı sözcük:
 * olayın ölçülebilir kısmı, renkten bağımsız okunabilir olmalı. Sayılar her
 * hâlde basılır; sıfır bir boşluk değil, ölçülmüş bir sonuçtur.
 *
 * ## `hata` sayacı listede YOK
 *
 * Üç sayaç işin ÜRÜNÜNÜ ölçüyor: kaç adres çekildi, kaçı yeni, kaçı değişti.
 * `hata` bunlarla aynı cinsten değil — bir çıktı değil, bir olay. Listeye
 * girdiğinde iki sorun çıkıyordu: (1) `hata 0` her koşuda basılıyor ve olmayan
 * bir sorunu her seferinde gündeme getiriyordu; (2) `hata 3` ise tek bir sayı
 * olarak, hangi bankada ne olduğunu söylemeden bir alarm kuruyordu — oysa şerit
 * bir özet satırı, bir olay kaydı değil.
 *
 * Hata bilgisi KAYBOLMUYOR, yerine gidiyor: gerçek bir hata varsa bandın kendi
 * durumu `hata`ya düşüyor (`bantSinifi`), başlık cümlesi bunu yazıyor ve iş
 * günlüğü hangi adreste ne olduğunu satır satır veriyor. Bir sayı yerine bir
 * cümle ve bir kayıt — CLAUDE.md §19'un «kaynağa dayandır» kuralının durum
 * şeridindeki karşılığı.
 */
function monoDurumListesi(is: RefreshJob): string {
  return [
    `çekilen ${is.cekilen}`,
    `yeni ${is.yeni}`,
    `değişen ${is.degisen}`,
  ].join(" · ");
}

/**
 * İlerlemenin YAZILI hâli. Çubuk uzunluğu ve rengi tek sinyal olamaz.
 *
 * Toplam henüz bilinmiyorken (keşif evresi) bir yüzde İDDİA EDİLMEZ: o an
 * bilinen tek şey kaç adresin işlendiğidir ve cümle bunu söyler. Uydurma bir
 * `%0` ile gerçek bir `%0` aynı metne düşmez.
 */
function oranMetni(is: RefreshJob, oran: number | null): string {
  if (oran === null) {
    return `${is.tamamlanan} adres işlendi · toplam henüz bilinmiyor`;
  }
  return `${is.tamamlanan} / ${is.toplam} adres · %${Math.round(oran * 100)}`;
}

export default function TazelemePanel() {
  const banks = useAsync(() => api.banks(), []);
  const [onizleme, setOnizleme] = useState<RefreshPreview | null>(null);
  const [is, setIs] = useState<RefreshJob | null>(null);
  const [hata, setHata] = useState<EkranHatasi | null>(null);
  const [mesgul, setMesgul] = useState(false);
  // Yoklama bırakıldı mı. Bitmemiş bir iş kaydı ekranda asılı kalırsa
  // `calisiyor` sonsuza kadar doğru kalır ve TÜM banka düğmeleri kilitlenir;
  // bu bayrak o kilide açık bir çıkış yolu takar.
  const [yoklamaBirakildi, setYoklamaBirakildi] = useState(false);

  // Yoklama zamanlayıcısı bileşen kaldırılınca mutlaka durmalı; aksi halde
  // sekme değiştikçe arka planda birikir.
  const zamanlayici = useRef<ReturnType<typeof setTimeout> | null>(null);
  const canli = useRef(true);
  // ARDIŞIK düşüş sayacı: araya giren tek bir başarılı sorgu bunu sıfırlar,
  // çünkü o an sunucu cevap veriyor demektir.
  const yoklamaHatasi = useRef(0);

  useEffect(() => {
    canli.current = true;
    return () => {
      canli.current = false;
      if (zamanlayici.current) clearTimeout(zamanlayici.current);
    };
  }, []);

  /**
   * Hatayı ekrana koyar. `tekrar` YALNIZCA durum kodu gerçekten geçici bir
   * arızaya işaret ediyorsa düğmeye dönüşür; aksi halde sessizce düşürülür.
   */
  const hataBildir = useCallback((e: unknown, tekrar?: () => void) => {
    setHata({
      hata: e,
      tekrar: tekrar && hataTekrarlanabilir(hataDurumu(e)) ? tekrar : null,
      not: null,
      kaynak: "eylem",
    });
  }, []);

  const yokla = useCallback(async (jobId: string) => {
    try {
      const durum = await api.refreshStatus(jobId);
      if (!canli.current) return;
      yoklamaHatasi.current = 0;
      setYoklamaBirakildi(false);
      setHata((onceki) => (onceki?.kaynak === "yoklama" ? null : onceki));
      setIs(durum);
      if (!durum.bitti) {
        zamanlayici.current = setTimeout(() => void yokla(jobId), YOKLAMA_MS);
      }
    } catch (e) {
      if (!canli.current) return;
      // Durum sorgusu düşerse iş yine de koşuyor olabilir; sonucu kaybetmemek
      // için tek düşüşte yoklamayı bırakmıyoruz ama hatayı da gizlemiyoruz.
      yoklamaHatasi.current += 1;
      const deneme = yoklamaHatasi.current;
      const gecici = hataTekrarlanabilir(hataDurumu(e));

      // Kalıcı bir durum kodunda (ör. 404: böyle bir iş kaydı yok) beklemenin
      // anlamı yok — ilk düşüşte bırakılır.
      if (gecici && deneme < YOKLAMA_AZAMI_HATA) {
        setHata({
          hata: e,
          tekrar: null,
          not: `Durum sorgusu düştü; yeniden sorulacak (${deneme}/${YOKLAMA_AZAMI_HATA}).`,
          kaynak: "yoklama",
        });
        zamanlayici.current = setTimeout(() => void yokla(jobId), YOKLAMA_MS * 2);
        return;
      }

      setYoklamaBirakildi(true);
      setHata({
        hata: e,
        tekrar: gecici
          ? () => {
              yoklamaHatasi.current = 0;
              setYoklamaBirakildi(false);
              setHata(null);
              void yokla(jobId);
            }
          : null,
        not: yoklamaBirakmaNotu(deneme, gecici),
        kaynak: "yoklama",
      });
    }
  }, []);

  async function onizlemeAc(bank: Bank) {
    setHata(null);
    setOnizleme(null);
    setMesgul(true);
    try {
      setOnizleme(await api.refreshPreview(bank.slug));
    } catch (e) {
      hataBildir(e, () => void onizlemeAc(bank));
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
      yoklamaHatasi.current = 0;
      setYoklamaBirakildi(false);
      setIs(kayit);
      void yokla(kayit.is_id);
    } catch (e) {
      // 409 = başka bir tazeleme koşuyor. O iş bitince aynı düğme çalışır,
      // dolayısıyla burada «tekrar dene» gerçek bir söz verir.
      hataBildir(e, () => void baslat(slug));
    } finally {
      setMesgul(false);
    }
  }

  async function durdur(jobId: string) {
    setHata(null);
    try {
      setIs(await api.refreshCancel(jobId));
    } catch (e) {
      hataBildir(e, () => void durdur(jobId));
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

        {/* PROVENANS ŞERİDİ: bir arıza değil, bir SINIR bildirir. */}
        <div className="tz-etik">
          <strong className="tz-etik-baslik">
            Bu yüzey ağa çıkar — panelin tek istisnası
          </strong>
          <p className="tz-etik-govde">
            Karşılaştırma, çelişki tespiti ve sohbet ekranları internete{" "}
            <b>hiçbir koşulda çıkmaz</b>; önceden hazırlanmış veri tabanından
            okumaya devam ederler. Yalnız bu yüzey bankanın resmî sitesine
            istek gönderir ve yalnız jüri modunda erişilebilir. Tazeleme ham
            belge arşivine yazar, veri tabanına dokunmaz — bu yüzden yarıda
            kalan bir tazeleme gösterilen hiçbir sonucu bozamaz. Ağ yoksa ya da
            site istekleri reddederse işlem açık bir hata ile biter.
          </p>
        </div>

        <h3>toplama taahhüdü</h3>
        {/* Etik kısıt bir AYAR DEĞİL: değiştirilebilir bir kutu değil, okunan
            bir taahhüt (CLAUDE.md §14). Değerler sistemin kendi kısıtlarıdır;
            bankaya özgü kesin bekleme süresi ön izlemede tek tek yazılır. */}
        <ul className="tz-taahhut">
          <li>
            <span className="tz-taahhut-ad">robots.txt</span>
            <span className="tz-taahhut-deger">
              Sitenin tarama kurallarına uyulur. Kurallar bir adresi kapsam dışı
              bırakıyorsa o adres alınmaz ve gerekçesi listelenir.
            </span>
          </li>
          <li>
            <span className="tz-taahhut-ad">bekleme</span>
            <span className="tz-taahhut-deger">
              Domain başına <span className="mono">2–5 saniye</span>: her istek
              arasında beklenir, eşzamanlı istek gönderilmez. Bankaya özgü kesin
              değer başlatmadan önceki ön izlemede yazılıdır.
            </span>
          </li>
          <li>
            <span className="tz-taahhut-ad">istemci adı</span>
            <span className="tz-taahhut-deger">
              İstekler kendini tanıtan bir istemci adıyla gider; tarayıcı
              taklidi yapılmaz.
            </span>
          </li>
          <li>
            <span className="tz-taahhut-ad">provenans</span>
            <span className="tz-taahhut-deger">
              Her belge kaynak adresi ve zaman damgasıyla saklanır. Kaynağı
              olmayan hiçbir metin arşive girmez.
            </span>
          </li>
        </ul>
      </section>

      {hata && (
        <section className="card">
          {/* `hint` ikinci kez BASILMAZ: `ErrorNotice` onu zaten yazıyordu ve
              aynı cümle üst üste iki kez görünüyordu. */}
          <ErrorNotice error={hata.hata} onRetry={hata.tekrar ?? undefined} />
          {hata.not && <p className="small muted">{hata.not}</p>}
        </section>
      )}

      {is && (
        <section className="card">
          <h2>{is.bank_name}</h2>

          {/* TEK SAKİN BANT. Dört ayrı kutu (durum + ilerleme + sayaçlar +
              yoklama uyarısı) yerine tek bant: olay tek. Renk tek sinyal
              değil — nokta, başlık cümlesi ve mono durum listesi aynı şeyi üç
              ayrı yolla söyler. */}
          <div
            className={`durum-bant ${bantSinifi(is.durum)}`}
            aria-live="polite"
          >
            <span aria-hidden="true" className="durum-bant-nokta" />
            <div className="durum-bant-govde">
              <div className="durum-bant-baslik">{durumEtiketi(is.durum)}</div>
              <div className="durum-bant-aciklama">
                {is.asama}
                {is.mesaj ? ` — ${is.mesaj}` : ""}
              </div>
            </div>
            <span className="durum-bant-liste">{monoDurumListesi(is)}</span>
          </div>

          {calisiyor && yoklamaBirakildi && (
            // İlerleme çubuğu BASILMAZ: artık durum sorulmadığı için çubuk
            // hareket etmez ve donmuş bir çubuk "iş takıldı" der — oysa iş
            // sunucuda pekâlâ sürüyor olabilir. Söylenen şey, bilinen şey:
            // izleme durdu, kaydı kapatmak listeyi serbest bırakır.
            <div className="notice notice-warn">
              <strong>İlerleme izleme durduruldu</strong>
              <div className="notice-body">
                Tazeleme sunucuda sürüyor olabilir; bu ekran artık durum
                sormuyor. Kaydı kapatmak banka listesini yeniden kullanılabilir
                yapar ve sunucudaki işe dokunmaz.
              </div>
              <div className="row" style={{ marginTop: "var(--sp-3)" }}>
                <button
                  type="button"
                  className="btn btn-ghost"
                  onClick={() => {
                    setIs(null);
                    setYoklamaBirakildi(false);
                    setHata(null);
                  }}
                >
                  Kaydı kapat
                </button>
              </div>
            </div>
          )}

          {calisiyor && !yoklamaBirakildi && (
            <div className="tazele-ilerleme" aria-live="polite">
              {/* Çubuk + YANINDA yazılı oran. Çubuğun uzunluğu okunabilir bir
                  sayı değildir; sayı her hâlde metin olarak da basılır. */}
              <div className="tz-oran">
                <div
                  className="tazele-ilerleme-cubuk"
                  role="progressbar"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={
                    oran === null ? undefined : Math.round(oran * 100)
                  }
                  aria-label="Tazeleme ilerlemesi"
                >
                  <span
                    className={`tazele-ilerleme-dolgu${oran === null ? " belirsiz" : ""}`}
                    style={oran === null ? undefined : { width: `${oran * 100}%` }}
                  />
                </div>
                <span className="tz-oran-sayi">{oranMetni(is, oran)}</span>
              </div>
              <div className="row">
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

          {/* Beş ayrı sayaç kutusu KALDIRILDI. Aynı beş sayı bandın mono
              listesinde ve — iş bittiğinde — tek cümlelik özette zaten var;
              üç yerde basmak bir olayı üç olay gibi gösteriyordu. */}
          {ozet && <p className="small muted">{ozet}</p>}

          {is.robots_ozet && (
            <p className="small faint">
              Tarama kuralları: <span className="mono">{is.robots_ozet}</span>
            </p>
          )}

          {is.notlar.length > 0 && (
            <>
              <h3>iş günlüğü</h3>
              {/* Makine çıktısı: mono, en küçük ölçü, sınırlı yükseklik +
                  kendi kaydırması. `tabIndex` klavyeyle kaydırma için ZORUNLU:
                  fareyle kaydırılıp klavyeyle kaydırılamayan bir kutu
                  erişilemez bir kutudur. */}
              <div
                className="tz-gunluk"
                role="log"
                tabIndex={0}
                aria-label="Tazeleme iş günlüğü"
              >
                {is.notlar.map((not, i) => (
                  <div key={`${i}-${not}`} className="tz-gunluk-satir">
                    {not}
                  </div>
                ))}
              </div>
            </>
          )}

          {is.belgeler.length > 0 && (
            <>
              <h3>belgeler · {is.belgeler.length}</h3>
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
              <h3>alınamayan adresler · {is.hata_tamami}</h3>
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
          {/* Nötr not: burada henüz bir şey OLMADI, bir şey olacağı söylendi.
              Uyarı rengi bu bloğa ait değil — karar hâlâ operatörde. */}
          <div className="uc-not">
            <strong className="uc-not-baslik">
              Bu düğmeye basınca ne olacak
            </strong>
            <p className="uc-not-govde">
              {onizleme.bank_name} sitesine yaklaşık{" "}
              <b>{tahminiIstek(onizleme)}</b> gönderilecek ve işlem kabaca{" "}
              <b>{tahminiSure(onizleme)}</b> sürecek. En çok{" "}
              {onizleme.azami_belge} belge alınır; şu an arşivde{" "}
              {onizleme.arsivdeki_belge} belge duruyor ve{" "}
              {onizleme.giris_sayfasi} liste sayfasından başlanır.
            </p>
          </div>

          <h3>bu banka için etik kısıt</h3>
          {/* Bekleme süresi bu ekranın en önemli sayısıdır ve ön izlemede
              BANKAYA ÖZGÜ kesin değeriyle basılır: yukarıdaki taahhüt listesi
              sistemin aralığını söylüyor, burası uygulanacak değeri. */}
          <ul className="tz-taahhut">
            <li>
              <span className="tz-taahhut-ad">bekleme</span>
              <span className="tz-taahhut-deger">
                Her istek arasında{" "}
                <span className="mono">{sureMetni(onizleme.gecikme_sn)}</span>{" "}
                beklenir.
              </span>
            </li>
            <li>
              <span className="tz-taahhut-ad">robots.txt</span>
              <span className="tz-taahhut-deger">
                {onizleme.robots_uyumu
                  ? "Sitenin tarama kuralları okunur ve uygulanır."
                  : "Bu banka için tarama kuralı okunamadı; kapsam dışı adres varsayılamaz."}
              </span>
            </li>
            <li>
              <span className="tz-taahhut-ad">istemci adı</span>
              <span className="tz-taahhut-deger">
                <span className="mono">{onizleme.user_agent}</span>
              </span>
            </li>
            <li>
              <span className="tz-taahhut-ad">yazım yeri</span>
              <span className="tz-taahhut-deger">
                Yalnız ham belge arşivi:{" "}
                <span className="mono">{onizleme.hedef_dizin}</span>. Veri
                tabanı değişmez; kıyas ve sohbet sonuçları aynı kalır.
              </span>
            </li>
            <li>
              <span className="tz-taahhut-ad">ağ</span>
              <span className="tz-taahhut-deger">
                İnternet bağlantısı gerekir; bağlantı yoksa işlem açık bir hata
                ile biter.
              </span>
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
          /* İSKELET, animasyonlu sayaç DEĞİL: yapı hemen basılır, yalnız
             değerler bekler. Dönen bir sayaçtan okunan sayı, hiç okunmamış bir
             sayıdır. İskeleti `durum.css` çiziyor ve `prefers-reduced-motion`
             uyumu orada tanımlı.
             `satir={11}` bir DEĞER İDDİASI DEĞİL, bir yerleşim beklentisi:
             hedef banka kümesi 11 satır (CLAUDE.md §13) ve iskelet o kadar
             satır çizince liste geldiğinde kart yüksekliği zıplamaz. Ekran
             okuyucudan gizli — okunacak şey etikettir. */
          <Loading label="Banka listesi yükleniyor…" satir={11} />
        ) : banks.error ? (
          <ErrorNotice error={banks.error} />
        ) : (banks.data ?? []).length === 0 ? (
          /* BOŞ ≠ HATA: istek çalıştı, liste gerçekten boş. Sahte bir banka
             satırı basmak, boş bir liste göstermekten kötüdür. */
          <EmptyNotice title="Tanımlı banka yok" kesir="0 banka">
            Banka listesi <span className="mono">config/banks.yaml</span>{" "}
            dosyasından okunur. Dosyaya bir satır eklenip sunucu yeniden
            başlatıldığında bu liste kendiliğinden dolar.
          </EmptyNotice>
        ) : (
          <ul className="tazele-liste">
            {(banks.data ?? []).map((b) => {
              // Çıkmaz YALNIZ kendi bankasını bağlar: bir bankanın kapalı
              // tarama kuralı, diğerlerinin düğmesini kilitlemez.
              const cikmaz = is && is.bank === b.slug ? isCikmazi(is) : null;
              const cikmazId = `tazele-cikmaz-${b.slug}`;
              return (
                <li key={b.slug} className="tazele-satir">
                  <div className="grow">
                    <div>
                      <b>{b.name}</b>
                    </div>
                    <div className="small faint mono">{b.website_url ?? "—"}</div>
                    {cikmaz && (
                      <div className="small muted" id={cikmazId}>
                        <b>{cikmaz.neOldu}</b> {cikmaz.neYapilabilir}
                      </div>
                    )}
                  </div>
                  {cikmaz ? (
                    // Düğme kapalı ama GÖRÜNÜR: kaybolsaydı operatör eylemin
                    // hiç var olmadığını sanırdı. Yanındaki çıkış yolu bilinçli
                    // olarak bir "tekrar dene" değil — gerekçenin giderildiğini
                    // operatörün açıkça beyan etmesini ister.
                    <div className="row-tight">
                      <button
                        type="button"
                        className="btn btn-ghost"
                        disabled
                        aria-describedby={cikmazId}
                      >
                        Şimdi tazele
                      </button>
                      <button
                        type="button"
                        className="btn btn-link"
                        onClick={() => setIs(null)}
                      >
                        Gerekçe giderildi, düğmeyi aç
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      className="btn btn-ghost"
                      disabled={mesgul || calisiyor}
                      onClick={() => void onizlemeAc(b)}
                    >
                      Şimdi tazele
                    </button>
                  )}
                </li>
              );
            })}
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
