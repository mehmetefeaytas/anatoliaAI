/**
 * AI özeti — kaynak metnin ÜSTÜNDE, üretildiği açıkça etiketli.
 *
 * İlgili: src/api/main.py `GET /campaigns/{id}/text` (`ozet`, `ozet_kaynak`)
 *         scripts/build_summaries.py, src/summarize/ozet.py
 *
 * Kural: özet ile kaynak metin aynı ekranda görünüyorsa, hangisinin üretilmiş
 * hangisinin belge olduğu tek bakışta anlaşılmalıdır. Etiket yumuşatılmaz:
 * «yapay zekâ destekli» gibi belirsiz bir sıfat değil, «AI tarafından
 * üretilmiştir» denir — okuyan, metnin kaynağını değil modeli gördüğünü bilir.
 *
 * ## Neden «LLM» değil «AI»
 *
 * ## Etiketin üçüncü hâli: «üretilmiş» (v2 tasarım, 2026-08-12)
 *
 * Etiket iki kez değişti ve ikinci değişiklik burada GERİ ALINMIYOR, ileriye
 * taşınıyor. 2026-08-09'daki gerekçe şuydu: «LLM» bir kısaltma ve jargon
 * (`scripts/jargon_lint.py`). Gerekçe doğruydu, çözümü yarımdı — «AI» da bir
 * kısaltma. v2 tasarımı kısaltmayı tümden atıyor: rozet tek bir Türkçe sözcük,
 * «üretilmiş», ve okuyana asıl ayrımı söylüyor — bu metin ALINTILANMADI, ÜRETİLDİ.
 *
 * Yanındaki cümle «AI tarafından» yerine «Yerel model» diyor ve bu daha
 * kesindir: model bu makinede çalıştı, bir servise gitmedi (CLAUDE.md §2
 * on-prem kısıtı). «Kaynak metin aşağıda tam hâliyle duruyor» ise özetin neyin
 * yerine geçMEDİĞİNİ söylüyor.
 *
 * Rozetin rengi `--llm`, `--warn` değil: «üretilmiş» bir uyarı değildir.
 *
 * Eski gerekçe kaydı:
 * Görünen etiket 2026-08-09'da «LLM özeti»nden «AI özeti»ne çevrildi. «LLM»
 * bir mimari adıdır ve panelin okuyucusuna (jüri, banka kullanıcısı) hiçbir
 * şey söylemez; «AI» aynı iddiayı taşır ama anlaşılır. Yumuşatma değil:
 * üretilmiş olduğu bilgisi cümlede aynen duruyor. Kod içindeki adlar
 * (`ozet_kaynak: "llm"`, `KAYNAK_ETIKET`) DEĞİŞMEDİ — onlar DB sözleşmesidir.
 *
 * ## Özet YOKSA neden sessiz kalmıyoruz — ve neden kısa
 *
 * Bu bileşen eskiden `ozet` boşsa `null` döndürüyordu; ölçüm bunu çürüttü:
 * korpusun büyük kısmında `ozet` boştu, yani kullanıcı hiçbir şey görmüyor ve
 * «bozuk mu, yok mu» ayrımını yapamıyordu. Sessizlik dürüstlük değil,
 * belirsizlik üretiyordu.
 *
 * Ama ilk yazılan boşluk notu dört cümleydi ve kendini savunuyordu; ekranın
 * çoğunda görünen bir not, kaynak metinden çok yer kaplayınca bilgi değil
 * gürültü olur. Not iki cümleye indirildi. İNDİRİLİRKEN KORUNAN İKİ ŞEY:
 * (1) özetin ÜRETİLMEDİĞİ, (2) uydurulmayacağı. Sahte özet yasağı
 * `src/summarize/ozet.py` içinde kurallıdır; arayüz o yasağı ne bozar ne de
 * onu anlatmaktan vazgeçer.
 *
 * `ExtractLive` LLM kapalıyken açıkça uyarı basıyor; bu, aynı dürüstlük
 * sinyalinin özet yolundaki karşılığıdır.
 *
 * ## `veri yok ≠ değer sıfır` neden BU yüzeyde
 *
 * Bu bileşen tek bir yerden çağrılıyor: belge denetim ekranı, hem de çıkarılan
 * alanlar tablosunun hemen ardından. O tablonun bazı hücreleri `—` basıyor ve
 * o çizgi iki bambaşka şey demek olabilir: alan metinde geçmiyor (`null`) ya da
 * değer ölçüldü ve sıfır (`%0` — masrafsız, ilk 6 ay ödemesiz). İkincisi
 * gerçek bir üründür ve alanın EN AVANTAJLI ucudur.
 *
 * Ayrımın okuma anahtarı, ayrımın okunduğu ekranda durmalı. Kutunun kendi
 * gövdesi büyümüyor: anahtar katlanmış bir göz-üstü etiketi olarak geliyor
 * (`VeriYokSifirDegil`, ./ErrorNotice.tsx) ve isteyen açıyor.
 */

