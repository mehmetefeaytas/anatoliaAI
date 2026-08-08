/**
 * LLM özeti — kaynak metnin ÜSTÜNDE, üretildiği açıkça etiketli.
 *
 * İlgili: src/api/main.py `GET /campaigns/{id}/text` (`ozet`, `ozet_kaynak`)
 *         scripts/build_summaries.py, src/summarize/ozet.py
 *
 * Kural: özet ile kaynak metin aynı ekranda görünüyorsa, hangisinin üretilmiş
 * hangisinin belge olduğu tek bakışta anlaşılmalıdır. Etiket yumuşatılmaz
 * («yapay zekâ destekli» değil, «LLM tarafından üretilmiştir»).
 *
 * ## Özet YOKSA neden artık sessiz kalmıyoruz
 *
 * Bu bileşen eskiden `ozet` boşsa `null` döndürüyordu; gerekçesi «boş kutu,
 * bilgi yokluğunu bilgi varmış gibi gösterir» idi. Ölçüm bu gerekçeyi
 * çürüttü: 1.774 kampanyanın 1.429'unda (%81) `ozet` boş. Yani kullanıcı
 * ekranların çoğunda hiçbir şey görmüyor ve «bozuk mu, yok mu» ayrımını
 * yapamıyor. Sessizlik burada dürüstlük değil, belirsizlik üretiyordu.
 *
 * Artık boşluk ADLANDIRILIYOR: özetin üretilmediği yazılıyor ve sebebi
 * söyleniyor (özetler toplu koşumda üretilir, korpusun tamamı henüz
 * işlenmedi). SAHTE ÖZET ÜRETİLMİYOR — `src/summarize/ozet.py` kural tabanlı
 * sahte özeti zaten yasaklıyor, arayüz de o yasağı bozmuyor (CLAUDE.md §19).
 *
 * `ExtractLive` LLM kapalıyken açıkça uyarı basıyor; bu, aynı dürüstlük
 * sinyalinin özet yolundaki karşılığıdır.
 */

type Props = {
  ozet?: string | null;
  ozetKaynak?: string | null;
  /**
   * Özet yoksa açıklayıcı notu bas. Yalnızca özetin BEKLENDİĞİ yerlerde
   * (belge denetim ekranı, kıyas çekmecesi) anlamlıdır; listede her satırın
   * altına not basmak gürültü olurdu.
   */
  bosluguAcikla?: boolean;
};

const KAYNAK_ETIKET: Record<string, string> = {
  llm: "yerel LLM",
  rule: "kural katmanı",
  extractive: "çıkarımsal (metinden seçilmiş cümleler)",
};

export default function SummaryNotice({
  ozet,
  ozetKaynak,
  bosluguAcikla = true,
}: Props) {
  const metin = typeof ozet === "string" ? ozet.trim() : "";

  if (!metin) {
    if (!bosluguAcikla) return null;
    return (
      <div className="summary-box summary-empty">
        <div className="summary-label">
          <span className="badge">özet yok</span>
          <span>Bu belge için özet üretilmedi.</span>
        </div>
        <p className="summary-body">
          Özetler yerel LLM ile toplu koşumda üretilir ve korpusun tamamı henüz
          işlenmedi. Eksik özet, belgenin kendisiyle ilgili bir eksiklik
          değildir; kaynak metin aşağıda tam hâliyle durur. Bu boşluk
          doldurulmaz — üretilmemiş bir özet uydurulmaz.
        </p>
      </div>
    );
  }

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
      <p className="summary-body">{metin}</p>
    </div>
  );
}
