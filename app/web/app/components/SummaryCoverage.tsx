"use client";

/**
 * Özet kapsam göstergesi — «%81'inde özet yok» bilgisini görünür kılar.
 *
 * İlgili: ./SummaryNotice.tsx, scripts/build_summaries.py
 *
 * ## Neden ekranda duruyor
 *
 * Panel LLM özeti vaat ediyor ama kampanyaların büyük çoğunluğunda özet boş:
 * özetler yerel LLM ile toplu koşumda üretiliyor ve korpusun tamamı henüz
 * işlenmedi. Kullanıcı bunu bilmeden tek tek belgeleri açarsa, boş özetlerin
 * bir ARIZA olduğunu sanır.
 *
 * Sayı istemcide hesaplanır: `/campaigns` yanıtı `ozet` alanını zaten
 * taşıyor. Ek uç açmak, aynı bilgiyi ikinci kez üretmek olurdu.
 *
 * Eksik kapsamı gizlemiyoruz. Bir teslim ekranında «%19» yazmak konforlu
 * değil, ama ölçülen sayı budur ve yuvarlamak ya da saklamak, sistemin
 * ne yaptığı hakkında yanlış bir izlenim bırakırdı (CLAUDE.md §19).
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
      <b>{trNum(ozetli)}</b> / {trNum(toplam)} kampanyada LLM özeti var (%
      {trNum(oran)}).{" "}
      {eksik > 0 && (
        <>
          Kalan {trNum(eksik)} belge için özet <b>henüz üretilmedi</b>; kaynak
          metin her belgede tam hâliyle durur ve eksik özet uydurulmaz.
        </>
      )}
    </p>
  );
}
