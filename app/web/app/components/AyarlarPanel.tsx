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
 *
 * ## v2 «kanıt defteri» görsel dili — bu ekranda ne değişti
 *
 * Ekranın ADI «Ayarlar» ama içeriği bir ayar değil, bir SÖZLEŞME. Eskiden bu
 * ikilik yalnız açıklama paragrafında yazılıydı; biçim onu söylemiyordu:
 * uçlar rozetli birer kart başlığıydı ve `501` rozeti bir uyarı gibi
 * duruyordu. Üç şey değişti:
 *
 *  1. **Nötr not en üstte** (`.uc-not`, sol kenarda 3px `--line`). Bu panelin
 *     ne OLMADIĞINI söyler. Şerit uyarı renginde değil: uyarı rengi «bir şey
 *     ters gitti» der, oysa burada ters giden bir şey yok — tanım var,
 *     davranış yok.
 *  2. **Uç satırı** (`.uc-satir`): mono metot + yol solda, sans açıklama
 *     ortada, durum rozeti sağda. Hangisinin makine verisi olduğu yazı
 *     tipinden okunur (tokens.css, «ÜÇ SES»).
 *  3. **Kesikli çerçeveli rozet** (`.uc-durum-yok`): kesikli çerçeve bu
 *     panelde boşluğun biçimidir ve kapsama cetvelinin `bos` hâliyle aynı
 *     sözcüğü kullanır. Renk tek sinyal değil — rozetin metni de durumu
 *     söylüyor («gelecek faz · 501»).
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

        {/* Bu panelin ne OLMADIĞINI söyleyen NÖTR not. Uyarı değil: tanım var,
            davranış yok. */}
        <div className="uc-not">
          <strong className="uc-not-baslik">
            Bu bir ayar ekranı değil, bir sözleşme belgesi
          </strong>
          {/* Cümle `acik` durumuna BAĞLI: uçlar açıldığı gün «form yok, çünkü
              çalışmıyor» gerekçesi kendiliğinden yanlışa döner ve ekran
              eskisini söylemeye devam ederdi. */}
          <p className="uc-not-govde">
            {acik ? (
              <>
                Uçlar açık; aşağıdaki satırlar artık çalışan bir davranışı
                anlatıyor. Yine de bu ekran bir form taşımaz — veri ekleme yolu
                istemci tarafında değil, ucun kendisindedir.
              </>
            ) : (
              <>
                Doldurulup gönderilebilen hiçbir alan yok ve bilerek yok:
                doldurulabilen bir form, doldurulunca çalışacağını vaat eder.
                Uçlar bugün <b>501</b> döndüğü için o vaat tutulamaz.
              </>
            )}{" "}
            Aşağıdaki tanım <b>sunucudan okunur</b>, bu ekranda sabit yazılmaz —
            sözleşme değiştiğinde ekran da değişir.
          </p>
        </div>
      </div>

      {uclar.map((uc) => (
        <div key={`${uc.yontem} ${uc.yol}`} className="card">
          <h2>{uc.baslik}</h2>

          {/* Mono adres + sans açıklama + durum rozeti. Sıra korunur: önce
              makinenin söylediği, sonra sistemin söylediği, sonra durum. */}
          <div className="uc-satir">
            <code className="uc-adres">
              <span className="uc-yontem">{uc.yontem}</span>
              {uc.yol}
            </code>
            <p className="uc-ozet">{uc.ozet}</p>
            <span className={`uc-durum ${acik ? "uc-durum-var" : "uc-durum-yok"}`}>
              {acik ? "uygulandı" : "gelecek faz · 501"}
            </span>
          </div>

          <h3>gövde alanları</h3>
          <div className="table-wrap">
            <table className="data stackable">
              <caption
                className="small muted"
                style={{ captionSide: "bottom", textAlign: "left" }}
              >
                {uc.baslik} ucunun gövde alanları — tanımlı şema, çalışan bir
                form değil.
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
