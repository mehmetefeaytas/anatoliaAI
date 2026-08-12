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
 *
 * ## Neden zaman çerçevesi EN ÜSTTE
 *
 * Kapalılık bilgisi eskiden sözleşme kartının İÇİNDEydi ve "gelecek faz"
 * diyordu — bir takvim değil, bir erteleme gibi okunuyordu. Uçların ne zaman
 * açılacağı ("yakın dönem, iş birliği durumunda") ekranı okuyan kişinin ilk
 * gördüğü şey olmalı: aşağıdaki tabloları uygulanmış bir özellik sanarak
 * okumaya başlamamalı. Cümlenin kendisi burada YAZILMAZ, `/admin/plan`'dan
 * gelir — başlık ile gerekçe ayrı yerlerde yaşasa biri değiştiğinde diğeri
 * eskisini göstermeye devam ederdi.
 */

import { api } from "../lib/api";
import type { AdminPlan } from "../lib/api";
import { ErrorNotice, Loading } from "./ErrorNotice";
import { useAsync } from "../lib/useAsync";
import "../styles/zorvaka.css";

export default function AyarlarPanel() {
  const plan = useAsync<AdminPlan>(() => api.adminPlan(), []);

  if (plan.loading) return <Loading label="Ayarlar yükleniyor…" />;
  if (plan.error) return <ErrorNotice error={plan.error} />;
  if (!plan.data) return null;

  const { acik, baslik, durum_etiketi, sebep, bugunku_yol, uclar } = plan.data;

  return (
    <section>
      <div className={`card zaman-serit${acik ? "" : " zaman-kapali"}`}>
        <p className="zaman-etiket">{durum_etiketi}</p>
        <h2 className="zaman-baslik">{baslik}</h2>
        <p className="zaman-gerekce">{sebep}</p>
        <p className="small">
          Bugün geçerli yol: <code>{bugunku_yol}</code>
        </p>
      </div>

      <div className="card">
        <h2>Veri ekleme uçları</h2>
        <p className="small muted">
          Bankaların kampanyalarını ve finansal ürünlerini arayüzden eklemek
          için tasarlanan uçların sözleşmesi. Aşağıdaki tanım{" "}
          <b>sunucudan okunur</b>, bu ekranda sabit yazılmaz — uçlar
          değiştiğinde ekran da değişir. Uçlar bugün <b>kapalı</b>; tablolar
          uygulanmış bir özelliği değil, tanımlanmış bir sözleşmeyi anlatır.
        </p>
      </div>

      {uclar.map((uc) => (
        <div key={`${uc.yontem} ${uc.yol}`} className="card">
          {/* `row` (yatay) — `chip-group` DEĞİL: o sınıf dikey bir sütun ve
              rozetleri kart genişliğine yayıyordu. */}
          <div className="row">
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
