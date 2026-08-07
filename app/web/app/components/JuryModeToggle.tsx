"use client";

/**
 * Jüri modu anahtarı — modun AÇIK olduğu her zaman görünür.
 *
 * İlgili: ../lib/juryMode.tsx
 *
 * Gizli bir mod, açık unutulduğunda ticari ekranı denetim ekranına çevirir ve
 * kimse fark etmez. Bu yüzden mod açıkken düğmenin yanında ayrıca bir şerit
 * durur: neyin değiştiğini tek cümleyle söyler.
 */

import { useJuryMode } from "../lib/juryMode";

export default function JuryModeToggle() {
  const { jury, setJury, ready } = useJuryMode();

  return (
    <div className="jury-bar">
      <button
        type="button"
        className={`chip jury-toggle${jury ? " on" : ""}`}
        aria-pressed={jury}
        onClick={() => setJury(!jury)}
        title="Güven skorlarını kıyas tablosunda da göster (adres satırına ?juri=1 eklemek de aynı işi yapar)"
      >
        <span aria-hidden="true" className="jury-dot" />
        Jüri modu: {ready && jury ? "açık" : "kapalı"}
      </button>
      {jury && (
        <span className="small muted">
          Kıyas tablosunda güven skorları görünür. Denetim ekranları (Jüri Audit
          Paneli, Canlı Çıkarım, Şeffaf Skorlama) bu moddan bağımsız olarak
          skorları her hâlde gösterir.
        </span>
      )}
    </div>
  );
}
