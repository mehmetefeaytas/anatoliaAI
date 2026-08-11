"use client";

/**
 * Ayarlar — gelecek faz uçlarının sözleşmesi + bugünkü veri ekleme yolu.
 *
 * İlgili: src/api/gelecek.py (sözleşmenin TEK kaynağı), src/api/main.py
 *         ./TazelemePanel.tsx (bugün çalışan veri toplama yolu)
 *
 * ## Neden buradaki liste kodlanmıyor, sunucudan okunuyor
 *
 * Uç adresleri, gövde alanları ve kapalı olma gerekçesi `/admin/plan`'dan
 * geliyor. Aynı listeyi burada ikinci kez yazmak, bu projede altı kez
 * tekrarlayan «aynı bilgi iki yerde» kusuruna yeni bir örnek eklerdi: sunucu
 * sözleşmeyi değiştirdiğinde ekran eskisini göstermeye devam ederdi ve kimse
 * fark etmezdi.
 *
 * ## Neden burada form YOK
 *
 * Doldurulup gönderilebilen bir form, doldurulunca çalışacağını vaat eder.
 * Uçlar 501 döndüğü için o vaat tutulamaz; jüri ekranında "ekle"ye basıp
 * hiçbir şeyin olmadığını görmek, hiç form olmamasından kötüdür. Ekran
 * sözleşmeyi ve gerekçeyi gösterir; bugün işleyen yolu da adıyla söyler.
 */

import { api } from "../lib/api";
import type { AdminPlan } from "../lib/api";
import { ErrorNotice, Loading } from "./ErrorNotice";
import { useAsync } from "../lib/useAsync";

export default function AyarlarPanel() {
  const plan = useAsync<AdminPlan>(() => api.adminPlan(), []);

  if (plan.loading) return <Loading label="Ayarlar yükleniyor…" />;
  if (plan.error) return <ErrorNotice error={plan.error} />;
  if (!plan.data) return null;

  const { acik, sebep, bugunku_yol, uclar } = plan.data;

  return (
    <section>
      <div className="card">
        <h2>Veri ekleme uçları</h2>
        <p className="small muted">
          Bankaların kampanyalarını ve finansal ürünlerini arayüzden eklemek
          için tasarlanan uçların sözleşmesi. Aşağıdaki tanım{" "}
          <b>sunucudan okunur</b>, bu ekranda sabit yazılmaz — uçlar
          değiştiğinde ekran da değişir.
        </p>

        <div className={`notice ${acik ? "notice-ok" : "notice-warn"}`}>
          <b>{acik ? "Açık" : "Gelecek faz — bu sürümde kapalı"}</b>
          <p className="small" style={{ margin: "var(--sp-2) 0 0" }}>
            {sebep}
          </p>
          <p className="small" style={{ margin: "var(--sp-2) 0 0" }}>
            Bugün geçerli yol: <code>{bugunku_yol}</code>
          </p>
        </div>
      </div>

      {uclar.map((uc) => (
        <div key={`${uc.yontem} ${uc.yol}`} className="card">
          <div className="chip-group">
            <span className="badge badge-baglam">{uc.yontem}</span>
            <code>{uc.yol}</code>
            {!acik && <span className="badge badge-warn">501</span>}
          </div>
          <h3>{uc.baslik}</h3>
          <p className="small muted">{uc.ozet}</p>

          <div className="table-wrap">
            <table className="data stackable">
              <caption
                className="small muted"
                style={{ captionSide: "bottom", textAlign: "left" }}
              >
                {uc.baslik} ucunun gövde alanları.
              </caption>
              <thead>
                <tr>
                  <th scope="col">Alan</th>
                  <th scope="col">Tip</th>
                  <th scope="col">Zorunlu</th>
                  <th scope="col">Açıklama</th>
                </tr>
              </thead>
              <tbody>
                {uc.alanlar.map((alan) => (
                  <tr key={alan.ad}>
                    <td data-label="Alan">
                      <code>{alan.ad}</code>
                    </td>
                    <td data-label="Tip" className="muted">
                      {alan.tip}
                    </td>
                    <td data-label="Zorunlu">
                      {alan.zorunlu ? "evet" : "hayır"}
                    </td>
                    <td data-label="Açıklama" className="muted">
                      {alan.aciklama}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}
    </section>
  );
}
