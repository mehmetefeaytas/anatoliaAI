"use client";

/**
 * Çelişki tespiti (CLAUDE.md §18 yenilikçilik hedefi #2).
 *
 * İlgili: src/api/main.py `/contradictions`, `/contradictions/summary`,
 *         src/comparison/contradiction.py, ./KaynakDipnotu.tsx,
 *         ../styles/celiski.css
 *
 * ## Ekranın tezi: İKİ İDDİA DA BANKANIN KENDİ CÜMLESİ
 *
 * En güçlü örnek: banka «masrafsız» der, aynı belgede tahsis ücreti alanı
 * doludur. Bu ekranın yapmadığı şey, hangisinin doğru olduğuna karar vermek.
 * Sistem taraf tutmaz: iki ifadeyi BANKANIN sesiyle (serif, tırnak içinde),
 * eşit genişlikte, yan yana koyar ve ikisinin de karakter aralığını verir.
 * Kararı jüri — ya da bankanın kendisi — verir.
 *
 * Bu yüzden ekranda «banka yanlış söylüyor» diyen tek bir cümle ya da biçim
 * yok. Sistemin kendi sesi (sans) yalnız NEYİN çeliştiğini söyler.
 *
 * ## Neden --warn, neden --bad DEĞİL
 *
 * Çelişki bir çökme değil bir gözlemdir: tarama koşmuş, belgeyi okumuş ve
 * birbirini tutmayan iki ifade bulmuştur. `--bad` bu üründe arıza rengidir
 * (`ErrorNotice`, düşük güven, uydurma değer); onu buraya taşımak bankanın
 * metnini bir sistem hatası gibi göstermek olurdu. Renk tek sinyal de değil:
 * mono BÜYÜK HARF damga (`çelişki`) + sol şerit + tam açıklama cümlesi.
 *
 * ## Bulgu yoksa: NÖTR, kutlama değil
 *
 * Sıfır çelişki bir başarı DEĞİLDİR — aranan şey bulunamamış da olabilir. Bu
 * yüzden yeşil bir kutu basılmaz; nötr çerçeve + taranan kümenin ölçüsü
 * yazılır (`EmptyNotice`, kesik taban çizgisi + mono kesir).
 *
 * ## Alıntılar tel üzerinde YOK — ölçülmüş sınır
 *
 * `src/comparison/contradiction.py` her çelişkinin iki tarafını `Evidence`
 * olarak taşıyor (`raw_value`, `source_span`, `span_start/end`) ama
 * `src/api/main.py:_campaign_contradictions` yalnız `kind` / `detail` /
 * `fields` üçlüsünü sarıyor; `evidence` uçta düşüyor. Alıntı uydurulmadığı
 * için bu ekran onu BELGE METNİNDEN alır: kullanıcı kartı açtığında
 * `campaignText(id)` çekilir ve çelişen alanların kendi kayıtları eşleştirilir.
 * Kaydı olmayan taraf boş bırakılır (kesikli çip), doldurulmaz. Kalıcı çözüm
 * `evidence`i uçta göndermektir; istek raporda koordinatöre bırakıldı.
 */

import { useState } from "react";
import { api } from "../lib/api";
import type { CampaignFieldDetail, ContradictionRow } from "../lib/api";
import {
  contradictionLabel,
  extractorClass,
  extractorLabel,
  formatValue,
  trNum,
} from "../lib/format";
import { useAsync } from "../lib/useAsync";
import KaynakDipnotu from "./KaynakDipnotu";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import "../styles/celiski.css";

