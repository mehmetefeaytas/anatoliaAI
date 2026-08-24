"use client";

/**
 * Tek alan kıyasının üstündeki ÖZET ŞERİT — iki dış kaynağın manşeti.
 *
 * İlgili: FinansmanOranPanel.tsx · KatilmaPanel.tsx (aynı verinin tam hâli)
 *         ../lib/api.ts (`finansmanOranlari`, `katilmaOranlari`)
 *
 * ## Niçin var
 *
 * Yayımlanan finansman oranları ve TKBB katılma oranları ayrı görünümlerde
 * duruyordu; varsayılan kıyas ekranını açan kişi onların VARLIĞINI bile
 * görmüyordu. Kullanıcı raporu (2026-08-25): *"Yayımlanan finansman oranları
 * ve Katılma hesabı oranları kısımlarında olan bilgiler Tek alan kıyası
 * kısmında da olsun."*
 *
 * ## Niçin MANŞET, tam tablo değil
 *
 * İki kaynak da kampanya korpusundan gelmiyor ve kanıt zincirleri farklı.
 * Tam tabloyu buraya koymak, üç ayrı kaynağı tek ekranda eşit ağırlıkta
 * gösterip "hepsi aynı ölçümdür" izlenimi verirdi. Şerit yalnız iki sayı ve
 * iki yön uyarısı taşıyor; ayrıntı kendi görünümünde.
 *
 * ## İki YÖN, iki ayrı satır
 *
 * Finansmanda DÜŞÜK oran iyi (ödediğiniz), katılmada YÜKSEK iyi
 * (kazandığınız). Aynı satırda yan yana yazmak, iki ters yönlü sayıyı
 * kıyaslanabilir gibi gösterirdi.
 */

import { api } from "../lib/api";
import { trNum } from "../lib/format";
import { useAsync } from "../lib/useAsync";

export default function OranSeridi() {
  const fin = useAsync(() => api.finansmanOranlari(), []);
  const kat = useAsync(() => api.katilmaOranlari({}), []);

  const f = fin.data?.rows?.[0] ?? null;
  const k = kat.data?.rows?.[0] ?? null;

  // Hiçbiri gelmediyse şerit hiç basılmıyor: boş bir kutu, ölçülmemiş bir şeyi
  // ölçülmüş gibi gösteren bir yer tutucudur.
  if (!f && !k) return null;

  return (
    <section className="card" aria-labelledby="oran-serit-baslik">
      <h3 id="oran-serit-baslik" style={{ marginTop: 0 }}>
        Kampanya dışı iki kaynak
      </h3>
      <p className="muted" style={{ marginTop: 0 }}>
        Aşağıdaki kıyas <b>kampanya belgelerinden</b> çıkarılan alanlara
        dayanıyor. Bankalar iki bilgiyi daha yayımlıyor ve onlar kampanya
        metninde bulunmuyor — bu yüzden ayrı sayılıyor, aynı tabloya
        karıştırılmıyor.
      </p>

      <ul style={{ marginBottom: 0 }}>
        {f && (
          <li>
            <b>Finansman oranı</b> (bankaların hesaplama araçlarından) — en
            düşük: <span className="mono">%{trNum(f.monthly_rate ?? 0)}</span>{" "}
            aylık, {f.bank_slug}
            {f.product_name ? ` · ${f.product_name}` : ""}.{" "}
            <span className="badge badge-warn">düşük oran avantajlı</span>{" "}
            <span className="muted">
              ({fin.data?.kapsam.kayit} kayıt · {fin.data?.kapsam.banka} banka;
              tamamı için görünüm anahtarından «Yayımlanan finansman oranları»)
            </span>
          </li>
        )}
        {k && (
          <li>
            <b>Katılma hesabı oranı</b> (TKBB haftalık yayını) — en yüksek:{" "}
            <span className="mono">%{trNum(k.annual_rate ?? 0)}</span>{" "}
            {k.bank_name ?? k.bank_slug}
            {k.term_months ? ` · ${k.term_months} ay` : ""}.{" "}
            <span className="badge badge-warn">yüksek oran avantajlı</span>{" "}
            <span className="muted">
              (tamamı için görünüm anahtarından «Katılma hesabı oranları»)
            </span>
          </li>
        )}
      </ul>
    </section>
  );
}