import { VeriYokSifirDegil } from "./ErrorNotice";

type Props = {
  ozet?: string | null;
  ozetKaynak?: string | null;
  /**
   * Özet yoksa açıklayıcı notu bas. Yalnızca özetin BEKLENDİĞİ yerlerde
   * (belge denetim ekranı, kıyas çekmecesi) anlamlıdır; listede her satırın
   * altına not basmak gürültü olurdu.
   */
  bosluguAcikla?: boolean;
  /**
   * `null` ile `%0` ayrımının okuma anahtarını bas.
   *
   * Varsayılan AÇIK: bu bileşenin bulunduğu tek yer, alan tablosunun altıdır
   * ve anahtar oraya aittir. Özetin listede tek satır olarak göründüğü bir
   * yüzeye taşınırsa kapatılmalı — orada anlatacağı bir tablo yoktur.
   */
  sifirAyrimi?: boolean;
};

/**
 * `ozet_kaynak` ANAHTARI (şema adı, DB sözleşmesi) → görünen etiket.
 *
 * Anahtarlar `llm/rule/extractive` olarak KALIR — `extractor` şemasının
 * adlarıdır ve arayüz sözcüğü değiştiği için şema adı değiştirilmez.
 * Etiket tarafında ise «yerel LLM» yerine «yerel yapay zekâ modeli» yazıyor:
 * aynı cümlede bir yandan «AI özeti» deyip öbür yandan «LLM» demek tutarsızdı.
 * «Yerel» sözcüğü korunuyor, çünkü tek anlamlı teknik iddia odur: model
 * kendi donanımımızda koşuyor, dışarıya belge gitmiyor.
 */
const KAYNAK_ETIKET: Record<string, string> = {
  llm: "yerel yapay zekâ modeli",
  rule: "kural katmanı",
  extractive: "çıkarımsal (metinden seçilmiş cümleler)",
};

export default function SummaryNotice({
  ozet,
  ozetKaynak,
  bosluguAcikla = true,
  sifirAyrimi = true,
}: Props) {
  const metin = typeof ozet === "string" ? ozet.trim() : "";

  if (!metin) {
    if (!bosluguAcikla) return null;
    return (
      <>
        <div className="summary-box summary-empty">
          <div className="summary-label">
            <span className="badge">özet yok</span>
            <span className="summary-note">Bu belgede özetlenecek içerik yok.</span>
          </div>
          <p className="summary-body">
            Sayfanın tamamı çerçeve metni (form listesi, gezinme, yasal
            bildirim). Uydurma özet basılmaz — kaynak metin aşağıda tam
            hâliyle durur.
          </p>
        </div>
        {sifirAyrimi && <VeriYokSifirDegil />}
      </>
    );
  }

  const kaynak = ozetKaynak ? KAYNAK_ETIKET[ozetKaynak] ?? ozetKaynak : null;

  return (
    <>
      <div className="summary-box">
        <div className="summary-label">
          <span className="badge badge-llm">üretilmiş</span>
          <span className="summary-note">
            Yerel model özeti. Kaynak metin aşağıda tam hâliyle duruyor.
            {kaynak ? ` (üreten: ${kaynak})` : ""}
          </span>
        </div>
        <p className="summary-body">{metin}</p>
      </div>
      {sifirAyrimi && <VeriYokSifirDegil />}
    </>
  );
}
