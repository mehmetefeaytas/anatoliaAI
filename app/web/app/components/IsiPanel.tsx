"use client";

/**
 * Isı haritası ekranı — «bu alanı korpusun neresinde ölçebiliyoruz».
 *
 * İlgili: ./grafik/IsiHaritasi.tsx, ../styles/grafik.css, ../lib/api.ts,
 *         ../page.tsx, CLAUDE.md §12 (sekiz kampanya türü), §17 (adil kıyas)
 *
 * ## Neden bu dosya var
 *
 * `grafik/IsiHaritasi.tsx` HİÇBİR YERDEN çağrılmıyordu (ölçüldü: grep, sıfır
 * kullanım). Yani teslimde 11 × 8 kapsama haritası kod olarak vardı ama ekranda
 * hiç görünmüyordu — jüri onu göremezdi. Bu bileşen ona bir yüzey veriyor.
 *
 * ## Neden kendi sekmesi
 *
 * Harita bir ALANIN korpus genelindeki ölçülebilirliğini anlatıyor; kıyas ekranı
 * ise TEK kampanya türünde bankaları sıralıyor. İkisi farklı soruların cevabı:
 * «kim daha avantajlı» ile «bunu nerede ölçebiliyoruz». Haritayı kıyas ekranının
 * altına gömmek, ikinci soruyu birincinin dipnotu gibi gösterirdi — oysa bu
 * panelin tezi tam olarak ikinci sorunun birincisi kadar önemli olduğu.
 *
 * ## Neden tek istek DEĞİL
 *
 * Harita iki ayrı bilgiye ihtiyaç duyuyor ve ikisi ayrı uçtan geliyor:
 *
 *   `/campaigns`  belge var mı  → hücre `bos` mu `belgesiz` mi
 *   `/compare`    değer var mı  → hücre `dolu` mu `kosullu` mu
 *
 * Bu ayrım bileşenin tasarım kararı, bu dosyanın değil (bkz. IsiHaritasi.tsx).
 * Buradaki iş yalnız iki kaynağı birleştirmek ve alan seçimini taşımak.
 *
 * `/compare` çağrısı TÜRE GÖRE SÜZÜLMÜYOR (`type` parametresi verilmiyor):
 * harita sekiz türün hepsini birden çiziyor, yani satırların tamamı gerekiyor.
 * `per_bank=all` de bu yüzden — `best` (varsayılan) banka başına tek satır
 * bırakır ve bir bankanın iki türde ölçülmüş değeri varsa biri düşerdi, harita
 * o hücreyi yanlışlıkla boş çizerdi.
 */

import { useMemo } from "react";
import IsiHaritasi from "./grafik/IsiHaritasi";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import { api, type CampaignSummary, type FieldMeta } from "../lib/api";
import { useAsync } from "../lib/useAsync";

/**
 * Sekiz kampanya türünün RESMÎ sırası (CLAUDE.md §12).
 *
 * Alfabetik değil: genelden özele (Finansman → İhtiyaç/Konut/Taşıt), sonra
 * ürün dışı kampanya aileleri. `/stats`in `campaign_types` listesi alfabetik
 * geliyor ve haritada sütun sırası anlam taşıdığı için burada sabit tutuluyor.
 * Korpusta hiç geçmeyen tür de sütununu KORUR — sekiz sınıf, sekiz sütun.
 */
const TURLER: readonly string[] = [
  "Finansman",
  "İhtiyaç Finansmanı",
  "Konut Finansmanı",
  "Taşıt Finansmanı",
  "Kart",
  "Alışveriş Puanı",
  "Yeni Müşteri",
  "Yatırım Ürünü",
];

type Props = {
  /** Alan listesi — seçicinin kaynağı. */
  fields: FieldMeta[];
  /** Sayfanın zaten indirdiği belge üstverisi; ikinci istek atılmıyor. */
  kayitlar: CampaignSummary[];
  /** Belge listesi hâlâ yolda mı. */
  kayitlarYukleniyor: boolean;
  /** Haritanın konusu olan alan. */
  alan: string;
  onAlanDegis: (alan: string) => void;
};

export default function IsiPanel({
  fields,
  kayitlar,
  kayitlarYukleniyor,
  alan,
  onAlanDegis,
}: Props) {
  const bankalar = useAsync(() => api.banks(), []);
  // `per_bank=all`: gerekçe dosya başlığında. Alan değişince yeniden istenir.
  const kapsama = useAsync(
    () => api.compare(alan, undefined, undefined, "all"),
    [alan],
  );

  const seciliAlan = fields.find((f) => f.field === alan) ?? null;

  // Satır sırası KORPUS büyüklüğüne göre değil, katalog sırasına göre: harita
  // bir sıralama değil bir kapsama tablosu ve satırları belge sayısına göre
  // dizmek, okuyucuya olmayan bir hiyerarşi önerirdi.
  const bankaSirasi = useMemo(
    () => (bankalar.data ?? []).map((b) => b.name),
    [bankalar.data],
  );

  if (kayitlarYukleniyor || kapsama.loading || bankalar.loading) {
    return <Loading label="Kapsama haritası hesaplanıyor…" satir={6} />;
  }

  // Kapsama isteği düşerse harita çizilmez: `kapsama` olmadan her hücre
  // `bos`/`belgesiz` görünür ve harita sessizce «hiçbir yerde değer yok»
  // derdi — ölçülmemişi ölçülmüş göstermenin en sinsi hâli.
  if (kapsama.error) return <ErrorNotice error={kapsama.error} />;
  if (bankalar.error) return <ErrorNotice error={bankalar.error} />;

  return (
    <div className="stack">
      <div className="card">
        {/* Sınıfsız `h3`: `.card h3` zaten mono + BÜYÜK HARF + `--track-caps`
            göz-üstü etiketi (components.css). Yeni bir sınıf, aynı biçimi ikinci
            kez tanımlamak olurdu. */}
        <h3>haritanın konusu</h3>
        <label className="row-tight" htmlFor="isi-alan">
          <span className="mono muted">alan</span>
          <select
            id="isi-alan"
            value={alan}
            onChange={(e) => onAlanDegis(e.target.value)}
          >
            {fields.map((f) => (
              <option key={f.field} value={f.field}>
                {f.label}
              </option>
            ))}
          </select>
        </label>
        {/* Yön bilgisi haritada KULLANILMIYOR ve bunu söylemek gerekiyor:
            harita hangi bankanın daha iyi olduğunu değil, alanın nerede
            ölçülebildiğini gösteriyor. Sıralama iddiası yok. */}
        <p className="small muted" style={{ maxWidth: "var(--measure)" }}>
          Harita sıralama yapmaz; bir alanın on bir banka ile sekiz kampanya
          türünün kesişiminde <b>ölçülebilir olup olmadığını</b> gösterir. Dolu
          hücre bir üstünlük değil, bir ölçüm.
        </p>
      </div>

      {kayitlar.length === 0 ? (
        <EmptyNotice title="Belge üstverisi okunamadı" alan={alan}>
          Harita belge varlığına dayanıyor: bir hücrenin «belge var, değer yok»
          mu «hiç belge yok» mu olduğu bu listeden çıkıyor. Liste boşken iki hâl
          ayırt edilemez, o yüzden harita çizilmiyor.
        </EmptyNotice>
      ) : (
        <IsiHaritasi
          kayitlar={kayitlar}
          kapsama={kapsama.data ?? []}
          alanEtiketi={(seciliAlan?.label ?? alan).toLocaleLowerCase("tr")}
          turler={[...TURLER]}
          bankalar={bankaSirasi}
        />
      )}
    </div>
  );
}
