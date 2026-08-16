"use client";

/**
 * Ürün Tablosu — şartname Senaryo-1'in beklenen çıktısı (s.11–12).
 *
 * İlgili: src/api/main.py `/urun-tablosu`
 *         src/comparison/compare.py «Şartname Senaryo-1 tablosu» bloğu
 *         ./ComparePanel.tsx (kardeş görünüm; görünüm anahtarı orada)
 *         ./urunTablosu.ts (tipler + istemci)
 *
 * ## Bu görünüm neden AYRI
 *
 * Şartname s.12 çözümün çıktısını bir tabloyla TARİF EDİYOR:
 *
 *     Banka | Ürün Türü | Kâr Payı Oranı | Vade | Kampanya Avantajı |
 *     Masraf Durumu | Kampanya Süresi
 *
 * Bu, kardeş görünümün (tek alan × çok banka) devriği: bir banka, yedi kolon.
 * İkisi birbirinin yerine geçmez. Tek-alan görünümü SIRALAR ve sıralamanın
 * denetimini (kanıt, güven, katman, sıra rozeti) taşır; bu tablo SIRALAMAZ,
 * bir bankanın bir üründeki tüm ilan ettiklerini tek satırda gösterir.
 * Tek-alan görünümü olduğu gibi duruyor — bu onun yerine değil yanına geldi.
 *
 * ## Boş hücre bir KUSUR DEĞİL, bir ölçüm
 *
 * Tablo bugün büyük ölçüde «Belirtilmemiş» doluyor ve bu gizlenmiyor:
 * ekranın başındaki doluluk sayacı «kaç hücrenin kaçı dolu»yu SUNUCUDAN
 * gelen ölçümle basıyor. Sayı burada hesaplanmıyor ve koda gömülü değil —
 * çıkarım katmanı geliştikçe değişiyor, donmuş bir sayı bir gün ekranda
 * gerçek olmayan bir iddia olurdu.
 *
 * Şartnamenin kendi tablosunda da 21 hücrenin 3'ü "Belirtilmemiş"tir; yani
 * seyreklik beklenen çıktının bir parçası, ondan sapma değil.
 *
 * ## Her dolu hücre KANITINI taşır
 *
 * Değerin yanındaki `¶` rozeti belgeyi yandan açar ve kaynak aralığı
 * vurgular — her yüzeydeki aynı jest (bkz. `KaynakDipnotu`). Güven ve katman
 * jüri modunda ayrıca görünür. Kanıtsız bir hücre bu projede bir iddia
 * olmaya yetmez.
 */

import { useState } from "react";
import type { FieldMeta } from "../lib/api";
import { avantajMetni, extractorClass, extractorLabel, formatValue, trNum } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useJuryMode } from "../lib/juryMode";
import ConfidenceBadge from "./ConfidenceBadge";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";
import KaynakDipnotu from "./KaynakDipnotu";
import { urunTablosuGetir, type TabloHucresi, type TabloSatiri } from "./urunTablosu";

type Props = {
  /** Alan listesi (`/fields`) — avantaj parçalarının ETİKET kaynağı. */
  fields: FieldMeta[];
  /** Kampanya türü süzgeci; boş dize «Tümü». */
  type: string;
  /** «Tümü» seçeneğiyle birlikte tüm türler. */
  campaignTypes: string[];
  onTypeChange: (type: string) => void;
};

/** Türü boş gelen satırların bölüm başlığı — `ComparePanel` ile aynı sözcük. */
const TURSUZ = "Türü belirlenemedi";

/** Satırları ürün ailesine böler; sunucunun sırası KORUNUR. */
function turlereBol(
  rows: TabloSatiri[],
): { tur: string; satirlar: TabloSatiri[] }[] {
  const bolumler = new Map<string, TabloSatiri[]>();
  for (const row of rows) {
    const tur = row.campaign_type || TURSUZ;
    const liste = bolumler.get(tur) ?? [];
    liste.push(row);
    bolumler.set(tur, liste);
  }
  return Array.from(bolumler, ([tur, satirlar]) => ({ tur, satirlar }));
}

