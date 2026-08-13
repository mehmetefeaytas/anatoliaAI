"use client";

/**
 * İşlem günlüğü (audit log) paneli — «sistemde ne oldu, ne zaman oldu».
 *
 * İlgili: ../lib/gunluk.ts, ../lib/api.ts (`api.gunlukSayfa`),
 *         ../../../src/api/gunluk.py, ../../../src/api/main.py (`GET /log`)
 *
 * ## Neden var
 *
 * Bir canlı tazeleme `data/raw/albaraka/live/` altına 40 dosya yazdı ve "bunu
 * kim tetikledi, ne zaman" sorusu SAATLERCE cevapsız kaldı; cevabı sonunda
 * sistem değil, kullanıcının hafızası verdi. Sunucu artık her isteği kalıcı
 * bir kayda yazıyor; bu sekme o kaydın okunabilir yüzü.
 *
 * ## Varsayılan: YALNIZ YAZAN işlemler
 *
 * Panel her sekme değişiminde `/compare`, `/stats`, `/advantageous` çağırıyor
 * ve bir iş koşarken `/refresh/status` saniyede bir yoklanıyor. Hepsi eşit
 * ağırlıkta listelenseydi, uğruna bu günlüğün yazıldığı tek satır
 * (`POST /refresh`) yüzlerce okuma satırının arasında kaybolurdu. "Hepsini
 * göster" tek tık uzakta ve süzgeç etkinken bunu SÖYLEYEN bir satır var —
 * gizlenen bir şey olduğunu kullanıcı tahmin etmek zorunda kalmamalı.
 *
 * ## Sayfalama: "daha fazla" değil, SAYFA
 *
 * Belge seçicideki (`BelgeSecici`) "daha fazla" kalıbı listeyi büyütüyor;
 * burada aranan şey genelde EN SON olan, o yüzden liste yeniden eskiye ve
 * sabit sayfa boyunda. Toplam `X-Toplam-Kayit` başlığından geliyor ve
 * ekranda yazıyor: kullanıcının günlüğü tam sandığı tek hata bu sayının
 * eksikliğinden doğar.
 *
 * ## Döndürme kaydı SATIR OLARAK görünür
 *
 * `olay: "gunluk_dondu"` kayıtlarının metodu, yolu ve durum kodu yoktur;
 * tabloya boş hücrelerle basılsalardı bozuk satır sanılırlardı. Onlar tek
 * hücreye yayılmış bir cümle olarak çiziliyor — cevapladıkları soru
 * ("kayıt kayboldu mu") tam da bu ekranda soruluyor.
 */

import { useMemo, useState } from "react";
import { api } from "../lib/api";
import type { GunlukKaydi } from "../lib/api";
import {
  BOS_SUZGEC,
  type GunlukSuzgec,
  YOK,
  dondurmeCumlesi,
  durumSinifi,
  eylemOzeti,
  sorguParametreleri,
  sureEtiketi,
  suzgecEtkin,
  zamanDamgasi,
} from "../lib/gunluk";
import { trNum } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";

/** Sayfa boyu. 50 satır bir ekrana sığmıyor ama iki kaydırmada bitiyor. */
const SAYFA = 50;

/** Süzgeç çipleri için metotlar. Sunucudaki `YAZAN_METOTLAR` + okuma metodu. */
const METOTLAR = ["GET", "POST", "DELETE"] as const;

