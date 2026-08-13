"use client";

/**
 * Özet kapsam göstergesi + «LLM ile özet üret» düğmesi.
 *
 * İlgili: ./SummaryNotice.tsx, src/summarize/ozet_isi.py (arka plan işi),
 *         src/summarize/toplu.py (üretim gövdesi), src/api/main.py
 *
 * ## Neden ekranda duruyor
 *
 * Panel AI özeti vaat ediyor ama özetler toplu koşumda üretiliyor; koşum
 * bitene kadar bir kısmı boş. Kullanıcı bunu bilmeden tek tek belgeleri
 * açarsa, boş özetlerin bir ARIZA olduğunu sanır.
 *
 * ## Neden düğme gerekti
 *
 * Veri tazeleme ham arşive yeni ve değişmiş belgeler indiriyor; o belgeler
 * DB'ye girdiğinde özetsiz kalıyordu ve özetlerini üretmenin tek yolu sunucuda
 * komut satırından bir betik koşturmaktı. Kapsam sayacı eksikliği gösteriyor
 * ama gidermenin yolunu göstermiyordu.
 *
 * ## Sayı neden artık sunucudan geliyor
 *
 * Eskiden `/campaigns` yanıtından istemcide hesaplanıyordu (`ozet` alanı
 * doluysa say). O hesap tek bir soruyu cevaplayabiliyordu: "özet var mı".
 * Cevaplayamadığı soru şuydu: **özet neden yok?** Ekrandaki cümle "kalan
 * belgelerde özetlenecek içerik yok" diyordu ve bu, ölçüldüğü gün doğruydu —
 * ama yeni toplanan her belge için YANLIŞ olurdu, çünkü o belge denenmemişti
 * bile. Sunucu artık `campaigns.ozet_sebep` sütununa dayanarak dört kesişmeyen
 * kova döndürüyor ve cümle kovaya göre kuruluyor.
 *
 * ## Yoklama (polling)
 *
 * İş arka planda koşar; ekran 1,5 saniyede bir durum sorar. Belge başına ~6
 * saniye sürdüğü için ilerleme belge bazında raporlanır — parça bazında
 * olsaydı ekran dakikalarca donmuş görünürdü.
 *
 * ## Yükleme: cetvel önce çizilir
 *
 * Sayaç ilk isteği beklerken şerit eskiden HİÇ basılmıyordu ve sonra aniden
 * beliriyordu; kabuğun yüksekliği zıplıyor, üstelik o an ekranda «özet
 * kapsamı» diye bir şeyin var olduğu bile bilinmiyordu. Şimdi etiket ve şeridin
 * yapısı hemen basılıyor, yalnız SAYILAR bekliyor: yükleme sırasında hiçbir
 * sayı, hiçbir oran ve hiçbir animasyonlu sayaç görünmez. Nabız yalnız
 * «bekliyor» der ve `prefers-reduced-motion` altında durur.
 *
 * İskelet sonsuza kalmaz: kapsam isteği düşerse (`kapsamYukle` hatayı bilerek
 * yutuyor) `denendi` bayrağı iskeleti kaldırır — sonu olmayan bir bekleyiş,
 * bozuk bir sayaçtan daha kötü okunur.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { OzetIsi, OzetKapsam } from "../lib/api";
import { trNum } from "../lib/format";
import { ErrorNotice } from "./ErrorNotice";

/** Durum yoklama aralığı. Daha sık sormak sunucuya değer katmıyor. */
const YOKLAMA_MS = 1500;

