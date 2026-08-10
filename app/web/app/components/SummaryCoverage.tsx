"use client";

/**
 * Özet kapsam göstergesi — «kaç belgede AI özeti var» bilgisini görünür kılar.
 *
 * İlgili: ./SummaryNotice.tsx, scripts/build_summaries.py
 *
 * ## Neden ekranda duruyor
 *
 * Panel AI özeti vaat ediyor ama özetler toplu koşumda üretiliyor; koşum
 * bitene kadar bir kısmı boş. Kullanıcı bunu bilmeden tek tek belgeleri
 * açarsa, boş özetlerin bir ARIZA olduğunu sanır.
 *
 * Sayı istemcide hesaplanır: `/campaigns` yanıtı `ozet` alanını zaten
 * taşıyor. Ek uç açmak, aynı bilgiyi ikinci kez üretmek olurdu.
 *
 * ## Sayaç canlı — ÖLÇÜLDÜ (2026-08-09)
 *
 * Toplu koşum sürerken sayaç artmalı, yoksa kullanıcı ilerlemeyi göremez.
 * `/campaigns` uç noktası önbelleksizdir (her istekte `repo.all_campaigns()`
 * koşar), dolayısıyla sayfa her yenilendiğinde DB'nin O ANKİ hâlini gösterir.
 * Ölçüm: DB'de `ozet` dolu satır sayısı ile `/campaigns` üzerinden hesaplanan
 * sayı birebir aynı çıktı ve koşum ilerledikçe ikisi birlikte arttı.
 *
 * Not: belge ekranının uç noktası (`/campaigns/{id}/text`) kampanya başına
 * ÖNBELLEKLİDİR. Koşum sırasında bir belge özeti yazılmadan ÖNCE açıldıysa, o
 * belgede «özet yok» notu API yeniden başlatılana dek kalır. Kapsam sayacı bu
 * önbellekten etkilenmez; ikisi geçici olarak ayrışabilir.
 *
 * Eksik kapsamı gizlemiyoruz: ölçülen sayı neyse o yazılır, yuvarlanmaz ve
 * saklanmaz — aksi, sistemin ne yaptığı hakkında yanlış izlenim bırakırdı.
 */

import { trNum } from "../lib/format";

type Props = {
  toplam: number;
  ozetli: number;
};

export default function SummaryCoverage({ toplam, ozetli }: Props) {
  if (toplam <= 0) return null;

  const oran = Math.round((ozetli / toplam) * 100);
  const eksik = toplam - ozetli;

  return (
    <p className="small muted" style={{ margin: "0 0 var(--sp-4)" }}>
      <span className="badge badge-llm">özet kapsamı</span>{" "}
      <b>{trNum(ozetli)}</b> / {trNum(toplam)} kampanyada AI özeti var (%
      {trNum(oran)}).{" "}
      {eksik > 0 && (
        <>
          Kalan {trNum(eksik)} belgede <b>özetlenecek içerik yok</b>: sayfanın
          tamamı çerçeve metni (form listesi, gezinme, yasal bildirim). Kaynak
          metin her belgede tam hâliyle durur ve uydurma özet basılmaz.
        </>
      )}
    </p>
  );
}