export default function GunlukPanel() {
  const [suzgec, setSuzgec] = useState<GunlukSuzgec>(BOS_SUZGEC);
  const [offset, setOffset] = useState(0);

  const params = useMemo(
    () => sorguParametreleri(suzgec, { limit: SAYFA, offset }),
    [suzgec, offset],
  );
  const sayfa = useAsync(() => api.gunlukSayfa(params), [params]);

  const kayitlar: GunlukKaydi[] = sayfa.data?.kayitlar ?? [];
  const toplam = sayfa.data?.toplam ?? null;

  /** Süzgeç değişince ilk sayfaya dön — yoksa boş bir sayfa görünürdü. */
  function suzgecDegis(yeni: Partial<GunlukSuzgec>) {
    setOffset(0);
    setSuzgec((s) => ({ ...s, ...yeni }));
  }

  return (
    <div className="stack">
      <section className="card">
        <h2>İşlem günlüğü</h2>
        <p className="lede">
          Sisteme gelen her istek kalıcı bir denetim kaydına yazılır: zaman
          (UTC), metot, yol, durum kodu, süre, isteği atan adres ve varsa ilgili
          iş kimliği. Sistemi DEĞİŞTİREN işlemler (tazeleme, özet üretimi, canlı
          çıkarım, iptaller) ayrıca işaretlenir ve bu liste varsayılan olarak
          yalnız onları gösterir.
        </p>
        <p className="small muted">
          İstek gövdeleri ve arama terimleri BİLEREK kaydedilmez: sohbet
          soruları kişisel veri taşıyabilir ve kalıcı bir kayda yazılan şey geri
          alınamaz. Yazan işlemlerde görünen özet, ucun kendi sonucundan gelir.
        </p>

        <div className="arac-cubugu">
          <button
            type="button"
            className={suzgec.yalnizYazanlar ? "chip" : "chip chip-muted"}
            aria-pressed={suzgec.yalnizYazanlar}
            onClick={() => suzgecDegis({ yalnizYazanlar: true })}
          >
            Yalnız yazan işlemler
          </button>
          <button
            type="button"
            className={!suzgec.yalnizYazanlar ? "chip" : "chip chip-muted"}
            aria-pressed={!suzgec.yalnizYazanlar}
            onClick={() => suzgecDegis({ yalnizYazanlar: false })}
          >
            Tüm istekler
          </button>

          <select
            className="select"
            aria-label="HTTP metodu"
            value={suzgec.metot}
            onChange={(e) => suzgecDegis({ metot: e.target.value })}
          >
            <option value="">Tüm metotlar</option>
            {METOTLAR.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>

          <input
            className="input grow"
            type="search"
            placeholder="Yol ara (örn. refresh)"
            aria-label="Yol araması"
            value={suzgec.yol}
            onChange={(e) => suzgecDegis({ yol: e.target.value })}
          />

          <input
            className="input"
            type="date"
            aria-label="Başlangıç tarihi"
            value={suzgec.baslangic}
            onChange={(e) => suzgecDegis({ baslangic: e.target.value })}
          />
          <input
            className="input"
            type="date"
            aria-label="Bitiş tarihi"
            value={suzgec.bitis}
            onChange={(e) => suzgecDegis({ bitis: e.target.value })}
          />

          {(suzgecEtkin(suzgec) || !suzgec.yalnizYazanlar) && (
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => {
                setOffset(0);
                setSuzgec(BOS_SUZGEC);
              }}
            >
              Süzgeçleri temizle
            </button>
          )}
          <button
            type="button"
            className="btn btn-ghost"
            onClick={() => sayfa.reload()}
          >
            Yenile
          </button>
        </div>

        {/* Süzgecin ne SAKLADIĞI yazılır. Gizlenen satır olduğunu kullanıcının
            tahmin etmesi gerekmemeli — bu ekranın tamamı zaten "ne gizlendi"
            sorusuna cevap vermek için var. */}
        {suzgec.yalnizYazanlar && (
          <p className="small faint">
            Okuma istekleri (<span className="mono">GET</span>) listede yok ama
            kaydediliyor. «Tüm istekler» ile hepsi görünür.
          </p>
        )}
      </section>

      <section className="card">
        <h2>Kayıtlar</h2>

        {sayfa.loading ? (
          <Loading label="İşlem günlüğü yükleniyor…" satir={8} />
        ) : sayfa.error ? (
          <ErrorNotice error={sayfa.error} onRetry={() => sayfa.reload()} />
        ) : kayitlar.length === 0 ? (
          /* BOŞ ≠ HATA: uç çalıştı, süzgeç gerçekten boş küme verdi. */
          <EmptyNotice
            title={
              suzgecEtkin(suzgec)
                ? "Bu süzgeçle eşleşen kayıt yok"
                : "Henüz yazan bir işlem kaydedilmemiş"
            }
            kesir={`0 / ${trNum(toplam ?? 0)} kayıt`}
          >
            {suzgecEtkin(suzgec) ? (
              <>
                Süzgeçleri temizleyip yeniden bakabilirsiniz. Kayıt yokluğu bir
                hata değil; sistem o aralıkta eşleşen bir işlem görmedi.
              </>
            ) : (
              <>
                Günlük sunucu açıldığında yazılmaya başlar. Tazeleme, özet
                üretimi ya da canlı çıkarım gibi bir işlem çalıştırıldığında ilk
                satır burada belirir. «Tüm istekler» seçeneği okuma trafiğini de
                gösterir.
              </>
            )}
          </EmptyNotice>
        ) : (
          <>
            <div className="table-wrap">
              <table className="data stackable">
                <thead>
                  <tr>
                    <th scope="col">Zaman (UTC)</th>
                    <th scope="col">İşlem</th>
                    <th scope="col">Yol</th>
                    <th scope="col">Durum</th>
                    <th scope="col">Süre</th>
                    <th scope="col">İstemci</th>
                    <th scope="col">Ayrıntı</th>
                  </tr>
                </thead>
                <tbody>
                  {kayitlar.map((k, i) => (
                    <GunlukSatiri
                      // Kayıtların kimliği yok (dosya ekleme-only, kimlik
                      // üretmek şemaya ait olmayan bir alan eklerdi); sayfa
                      // içinde sıra + damga tekil bir anahtar veriyor.
                      key={`${k.zaman}-${offset + i}`}
                      kayit={k}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            <div className="row" role="status">
              <span className="small muted grow">
                {toplam === null
                  ? `${trNum(kayitlar.length)} kayıt gösteriliyor.`
                  : `${trNum(toplam)} kayıttan ${trNum(offset + 1)}–${trNum(
                      offset + kayitlar.length,
                    )} arası gösteriliyor.`}
              </span>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={offset === 0}
                onClick={() => setOffset((o) => Math.max(0, o - SAYFA))}
              >
                Daha yeni
              </button>
              <button
                type="button"
                className="btn btn-ghost"
                disabled={
                  toplam !== null
                    ? offset + kayitlar.length >= toplam
                    : kayitlar.length < SAYFA
                }
                onClick={() => setOffset((o) => o + SAYFA)}
              >
                Daha eski
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

/** Tek satır. Döndürme kayıtları isteklerden AYRI çizilir (bkz. dosya başlığı). */
function GunlukSatiri({ kayit }: { kayit: GunlukKaydi }) {
  const dondurme = dondurmeCumlesi(kayit);
  if (dondurme) {
    return (
      <tr>
        <td data-label="Zaman (UTC)" className="mono nowrap">
          {zamanDamgasi(kayit.zaman)}
        </td>
        <td data-label="İşlem" colSpan={6} className="small">
          <span className="badge badge-warn">Günlük döndü</span> {dondurme}
        </td>
      </tr>
    );
  }

  const ozet = eylemOzeti(kayit.eylem);
  return (
    <tr>
      <td data-label="Zaman (UTC)" className="mono nowrap">
        {zamanDamgasi(kayit.zaman)}
      </td>
      <td data-label="İşlem" className="nowrap">
        <span className="mono">{kayit.metot ?? YOK}</span>{" "}
        {kayit.yazan && <span className="badge badge-warn">Yazan</span>}
      </td>
      <td data-label="Yol" className="mono">
        {kayit.yol ?? YOK}
      </td>
      <td data-label="Durum">
        <span className={durumSinifi(kayit.durum)}>{kayit.durum ?? YOK}</span>
      </td>
      <td data-label="Süre" className="num mono">
        {sureEtiketi(kayit.sure_ms)}
      </td>
      <td data-label="İstemci" className="mono small">
        {/* Adres bilinmiyorsa UYDURULMAZ — çizgi basılır. */}
        {kayit.istemci ?? YOK}
      </td>
      <td data-label="Ayrıntı" className="small">
        {ozet ?? <span className="faint">{YOK}</span>}
        {kayit.is_id && (
          <div className="small faint mono">iş: {kayit.is_id}</div>
        )}
      </td>
    </tr>
  );
}
