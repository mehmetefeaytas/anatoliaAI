"use client";

/**
 * Alan çipleri — 12 alanın tamamı, iki KİPTE (CLAUDE.md §9 veri modeli).
 *
 * İlgili: ./ComparePanel.tsx (seçici kipi), ./BankaSayfasi.tsx (durum kipi),
 *         ../styles/banka.css (`.alan-cip*`), ../lib/api.ts (`FieldMeta`),
 *         src/api/main.py `GET /fields`
 *
 * Eski arayüzde 3 alan sabit kodluydu (`page.tsx:21-25`); kural katmanı 12/12
 * alanı çıkarıyor olmasına rağmen 9'u ekranda hiç görünmüyordu. Liste artık
 * `GET /fields` ucundan gelir → yeni alan eklenince arayüz kendiliğinden büyür.
 *
 * ## İki kip, tek liste — neden aynı bileşen
 *
 * SEÇİCİ kipi (varsayılan): «hangi alan kıyaslanacak» sorusunu sorar, çipler
 * düğmedir, biri seçilidir. Sıralaması tanımlı OLMAYAN alanlar
 * (`direction === "unranked"`) soluk gösterilir: kıyaslanamayan bir alanı
 * kıyaslanabilir gibi sunmak §17'ye aykırıdır.
 *
 * DURUM kipi (`durumlar` verilirse): «bu bankada hangi alan dolu» sorusunu
 * yanıtlar, çipler düğme değil metindir. Ayrı bir bileşen yazılmadı çünkü iki
 * kipin ortak vaadi tam olarak şudur: **12 alanın 12'si her hâlde basılır,
 * boş olan gizlenmez.** O vaat tek yerde tutulmalı; iki dosyaya bölünse biri
 * güncellenip diğeri unutulurdu (aynı hikâye `FairnessNotice` başlığında).
 *
 * ## Durum kipinde ÜÇ hâl var, iki değil
 *
 * `dolu` / `bos` ayrımı yetmez, çünkü üçüncü bir hâl gerçekten var:
 * **bilinmiyor**. Bir alanın belirli bir bankada kaç belgede çıktığını veren
 * uç YOK (`/stats` yalnız `banka_kapsami = {belge, alan}` verir, yani KAÇ
 * çeşit alan dolduğunu söyler, HANGİLERİ olduğunu söylemez). Ölçülemeyen bir
 * durumu `null` diye basmak, bu ekranın reddettiği şeyin ta kendisi olurdu —
 * `YildizPuan` boş yıldız basmıyorsa, çip de kanıtsız `null` basmaz. Üç hâlin
 * üçü ayrı BİÇİM taşır (dolu çerçeve / kesikli çerçeve / kesikli çerçeve +
 * dolgu) ve üçü ayrı METİN taşır (`· 3` / `· null` / `· ?`); renk hiçbir
 * hâlde tek sinyal değildir.
 *
 * ## Görünür başlık neden eklendi (2026-08-09)
 *
 * Kullanıcı «kutucuklar ile Kampanya Türü kısmı kafa karıştırıyor» diye
 * bildirdi. Sebebi şuydu: bu çipler **etiketsizdi** — başlığı yalnız ekran
 * okuyucuya görünen `aria-label` taşıyordu. Görsel olarak hemen altındaki
 * «Kampanya türü» açılır süzgeciyle aynı satır bandındaydılar, dolayısıyla
 * ikisi tek bir süzgeç kümesi gibi okunuyordu. Oysa iki AYRI eksen var:
 *
 *   - Çipler: **hangi alan** kıyaslanacak (kâr payı oranı, vade, tutar …)
 *   - Kampanya türü süzgeci: **hangi ürün sınıfı** listelenecek (8 sınıf)
 *
 * Başlık artık görünür ve `aria-labelledby` ile aynı düğüme bağlı; böylece
 * gören ve görmeyen kullanıcı AYNI metni alır (ikisi ayrışırsa biri
 * güncellenip diğeri unutulur).
 */

import type { FieldMeta } from "../lib/api";

/**
 * Bir alanın bir bankadaki durumu.
 *
 * `dolu.adet === null` bilerek mümkündür: alanın DOLU olduğu kanıtlanmış ama
 * kaç belgede çıktığı ölçülemiyorsa sayı uydurulmaz, çip `· dolu` yazar.
 */
export type AlanDurumu =
  | { tip: "dolu"; adet: number | null }
  | { tip: "bos" }
  | { tip: "bilinmiyor" };

type Props = {
  fields: FieldMeta[];
  /** Seçici kipi: seçili alan. Durum kipinde verilmez. */
  value?: string;
  onChange?: (field: string) => void;
  /**
   * Verilirse bileşen DURUM kipine geçer. Eksik anahtar = `bilinmiyor`:
   * sözlükte olmayan alan sessizce düşmez, «ölçülemedi» olarak basılır.
   */
  durumlar?: Record<string, AlanDurumu>;
};

/** Durum kipindeki çipin biçim sınıfı ve son eki. */
function cipBicimi(durum: AlanDurumu): {
  sinif: string;
  ek: string;
  baslik: string;
} {
  switch (durum.tip) {
    case "dolu":
      return {
        sinif: "alan-cip alan-cip-dolu",
        ek: durum.adet === null ? "dolu" : String(durum.adet),
        baslik:
          durum.adet === null
            ? "Bu alan bu bankada çıkarıldı; belge sayısı bu uçtan gelmiyor."
            : `Bu alan bu bankanın ${durum.adet} belgesinde çıkarıldı.`,
      };
    case "bos":
      return {
        sinif: "alan-cip alan-cip-bos",
        ek: "null",
        baslik:
          "Ölçüldü ve bu bankada hiç çıkmadı — boş bırakıldı, sıfır yazılmadı.",
      };
    default:
      return {
        sinif: "alan-cip alan-cip-bilinmiyor",
        ek: "?",
        baslik:
          "Bu alanın bu bankadaki durumu ölçülemiyor: alan başına banka " +
          "kapsaması veren bir uç yok. «null» ile aynı şey DEĞİL.",
      };
  }
}

export default function FieldChips({
  fields,
  value,
  onChange,
  durumlar,
}: Props) {
  if (durumlar) {
    return (
      <div className="alan-seridi" role="list">
        {fields.map((f) => {
          const { sinif, ek, baslik } = cipBicimi(
            durumlar[f.field] ?? { tip: "bilinmiyor" },
          );
          return (
            <span key={f.field} className={sinif} role="listitem" title={baslik}>
              {/* Alan adı MAKİNE verisidir: ham sütun adı, Türkçe etiketi
                  `title`da. Bu ekranın işi hangi alanın çıkarıldığını
                  denetlenebilir kılmak; denetlenecek şey sütun adıdır. */}
              {f.field} · {ek}
            </span>
          );
        })}
      </div>
    );
  }

  return (
    <div className="chip-group">
      <span className="chip-group-label" id="alan-secici-basligi">
        Karşılaştırılacak alan
      </span>
      <div className="row" role="tablist" aria-labelledby="alan-secici-basligi">
        {fields.map((f) => (
          <button
            key={f.field}
            type="button"
            role="tab"
            aria-selected={value === f.field}
            className={`chip${f.comparable_field ? "" : " chip-muted"}`}
            title={f.direction_label}
            onClick={() => onChange?.(f.field)}
          >
            {f.label}
            {!f.comparable_field && (
              <span aria-hidden="true" title="Sıralama yönü tanımlı değil">
                {" "}
                ·
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
