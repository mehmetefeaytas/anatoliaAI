"use client";

/**
 * Alan seçici çipleri — 12 alanın tamamı (CLAUDE.md §9 veri modeli).
 *
 * Eski arayüzde 3 alan sabit kodluydu (`page.tsx:21-25`); kural katmanı 12/12
 * alanı çıkarıyor olmasına rağmen 9'u ekranda hiç görünmüyordu. Liste artık
 * `GET /fields` ucundan gelir → yeni alan eklenince arayüz kendiliğinden büyür.
 *
 * Sıralaması tanımlı OLMAYAN alanlar (`direction === "unranked"`) soluk gösterilir:
 * kıyaslanamayan bir alanı kıyaslanabilir gibi sunmak CLAUDE.md §17'ye aykırıdır.
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

type Props = {
  fields: FieldMeta[];
  value: string;
  onChange: (field: string) => void;
};

export default function FieldChips({ fields, value, onChange }: Props) {
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
            onClick={() => onChange(f.field)}
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
