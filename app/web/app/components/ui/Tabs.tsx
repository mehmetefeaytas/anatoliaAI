"use client";

/**
 * Sekme şeridi — tam ARIA tab deseni.
 *
 * İlgili: ../../page.tsx, ../../lib/tabState.ts
 *
 * ## Eskiden neden yarımdı
 *
 * `role="tablist"` ve `aria-selected` vardı ama `role="tabpanel"`,
 * `aria-controls`/`id` eşlemesi ve ok tuşu navigasyonu YOKTU. Ekran okuyucu
 * için bu, "sekme" diye duyurulan ama neyi kontrol ettiği bilinmeyen bir
 * düğme kümesiydi; klavye kullanıcısı için de her sekmeye ayrı ayrı Tab'lamak
 * gereken bir engeldi.
 *
 * ## Roving tabindex
 *
 * WAI-ARIA deseni: şeritte YALNIZCA seçili sekme Tab sırasına girer
 * (`tabIndex={0}`), diğerleri çıkar (`tabIndex={-1}`). Sekmeler arasında ok
 * tuşlarıyla gezilir, Home/End uçlara atlar. Böylece Tab tuşu şeridi bir
 * bütün olarak geçer ve içeriğe ulaşır.
 *
 * Seçim ok tuşuyla ANINDA değişir (otomatik etkinleştirme). Panel içeriği
 * yerelden geldiği için gecikme yok; manuel etkinleştirme (Enter bekleme)
 * burada gereksiz bir tuş vuruşu olurdu.
 */

import { useRef } from "react";

export type SekmeTanimi<T extends string> = {
  key: T;
  label: string;
};

type Props<T extends string> = {
  sekmeler: readonly SekmeTanimi<T>[];
  aktif: T;
  onDegis: (key: T) => void;
  /** `aria-label` — şeridin ne olduğunu söyler. */
  etiket: string;
};

/** Panel `id`'si; `aria-controls` ile buradaki değer eşleşir. */
export function panelId(key: string): string {
  return `panel-${key}`;
}

/** Sekme düğmesinin `id`'si; panelin `aria-labelledby`'si buna işaret eder. */
export function sekmeId(key: string): string {
  return `sekme-${key}`;
}

export default function Tabs<T extends string>({
  sekmeler,
  aktif,
  onDegis,
  etiket,
}: Props<T>) {
  const seritRef = useRef<HTMLDivElement>(null);

  function odakla(indeks: number) {
    const dugmeler = seritRef.current?.querySelectorAll<HTMLButtonElement>(
      '[role="tab"]',
    );
    dugmeler?.[indeks]?.focus();
  }

  function tusa(e: React.KeyboardEvent<HTMLDivElement>) {
    const son = sekmeler.length - 1;
    const su = sekmeler.findIndex((s) => s.key === aktif);
    let hedef: number | null = null;

    // Şerit yatay: sağ/sol dolaşır, yukarı/aşağı sayfa kaydırması için
    // dokunulmadan bırakılır.
    if (e.key === "ArrowRight") hedef = su >= son ? 0 : su + 1;
    else if (e.key === "ArrowLeft") hedef = su <= 0 ? son : su - 1;
    else if (e.key === "Home") hedef = 0;
    else if (e.key === "End") hedef = son;

    if (hedef === null) return;
    e.preventDefault();
    onDegis(sekmeler[hedef].key);
    odakla(hedef);
  }

  return (
    <div
      ref={seritRef}
      className="tabs"
      role="tablist"
      aria-label={etiket}
      onKeyDown={tusa}
    >
      {sekmeler.map((s) => {
        const secili = s.key === aktif;
        return (
          <button
            key={s.key}
            id={sekmeId(s.key)}
            type="button"
            role="tab"
            className="chip"
            aria-selected={secili}
            aria-controls={panelId(s.key)}
            tabIndex={secili ? 0 : -1}
            onClick={() => onDegis(s.key)}
          >
            {s.label}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Sekme paneli sarmalayıcısı — `role="tabpanel"` + geriye dönük etiketleme.
 *
 * `tabIndex={0}`: panelin içinde odaklanılabilir öğe yoksa (yalnız metin)
 * klavye kullanıcısı içeriği yine de kaydırabilmeli.
 */
export function TabPanel({
  sekme,
  children,
}: {
  sekme: string;
  children: React.ReactNode;
}) {
  return (
    <div
      id={panelId(sekme)}
      role="tabpanel"
      aria-labelledby={sekmeId(sekme)}
      tabIndex={0}
    >
      {children}
    </div>
  );
}