export default function ContradictionAlert({
  onInspect,
}: {
  onInspect?: (campaignId: number) => void;
}) {
  const list = useAsync(() => api.contradictions(), []);
  const sum = useAsync(() => api.contradictionSummary(), []);

  return (
    <section className="card">
      <h2>Çelişki Tespiti</h2>
      <p className="lede">
        Bir belge kendi içinde tutarsızsa yakalanır — en güçlü örnek «masrafsız»
        denip aynı metinde tahsis ücreti belirtilmesi. Tarama otomatiktir;
        aşağıdaki bulgular elle seçilmedi.
      </p>
      <p className="celiski-doktrin">
        Çelişkinin iki tarafı da bankanın kendi cümlesidir. Sistem hangisinin
        geçerli olduğunu söylemez: ikisini yan yana koyar, karakter aralıklarını
        verir ve kararı okuyana bırakır.
      </p>

      {sum.loading && <Loading label="Tarama kapsamı hesaplanıyor…" satir={1} />}
      {!!sum.error && <ErrorNotice error={sum.error} />}

      {/* Bu ekranın TEK kesri: kaç belgede çelişki bulundu. Sayılar sunucudan
          gelir; sıfır bulgu ayrıca bir renk giymez. */}
      {sum.data && (
        <div className="celiski-kapsam">
          <span className="celiski-kapsam-etiket">çelişki bulunan belge</span>
          <span className="celiski-kapsam-kesir">
            {trNum(sum.data.affected_campaigns)} /{" "}
            {trNum(sum.data.scanned_campaigns)}
          </span>
          <span className="celiski-kapsam-not">
            taranan: {trNum(sum.data.scanned_campaigns)} belge ·{" "}
            {trNum(sum.data.scanned_banks)} banka · bulgu:{" "}
            {trNum(sum.data.contradiction_count)}
          </span>
        </div>
      )}

      {list.loading && <Loading label="Çelişkiler getiriliyor…" satir={2} />}
      {!!list.error && <ErrorNotice error={list.error} />}

      {list.data?.length === 0 && !list.loading && (
        <EmptyNotice
          title="Bu külliyatta iç çelişki bulunamadı"
          kesir={
            sum.data
              ? `0 / ${trNum(sum.data.scanned_campaigns)} belge`
              : undefined
          }
        >
          Bu ne bir başarı ne bir arıza: tarama koştu, kapsam yukarıda yazılı ve
          bu kümede birbirini tutmayan iki ifade bulunamadı. Aranan şeyin
          bulunamamış olması da mümkündür — kuralın canlı çalıştığını görmek için{" "}
          <b>Zor Vaka Tezgâhı</b> sekmesindeki çelişkili belgeleri deneyin.
        </EmptyNotice>
      )}

      {list.data && list.data.length > 0 && (
        <ul className="celiski-liste">
          {list.data.map((c, i) => (
            <CelisikiKarti
              key={`${c.campaign_id}-${c.kind}-${i}`}
              satir={c}
              onInspect={onInspect}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

/**
 * Tek çelişki kartı.
 *
 * Alıntılar KATLI durur ve istek yalnız açılınca atılır: kartın kendisi zaten
 * çelişkinin ne olduğunu söylüyor, belge metni ise 1.774 belgeden biri.
 */
function CelisikiKarti({
  satir,
  onInspect,
}: {
  satir: ContradictionRow;
  onInspect?: (campaignId: number) => void;
}) {
  const [acik, setAcik] = useState(false);
  const belge = useAsync(
    () => (acik ? api.campaignText(satir.campaign_id) : Promise.resolve(null)),
    [acik, satir.campaign_id],
  );

  const baslik = contradictionLabel(satir.kind);
  // Sözlükte karşılığı yoksa etiket = kodun kendisi. O hâlde makine sesiyle
  // basılır; uydurma bir Türkçe başlık üretilmez.
  const kodKaldi = baslik === satir.kind;

  const alanlar = new Map<string, CampaignFieldDetail>(
    (belge.data?.fields ?? []).map((f) => [f.field, f]),
  );

  return (
    <li className="celiski-kart">
      <div className="celiski-bas">
        <span className="celiski-damga">çelişki</span>
        {kodKaldi ? (
          <span className="celiski-tur-kod">{satir.kind}</span>
        ) : (
          <span className="celiski-tur">{baslik}</span>
        )}
      </div>

      <p className="celiski-gerekce">{satir.detail}</p>

      <div className="celiski-kunye">
        <span>{satir.bank_name || satir.bank}</span>
        {satir.campaign_type && <span>· {satir.campaign_type}</span>}
        <span>· belge #{satir.campaign_id}</span>
        <span>· alan: {satir.fields.join(" ↔ ")}</span>
        {/* Provenans çipi — `source_url ↗` / `scraped_at:` ailesiyle aynı biçim
            (bkz. styles/kanit.css `.kanit-cip`). Kayıtlı değilse çip yine
            basılır: yokluk da bir bilgidir. */}
        {satir.source_url ? (
          <a
            className="kanit-cip kaynak-baglanti"
            href={satir.source_url}
            target="_blank"
            rel="noopener noreferrer"
            title={satir.source_url}
          >
            source_url ↗
          </a>
        ) : (
          <span className="kanit-cip">source_url: kaydedilmedi</span>
        )}
        {onInspect && (
          <>
            <span>·</span>
            <button
              type="button"
              className="btn-link"
              onClick={() => onInspect(satir.campaign_id)}
            >
              denetim panelinde aç
            </button>
          </>
        )}
      </div>

      <details
        className="celiski-taraflar"
        onToggle={(e) => setAcik(e.currentTarget.open)}
      >
        <summary>
          bankanın kendi ifadesi · {satir.fields.length} alan
        </summary>

        {belge.loading && (
          <Loading label="Belge metni getiriliyor…" satir={2} />
        )}
        {!!belge.error && <ErrorNotice error={belge.error} />}

        {belge.data && (
          <>
            <div className="celiski-taraf-izgara">
              {satir.fields.map((alan) => (
                <Taraf
                  key={alan}
                  alan={alan}
                  detay={alanlar.get(alan) ?? null}
                  campaignId={satir.campaign_id}
                />
              ))}
            </div>
            <p className="celiski-doktrin">
              {satir.fields.length > 1
                ? "Yukarıdaki ifadelerin hepsi bankanın kendi metninden, yazıldığı hâliyle okundu: aynı belge aynı konuda birden fazla şey söylüyor."
                : "Yukarıdaki ifade bankanın kendi metninden, yazıldığı hâliyle okundu."}{" "}
              Sistem hangisinin geçerli olduğunu değil, her ifadenin metnin
              neresinde durduğunu bildirir.
            </p>
          </>
        )}
      </details>
    </li>
  );
}

/**
 * Çelişkinin BİR tarafı.
 *
 * Ham ifade kayıtlı değilse boş bırakılır: kesikli çerçeveli mono çip, uydurma
 * bir alıntı değil. Aynı dil kapsama cetvelinin `bos` hâlinde de kullanılır.
 */
function Taraf({
  alan,
  detay,
  campaignId,
}: {
  alan: string;
  detay: CampaignFieldDetail | null;
  campaignId: number;
}) {
  const soz = detay?.source_span ?? detay?.raw_value ?? null;

  return (
    <div className="celiski-taraf">
      <span className="celiski-taraf-alan">{detay?.label ?? alan}</span>

      {soz ? (
        <p className="celiski-taraf-soz">«{soz.trim()}»</p>
      ) : (
        <span className="celiski-taraf-yok">ham ifade kayıtlı değil</span>
      )}

      {detay && (
        <span className="celiski-taraf-deger">
          {formatValue(detay.canonical_value, detay.field)}
        </span>
      )}

      <span className="celiski-taraf-eylem">
        {detay && (
          <span className={extractorClass(detay.extractor)}>
            {extractorLabel(detay.extractor)}
          </span>
        )}
        <KaynakDipnotu
          campaignId={campaignId}
          span={detay}
          rawValue={detay?.raw_value ?? null}
        />
      </span>
    </div>
  );
}