export default function UrunTablosuPanel({
  fields,
  type,
  campaignTypes,
  onTypeChange,
}: Props) {
  const { jury } = useJuryMode();
  const tablo = useAsync(() => urunTablosuGetir(type || undefined), [type]);
  const [acikSatir, setAcikSatir] = useState<string | null>(null);

  /** Alan adı → Türkçe etiket. TEK kaynak `/fields`; burada sözlük tutulmaz. */
  const etiketle = (alan: string) =>
    fields.find((f) => f.field === alan)?.label ?? alan;

  const kolonlar = tablo.data?.columns ?? [];
  const doluluk = tablo.data?.doluluk ?? null;
  const bolumler = turlereBol(tablo.data?.rows ?? []);

  return (
    <div className="stack">
      <section className="card">
        <div className="cetvel-kabuk">
          <div className="cetvel-ust">
            <h2>Ürün Tablosu{type ? ` · ${type}` : ""}</h2>
            <span
              className="cetvel-alan"
              title="Şartname Senaryo-1, s.11–12: beklenen çıktı tablosu"
            >
              şartname s.12 · 7 kolon · banka başına tek satır
            </span>
          </div>

          {/* DOLULUK SAYACI — sayı sunucudan, çalışma anında ölçülmüş.
              «Seyrek» bir tabloyu seyrek olduğunu söylemeden göstermek,
              okuyucunun kusuru bizden önce keşfetmesi demekti. */}
          {doluluk !== null && doluluk.satir > 0 && (
            <div className="kapsama-sayaci rail rail-doktrin">
              <span className="kapsama-etiket">doluluk</span>
              <span className="kapsama-kesir">
                {trNum(doluluk.dolu)} / {trNum(doluluk.hucre)} hücre
              </span>
              <span className="kapsama-kirilim">
                {trNum(doluluk.satir)} satır × {trNum(doluluk.olculen_sutun)}{" "}
                ölçülen kolon · %{trNum(Math.round(doluluk.oran * 100))} dolu ·
                yedi kolonluk ölçüde {trNum(doluluk.tum_dolu)}/
                {trNum(doluluk.tum_hucre)}
              </span>
            </div>
          )}
        </div>

        <label className="row-tight" htmlFor="urun-tablosu-tur">
          <span className="mono muted">kampanya türü</span>
          <select
            id="urun-tablosu-tur"
            value={type}
            onChange={(e) => onTypeChange(e.target.value)}
          >
            <option value="">Tümü</option>
            {campaignTypes.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </label>

        <p className="small muted" style={{ maxWidth: "var(--measure)" }}>
          {tablo.data?.fairness_note ??
            "Her satır TEK bir kampanyadır; farklı kampanyalardan alınan " +
              "değerler aynı satırda birleştirilmez."}
        </p>

        {/* Sütun başına doluluk: hangi kolonun seyrek olduğunu SÖYLER.
            Tek bir yüzde, «kâr payı 16/66 ama masraf 44/66» ayrımını
            gizlerdi ve okuyucu boşluğun nerede olduğunu göremezdi. */}
        {doluluk !== null && doluluk.satir > 0 && (
          <p className="small faint">
            {kolonlar
              .filter((k) => k.olculur)
              .map((k) => {
                const s = doluluk.sutun_basina[k.key];
                return s ? `${k.label} ${trNum(s.dolu)}/${trNum(s.toplam)}` : null;
              })
              .filter(Boolean)
              .join(" · ")}
          </p>
        )}

        <div style={{ marginTop: "var(--sp-4)" }}>
          {tablo.loading && <Loading label="Ürün tablosu yükleniyor…" />}
          {!!tablo.error && <ErrorNotice error={tablo.error} />}
          {!tablo.loading && !tablo.error && tablo.data?.rows.length === 0 && (
            <EmptyNotice title="Bu süzgeçte kampanya yok">
              API yanıt verdi, ancak seçilen kampanya türünde hiç banka
              belgesi bulunamadı. Bu bir hata değil: sistem olmayan bir ürünü
              tabloya YAZMAZ.
            </EmptyNotice>
          )}

          {tablo.data && tablo.data.rows.length > 0 && (
            <div className="table-wrap">
              <table className="data stackable">
                <caption
                  className="small muted"
                  style={{
                    captionSide: "bottom",
                    textAlign: "left",
                    paddingTop: "var(--sp-2)",
                  }}
                >
                  Şartname s.12'nin yedi kolonu. Boş hücre «
                  {formatValue(null)}» yazar — sıfır ya da tahmin değil.
                  «Kampanya Avantajı» bir çıkarım alanı DEĞİLDİR: ödül, puan
                  ve indirim alanlarından derlenir, hiçbiri yoksa ücret
                  muafiyetinden; serbest metin üretilmez.{" "}
                  <span className="mono">¶</span> rozetine basınca belge
                  yandan açılır ve değerin kaynak metindeki aralığı
                  vurgulanır.
                </caption>
                <thead>
                  <tr>
                    {kolonlar.map((k) => (
                      <th key={k.key} scope="col">
                        {k.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {bolumler.map((bolum) => (
                    <FragmentBolum
                      key={bolum.tur}
                      bolum={bolum}
                      bolumSayisi={bolumler.length}
                      kolonlar={kolonlar}
                      jury={jury}
                      etiketle={etiketle}
                      acikSatir={acikSatir}
                      setAcikSatir={setAcikSatir}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

function FragmentBolum({
  bolum,
  bolumSayisi,
  kolonlar,
  jury,
  etiketle,
  acikSatir,
  setAcikSatir,
}: {
  bolum: { tur: string; satirlar: TabloSatiri[] };
  bolumSayisi: number;
  kolonlar: { key: string; label: string; olculur: boolean }[];
  jury: boolean;
  etiketle: (alan: string) => string;
  acikSatir: string | null;
  setAcikSatir: (a: string | null) => void;
}) {
  return (
    <>
      {/* Bölüm başlığı yalnız birden fazla tür varsa gerekli — tek tür
          seçiliyken gereksiz bir katman olurdu (ComparePanel ile aynı kural). */}
      {bolumSayisi > 1 && (
        <tr className="group-head">
          <td colSpan={kolonlar.length}>
            Kampanya türü: {bolum.tur} · {bolum.satirlar.length} banka
          </td>
        </tr>
      )}
      {bolum.satirlar.map((row) => {
        const anahtar = `${bolum.tur}-${row.bank}`;
        return (
          <Satir
            key={anahtar}
            row={row}
            kolonlar={kolonlar}
            jury={jury}
            etiketle={etiketle}
            acik={acikSatir === anahtar}
            onAc={() => setAcikSatir(acikSatir === anahtar ? null : anahtar)}
          />
        );
      })}
    </>
  );
}

function Satir({
  row,
  kolonlar,
  jury,
  etiketle,
  acik,
  onAc,
}: {
  row: TabloSatiri;
  kolonlar: { key: string; label: string; olculur: boolean }[];
  jury: boolean;
  etiketle: (alan: string) => string;
  acik: boolean;
  onAc: () => void;
}) {
  return (
    <>
      <tr>
        {kolonlar.map((k) => (
          <td key={k.key} data-label={k.label} className={k.olculur ? "num" : ""}>
            <Hucre
              hucre={row.cells[k.key]}
              campaignId={row.campaign_id}
              etiketle={etiketle}
            />
            {k.key === "bank" && row.other_count > 0 && (
              // Elenen kampanyalar gizlenmiyor, SAYILIYOR — satırın hangi
              // kampanyayı temsil ettiği belirsiz kalmasın.
              <div className="small faint">
                +{trNum(row.other_count)} kampanya daha
              </div>
            )}
            {k.key === "bank" && row.campaign_status === "expired" && (
              <div style={{ marginTop: "var(--sp-1)" }}>
                <span
                  className="badge badge-expired"
                  title="Kampanya sayfası kendi bitişini ilan ediyor ya da arşivde."
                >
                  süresi dolmuş
                </span>
              </div>
            )}
          </td>
        ))}
      </tr>
      {jury && (
        <tr>
          <td colSpan={kolonlar.length}>
            <button type="button" className="btn" onClick={onAc}>
              {acik ? "kanıtı gizle" : "kanıtı göster"}
            </button>
            {acik && (
              <KanitSeridi
                row={row}
                kolonlar={kolonlar}
                etiketle={etiketle}
              />
            )}
          </td>
        </tr>
      )}
    </>
  );
}

/** Tek hücre: değer + (varsa) kaynak rozeti. */
function Hucre({
  hucre,
  campaignId,
  etiketle,
}: {
  hucre: TabloHucresi | undefined;
  campaignId: number | null;
  etiketle: (alan: string) => string;
}) {
  // Sunucu bir kolonu göndermediyse (eski sürüm) hücre boş sayılır; jeton
  // yine aynıdır — burada ikinci bir «yok» biçimi uydurulmaz.
  if (!hucre) return <>{formatValue(null)}</>;

  if (hucre.sutun === "kampanya_avantaji") {
    return (
      <>
        <strong>{avantajMetni(hucre.parcalar, etiketle)}</strong>
        {hucre.parcalar.map((p, i) => (
          <KaynakRozeti key={`${p.field_name}-${i}`} hucre={p} campaignId={campaignId} />
        ))}
      </>
    );
  }

  return (
    <>
      <strong>{formatValue(hucre.value, hucre.field_name ?? undefined)}</strong>
      <KaynakRozeti hucre={hucre} campaignId={campaignId} />
    </>
  );
}

/**
 * Kaynak rozeti — yalnız ÖLÇÜLMÜŞ hücrelerde.
 *
 * Türetilmiş kolonların (Banka, Ürün Türü) ve boş hücrelerin gösterilecek bir
 * kaynağı yoktur; rozet basmak olmayan bir kanıta işaret etmek olurdu.
 */
function KaynakRozeti({
  hucre,
  campaignId,
}: {
  hucre: TabloHucresi;
  campaignId: number | null;
}) {
  if (hucre.bos || hucre.field_name === null || campaignId === null) return null;
  return (
    <KaynakDipnotu
      campaignId={campaignId}
      span={{
        span_start: hucre.span_start,
        span_end: hucre.span_end,
        span_scope: null,
        // İkisi de `boolean` (nullable DEĞİL) ve burada `false` veriliyor:
        // «doğrulandı» ile «çok anlamlı» iddialarını bu uç ölçmüyor, o yüzden
        // ikisini de İDDİA ETMİYORUZ. `true` yazmak ölçülmemiş bir doğrulama
        // beyan etmek olurdu; rozet doğrulanmamış varsayarak davranır.
        span_verified: false,
        span_ambiguous: false,
        window_start: null,
        window_end: null,
      }}
      rawValue={hucre.raw_value}
    />
  );
}

/** Jüri modunda satırın tüm kanıtı: ham ifade, güven, katman. */
function KanitSeridi({
  row,
  kolonlar,
  etiketle,
}: {
  row: TabloSatiri;
  kolonlar: { key: string; label: string; olculur: boolean }[];
  etiketle: (alan: string) => string;
}) {
  const olculen = kolonlar.filter((k) => k.olculur);
  const parcalar: { etiket: string; hucre: TabloHucresi }[] = [];
  for (const k of olculen) {
    const h = row.cells[k.key];
    if (!h || h.bos) continue;
    if (h.sutun === "kampanya_avantaji") {
      for (const p of h.parcalar) {
        parcalar.push({ etiket: etiketle(p.field_name ?? ""), hucre: p });
      }
      continue;
    }
    parcalar.push({ etiket: k.label, hucre: h });
  }

  if (parcalar.length === 0) {
    return (
      <p className="small faint">
        Bu satırda ölçülmüş hiçbir alan yok; gösterilecek kanıt da yok.
      </p>
    );
  }

  return (
    <ul className="stack">
      {parcalar.map(({ etiket, hucre }, i) => (
        <li key={`${hucre.field_name}-${i}`} className="small">
          <span className="mono muted">{etiket}</span>{" "}
          {hucre.raw_value ? (
            <span className="cetvel-ham">«{hucre.raw_value.trim()}»</span>
          ) : (
            <span className="mono faint">ham ifade kaydedilmemiş</span>
          )}{" "}
          <ConfidenceBadge value={hucre.confidence} source={null} />{" "}
          <span className={extractorClass(hucre.extractor as never)}>
            {extractorLabel(hucre.extractor as never)}
          </span>
        </li>
      ))}
    </ul>
  );
}
