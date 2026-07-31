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
 */

import type { FieldMeta } from "../lib/api";

type Props = {
  fields: FieldMeta[];
  value: string;
  onChange: (field: string) => void;
};

export default function FieldChips({ fields, value, onChange }: Props) {
  return (
    <div className="row" role="tablist" aria-label="Karşılaştırılacak alan">
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
  );
}