export default function SummaryCoverage() {
  const [kapsam, setKapsam] = useState<OzetKapsam | null>(null);
  const [is, setIs] = useState<OzetIsi | null>(null);
  const [hata, setHata] = useState<unknown>(null);
  const [mesgul, setMesgul] = useState(false);
  /** İlk kapsam isteği tamamlandı mı (başarılı ya da başarısız). */
  const [denendi, setDenendi] = useState(false);

  const zamanlayici = useRef<ReturnType<typeof setTimeout> | null>(null);
  const canli = useRef(true);

  useEffect(() => {
    canli.current = true;
    return () => {
      canli.current = false;
      if (zamanlayici.current) clearTimeout(zamanlayici.current);
    };
  }, []);

  const kapsamYukle = useCallback(async () => {
    try {
      const k = await api.summaryCoverage();
      if (canli.current) setKapsam(k);
    } catch {
      // Kapsam sayacı yardımcı bir göstergedir; alınamazsa panelin geri
      // kalanını hata kutusuyla boğmuyoruz. Düğmenin kendi hatası ayrı
      // gösterilir.
    } finally {
      // İstek BİTTİ bilgisi hatadan bağımsız: iskelet yalnız «henüz
      // sorulmadı» hâlini anlatır, «hiç gelmeyecek» hâlini anlatmaz.
      if (canli.current) setDenendi(true);
    }
  }, []);

  useEffect(() => {
    void kapsamYukle();
  }, [kapsamYukle]);

  const yokla = useCallback(
    async (jobId: string) => {
      try {
        const durum = await api.summaryStatus(jobId);
        if (!canli.current) return;
        setIs(durum);
        if (durum.bitti) {
          // İş bitti: sayaçlar artık değişti, yeniden oku.
          void kapsamYukle();
          return;
        }
        // Koşu sürerken de tazele: kapsam sayacı canlı artsın.
        void kapsamYukle();
        zamanlayici.current = setTimeout(() => void yokla(jobId), YOKLAMA_MS);
      } catch (e) {
        if (!canli.current) return;
        // Durum sorgusu düşerse iş yine de koşuyor olabilir; sonucu
        // kaybetmemek için yoklamayı bırakmıyoruz ama hatayı da gizlemiyoruz.
        setHata(e);
        zamanlayici.current = setTimeout(
          () => void yokla(jobId),
          YOKLAMA_MS * 2,
        );
      }
    },
    [kapsamYukle],
  );

  // Sayfa, koşan bir işin ortasında açılmış olabilir (yenileme, başka sekme).
  // O işi sahiplenmek, ilerlemeyi kaybetmemenin tek yolu.
  useEffect(() => {
    if (!kapsam?.calisan_is || is) return;
    void yokla(kapsam.calisan_is);
  }, [kapsam?.calisan_is, is, yokla]);

  async function baslat() {
    setHata(null);
    setMesgul(true);
    try {
      const kayit = await api.summaryBuild();
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
      setIs(await api.summaryCancel(jobId));
    } catch (e) {
      setHata(e);
    }
  }

  if (!kapsam) {
    if (denendi) return null;
    return (
      <div
        className="ozet-kapsam-iskelet"
        role="status"
        aria-live="polite"
        aria-busy="true"
      >
        <span className="durum-goz-ustu">özet kapsamı</span>
        <span className="durum-iskelet-genis" aria-hidden="true" />
        <p className="durum-iskelet-not">
          Kapsam sayısı sunucudan okunuyor. Yapı hemen basılır, yalnız değerler
          bekler — dönen bir sayaç bir oran iddia etmez.
        </p>
      </div>
    );
  }

  if (kapsam.toplam <= 0) return null;

  const oran = Math.round((kapsam.ozetli / kapsam.toplam) * 100);
  const kosuyor = !!is && !is.bitti;
  // «Kaynağı tazelendiği için özeti düşürülen belge» ile «üretimi sonuçsuz
  // kalan belge» AYNI KOVADA duruyor (`basarisiz`) ama aynı şey değil. Kova
  // ayrımı özet katmanının kuralıdır ve doğrudur: ikisi de TEKRAR DENENEBİLİR,
  // yani `hedef`e girer ve düğme ikisini de üretir (`summarize/toplu.sayim`).
  // Yanlış olan yalnız CÜMLE: tazeleme sonrası düşürülen özet için «üretim
  // sonuçsuz kaldı» demek, yapılmamış bir denemenin başarısızlığını iddia
  // etmek olurdu.
  //
  // Çözüm uca yeni bir kova EKLEMEK değil — o, «dört kova toplamı = korpus»
  // sözleşmesini bozardı. Uç `sebepler` sözlüğünü zaten döndürüyor; ayrım
  // burada, yalnız anlatı düzeyinde yapılıyor. Sayılar değişmiyor.
  const kaynakDegisti = kapsam.sebepler?.["kaynak_degisti"] ?? 0;
  // Alt sınır 0: sebep sözlüğü ile kova sayacı bir yarış durumunda ayrışırsa
  // ekranda negatif bir belge sayısı yazmasın.
  const basarisiz = Math.max(0, kapsam.basarisiz - kaynakDegisti);
  // Hedef daha belli değilken (iş "hedef belgeler belirleniyor" evresinde)
  // çubuk BELİRSİZ çizilir. 0/0'ı %100 diye göstermek, hiç başlamamış bir işi
  // bitmiş gibi gösterirdi.
  const oran0100 =
    is && is.hedef > 0
      ? Math.min(100, Math.round((is.islenen / is.hedef) * 100))
      : null;

  return (
    // İş KOŞARKEN katlama zorla açık: arkada ilerleyen bir üretimi katlanmış
    // bir kutunun içinde saklamak, kullanıcının onu durdurabileceğini de
    // saklardı. `open` yalnız o hâlde veriliyor; aksi hâlde nitelik hiç
    // yazılmaz ve kullanıcı kutuyu serbestçe açıp kapatabilir.
    <details className="ozet-kapsam" {...(kosuyor ? { open: true } : {})}>
      {/* KATLANDI (2026-08-12). Bu blok, adil kıyas notu katlandıktan sonra
          katlanan üstünün en büyük tek tüketicisi hâline gelmişti: üç satırlık
          bir paragraf ARTI bir operatör düğmesi, hem de sekmelerden önce ve her
          ekranda. Canlı ekranda ölçüldü — kıyas tablosu yine katlamanın altında
          kalıyordu, yalnız sebebi değişmişti.

          Özet: her zaman görünen tek satır. Gerekçeler ve üretim düğmesi
          açılınca geliyor. Kapatma DEĞİL, katlama: sayı hiç kaybolmuyor. */}
      <summary className="ozet-kapsam-ozet small muted">
        <span className="badge badge-llm">özet kapsamı</span>{" "}
        <b>{trNum(kapsam.ozetli)}</b> / {trNum(kapsam.toplam)} kampanyada{" "}
        {/* "AI özeti" TEK parçada kalmalı: JSX satır kırılması ifadeyi ikiye
            böldüğünde `test_ozet_gorunurluk` kapısı düşer — ve haklı olarak,
            çünkü kullanıcıya dönük etiketin bütünlüğünü ölçüyor. */}
        <span>AI özeti</span> var (%{trNum(oran)})
        {kapsam.hedef > 0 ? ` · ${trNum(kapsam.hedef)} belge bekliyor` : ""}
      </summary>

      <p className="small muted ozet-kapsam-govde">
        {kapsam.icerik_yok > 0 && (
          <>
            {trNum(kapsam.icerik_yok)} belgede{" "}
            <b>özetlenecek içerik yok</b>: sayfanın tamamı çerçeve metni (form
            listesi, gezinme, yasal bildirim).{" "}
          </>
        )}
        {kapsam.denenmemis > 0 && (
          <>
            {trNum(kapsam.denenmemis)} belge <b>henüz özetlenmedi</b>
            {basarisiz > 0
              ? `, ${trNum(basarisiz)} belgede üretim sonuçsuz kaldı`
              : ""}
            .{" "}
          </>
        )}
        {kapsam.denenmemis === 0 && basarisiz > 0 && (
          <>
            {trNum(basarisiz)} belgede üretim sonuçsuz kaldı; tekrar
            denenebilir.{" "}
          </>
        )}
        {kaynakDegisti > 0 && (
          <>
            {trNum(kaynakDegisti)} belgenin <b>kaynak metni tazelendi</b>, eski
            özeti bu yüzden düşürüldü — üretim başarısız olmadı, özet artık
            metni tarif etmiyordu. Bunlar tekrar üretilecek.{" "}
          </>
        )}
        Kaynak metin her belgede tam hâliyle durur ve uydurma özet basılmaz.
      </p>

      {kapsam.hedef > 0 && !kosuyor && (
        <div className="ozet-kapsam-eylem">
          <button
            type="button"
            className="btn"
            onClick={() => void baslat()}
            disabled={mesgul || !kapsam.llm_acik}
          >
            {/* Etiket «AI», şema adı «llm»: kullanıcıya dönük her metinde
                bu ayrım korunur (bkz. tests/test_ozet_gorunurluk.py). */}
            {mesgul
              ? "Başlatılıyor…"
              : `AI özeti üret (${trNum(kapsam.hedef)} belge)`}
          </button>
          <span className="small muted">
            {kapsam.llm_acik ? (
              <>
                Yerel modelle çalışır, <b>internet gerektirmez</b>. Belge başına
                birkaç saniye sürer; bu ekranı kapatsanız da arka planda devam
                eder.
              </>
            ) : (
              kapsam.llm_notu
            )}
          </span>
        </div>
      )}

      {kosuyor && is && (
        <div className="tazele-ilerleme" aria-live="polite">
          <div
            className="tazele-ilerleme-cubuk"
            role="progressbar"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={oran0100 ?? undefined}
            aria-label="Özet üretimi ilerlemesi"
          >
            <span
              className={`tazele-ilerleme-dolgu${
                oran0100 === null ? " belirsiz" : ""
              }`}
              style={oran0100 === null ? undefined : { width: `${oran0100}%` }}
            />
          </div>
          <div className="ozet-kapsam-eylem">
            <span className="small">
              {is.asama} <span className="muted">·</span>{" "}
              <b>{trNum(is.uretilen)}</b> özet üretildi
            </span>
            <button
              type="button"
              className="btn btn-ghost"
              onClick={() => void durdur(is.is_id)}
              disabled={is.iptal_istendi}
            >
              {is.iptal_istendi ? "Durduruluyor…" : "Durdur"}
            </button>
          </div>
        </div>
      )}

      {!!is && is.bitti && (
        <p className="small muted" style={{ margin: "var(--sp-2) 0 0" }}>
          {is.mesaj ?? is.asama} <b>{trNum(is.uretilen)}</b> özet üretildi,{" "}
          {trNum(is.yazilan)} satır yazıldı.
          {is.islenen > is.uretilen && (
            <>
              {" "}
              Kalan {trNum(is.islenen - is.uretilen)} belgede model özet
              üretmedi; <b>sahte özet basılmadı</b>.
            </>
          )}
        </p>
      )}

      {!!hata && (
        <div style={{ marginTop: "var(--sp-2)" }}>
          <ErrorNotice error={hata} />
        </div>
      )}
    </details>
  );
}
