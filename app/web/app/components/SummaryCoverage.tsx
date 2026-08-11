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

  if (!kapsam || kapsam.toplam <= 0) return null;

  const oran = Math.round((kapsam.ozetli / kapsam.toplam) * 100);
  const kosuyor = !!is && !is.bitti;
  // Hedef daha belli değilken (iş "hedef belgeler belirleniyor" evresinde)
  // çubuk BELİRSİZ çizilir. 0/0'ı %100 diye göstermek, hiç başlamamış bir işi
  // bitmiş gibi gösterirdi.
  const oran0100 =
    is && is.hedef > 0
      ? Math.min(100, Math.round((is.islenen / is.hedef) * 100))
      : null;

  return (
    <div className="ozet-kapsam">
      <p className="small muted" style={{ margin: 0 }}>
        <span className="badge badge-llm">özet kapsamı</span>{" "}
        <b>{trNum(kapsam.ozetli)}</b> / {trNum(kapsam.toplam)} kampanyada{" "}
        {/* "AI özeti" TEK parçada kalmalı: JSX satır kırılması ifadeyi ikiye
            böldüğünde `test_ozet_gorunurluk` kapısı düşer — ve haklı olarak,
            çünkü kullanıcıya dönük etiketin bütünlüğünü ölçüyor. */}
        <span>AI özeti</span> var (%{trNum(oran)}).{" "}
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
            {kapsam.basarisiz > 0
              ? `, ${trNum(kapsam.basarisiz)} belgede üretim sonuçsuz kaldı`
              : ""}
            .{" "}
          </>
        )}
        {kapsam.denenmemis === 0 && kapsam.basarisiz > 0 && (
          <>
            {trNum(kapsam.basarisiz)} belgede üretim sonuçsuz kaldı; tekrar
            denenebilir.{" "}
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
    </div>
  );
}
