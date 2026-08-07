/**
 * LLM özeti — kaynak metnin ÜSTÜNDE, üretildiği açıkça etiketli.
 *
 * İlgili: src/api/main.py `GET /campaigns/{id}/text` (`ozet`, `ozet_kaynak`)
 *
 * Kural: özet ile kaynak metin aynı ekranda görünüyorsa, hangisinin üretilmiş
 * hangisinin belge olduğu tek bakışta anlaşılmalıdır. Etiket yumuşatılmaz
 * («yapay zekâ destekli» değil, «LLM tarafından üretilmiştir»).
 *
 * `ozet` yoksa/boşsa bu bileşen HİÇBİR ŞEY basmaz — boş kutu, bilgi yokluğunu
 * bilgi varmış gibi gösterir.
 */

type Props = {
  ozet?: string | null;
  ozetKaynak?: string | null;
};

const KAYNAK_ETIKET: Record<string, string> = {
  llm: "yerel LLM",
  rule: "kural katmanı",
  extractive: "çıkarımsal (metinden seçilmiş cümleler)",
};

export default function SummaryNotice({ ozet, ozetKaynak }: Props) {
  if (typeof ozet !== "string" || !ozet.trim()) return null;

  const kaynak = ozetKaynak ? KAYNAK_ETIKET[ozetKaynak] ?? ozetKaynak : null;

  return (
    <div className="summary-box">
      <div className="summary-label">
        <span className="badge badge-llm">özet</span>
        <span>
          LLM tarafından üretilmiştir — kaynak metin aşağıdadır.
          {kaynak ? ` (üreten: ${kaynak})` : ""}
        </span>
      </div>
      <p className="summary-body">{ozet.trim()}</p>
    </div>
  );
}
