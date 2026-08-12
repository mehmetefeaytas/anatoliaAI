"use client";

/**
 * Belge seçici — 1774 seçenekli açılır listenin yerini alan arama + süzgeç.
 *
 * İlgili: src/api/main.py (`GET /campaigns?q=&bank=&type=&belge_turu=&status=`),
 *         ../lib/api.ts (`campaignsSayfa`), ../lib/arama.ts, ../lib/useAsync.ts,
 *         ../styles/arama.css
 *
 * ## Ölçülmüş sorun
 *
 * Denetim panelinde belge seçimi tek bir açılır listeydi ve içinde korpusun
 * tamamı — 1774 seçenek — vardı. Kaydırmaktan başka yol yoktu; dahası
 * korpustaki 126 sözleşme/tarife belgesi ile 458 süresi dolmuş kampanya o
 * listede AYIRT EDİLEMİYORDU. İki bilgi de veride vardı, ekranda yoktu.
 *
 * Bu bileşen ikisini de görünür kılar: arama kutusu + dört süzgeç ekseni
 * (banka · kampanya türü · belge türü · geçerlilik) + rozetler.
 *
 * ## Süzme SUNUCUDA
 *
 * Kovaların anlamı veri katmanının kuralıdır — özellikle «damgasız», yani
 * geçerlilik damgası hiç konmamış belgeler. Bu, «geçerli» DEMEK DEĞİLDİR ve
 * korpusun büyük kısmı bu durumdadır. Kuralı TSX'e kopyalamak onu iki yerde
 * yaşatırdı; bu yüzden her süzgeç değişimi sunucuya gider.
 *
 * İstemcideki `lib/arama.ts` yalnızca EŞLEŞMEYİ VURGULAR — hangi satırın
 * kalacağına o karar vermez.
 *
 * ## Sayfalama dürüsttür
 *
 * Aynı anda 50 satır gösterilir ve altında kaç belgeden kaçının görüldüğü
 * yazar. Toplam sunucudan gelir; istemcide sayılan bir "toplam" yalnızca
 * indirilen dilimi sayardı ve listeyi tam sanmaya yol açardı.
 */

import { useEffect, useMemo, useState } from "react";
import { api } from "../lib/api";
import type { CampaignParams } from "../lib/api";
import { aramaTerimleri, vurgulariBul } from "../lib/arama";
import { useAsync } from "../lib/useAsync";
import { EmptyNotice, ErrorNotice, Loading } from "./ErrorNotice";

type Props = {
  /** Şu an seçili belge; listede işaretlenir. */
  seciliId: number | null;
  onSec: (id: number) => void;
  /** Bileşenin görünür başlığı. */
  baslik?: string;
};

/** Bir sayfada gösterilen satır sayısı. */
const SAYFA = 50;

/** Sunucuya gitmeden önce beklenen süre (ms) — komut paletiyle aynı. */
const GECIKME_MS = 250;

/** Belge türü süzgecinin kovaları. Değerler sunucunun sınıf etiketleridir. */
const BELGE_TURLERI = [
  { deger: "kampanya", etiket: "kampanya" },
  { deger: "sozlesme", etiket: "sözleşme" },
] as const;

/**
 * Geçerlilik süzgecinin kovaları.
 *
 * «Damgasız» ÜÇÜNCÜ bir kovadır, «geçerli» ile aynı şey değildir: damga hiç
 * konmamış demektir ve korpusun büyük kısmı bu durumdadır. İkisini birleştirmek,
 * hiç doğrulanmamış belgeler için doğrulanmış bir iddia uydurmak olurdu.
 */
const DURUMLAR = [
  { deger: "active", etiket: "geçerli" },
  { deger: "expired", etiket: "süresi dolmuş" },
  { deger: "damgasiz", etiket: "damgasız" },
] as const;

/** Eşleşen harfleri boyar. */
function Vurgulu({ metin, terimler }: { metin: string; terimler: string[] }) {
  const parcalar = useMemo(
    () => vurgulariBul(metin, terimler),
    [metin, terimler],
  );
  return (
    <>
      {parcalar.map((p, i) =>
        p.vurgulu ? (
          <mark key={i}>{metin.slice(p.bas, p.son)}</mark>
        ) : (
          <span key={i}>{metin.slice(p.bas, p.son)}</span>
        ),
      )}
    </>
  );
}

/** Tek eksenli çip kümesi; `null` = süzme yok. */
function CipKumesi({
  etiket,
  secili,
  secenekler,
  onSec,
}: {
  etiket: string;
  secili: string | null;
  secenekler: ReadonlyArray<{ deger: string; etiket: string }>;
  onSec: (deger: string | null) => void;
}) {
  return (
    <div className="chip-group">
      <span className="chip-group-label">{etiket}</span>
      <div className="belge-secici-cipler">
        <button
          type="button"
          className="chip"
          aria-pressed={secili === null}
          onClick={() => onSec(null)}
        >
          hepsi
        </button>
        {secenekler.map((s) => (
          <button
            key={s.deger}
            type="button"
            className="chip"
            aria-pressed={secili === s.deger}
            onClick={() => onSec(secili === s.deger ? null : s.deger)}
          >
            {s.etiket}
          </button>
        ))}
      </div>
    </div>
  );
}

export default function BelgeSecici({
  seciliId,
  onSec,
  baslik = "Belge seç",
}: Props) {
  const [sorgu, setSorgu] = useState("");
  const [gecikmeli, setGecikmeli] = useState("");
  const [bank, setBank] = useState<string | null>(null);
  const [tur, setTur] = useState<string | null>(null);
  const [belgeTuru, setBelgeTuru] = useState<string | null>(null);
  const [durum, setDurum] = useState<string | null>(null);
  const [limit, setLimit] = useState(SAYFA);

  useEffect(() => {
    const zaman = setTimeout(() => setGecikmeli(sorgu.trim()), GECIKME_MS);
    return () => clearTimeout(zaman);
  }, [sorgu]);

  // Süzgeç değişince sayfa başa döner: 150. satırdan devam etmek, kullanıcının
  // hiç görmediği bir listenin ortasında başlamak olurdu.
  useEffect(() => {
    setLimit(SAYFA);
  }, [gecikmeli, bank, tur, belgeTuru, durum]);

  // Süzgeç seçenekleri korpustan gelir, elle yazılmaz: yeni bir banka ya da
  // kampanya türü eklendiğinde liste kendiliğinden büyür.
  const bankalar = useAsync(() => api.banks(), []);
  const istatistik = useAsync(() => api.stats(), []);

  const liste = useAsync(
    () =>
      api.campaignsSayfa({
        q: gecikmeli || undefined,
        bank: bank ?? undefined,
        type: tur ?? undefined,
        belge_turu: (belgeTuru as CampaignParams["belge_turu"]) ?? undefined,
        status: (durum as CampaignParams["status"]) ?? undefined,
        limit,
      }),
    [gecikmeli, bank, tur, belgeTuru, durum, limit],
  );

  const terimler = useMemo(() => aramaTerimleri(gecikmeli), [gecikmeli]);
  const kayitlar = liste.data?.kayitlar ?? [];
  const toplam = liste.data?.toplam ?? null;

  const bankaSecenekleri = (bankalar.data ?? []).map((b) => ({
    deger: b.slug,
    etiket: b.name,
  }));
  const turSecenekleri = (istatistik.data?.campaign_types ?? []).map((t) => ({
    deger: t,
    etiket: t,
  }));

  return (
    <div className="belge-secici">
      <div className="belge-secici-arama">
        <label className="small muted" htmlFor="belge-secici-girdi">
          {baslik}
        </label>
        <input
          id="belge-secici-girdi"
          className="input"
          type="search"
          autoComplete="off"
          placeholder="Banka, kampanya türü veya özet içinde ara…"
          value={sorgu}
          onChange={(e) => setSorgu(e.target.value)}
        />
      </div>

      <div className="belge-secici-suzgecler">
        <CipKumesi
          etiket="Banka"
          secili={bank}
          secenekler={bankaSecenekleri}
          onSec={setBank}
        />
        <CipKumesi
          etiket="Kampanya türü"
          secili={tur}
          secenekler={turSecenekleri}
          onSec={setTur}
        />
        <CipKumesi
          etiket="Belge türü"
          secili={belgeTuru}
          secenekler={BELGE_TURLERI}
          onSec={setBelgeTuru}
        />
        <CipKumesi
          etiket="Geçerlilik"
          secili={durum}
          secenekler={DURUMLAR}
          onSec={setDurum}
        />
      </div>

      {liste.loading && <Loading label="Belgeler getiriliyor…" />}
      {!!liste.error && <ErrorNotice error={liste.error} />}

      {liste.data && kayitlar.length === 0 && (
        <EmptyNotice title="Bu süzgeçlerle belge yok">
          Süzgeçlerden birini gevşetin ya da aramayı kısaltın. Belgenin tam
          metninde arama yapılmaz; aranan alanlar banka adı, kampanya türü,
          özet ve adrestir.
        </EmptyNotice>
      )}

      {kayitlar.length > 0 && (
        <ul className="belge-secici-liste" aria-label="Belgeler">
          {kayitlar.map((k) => (
            <li key={k.id}>
              <button
                type="button"
                className="belge-secici-satir"
                aria-current={k.id === seciliId}
                onClick={() => onSec(k.id)}
              >
                <span className="belge-secici-bas">
                  <span className="belge-secici-no mono">#{k.id}</span>
                  <Vurgulu
                    metin={k.bank_name || k.bank}
                    terimler={terimler}
                  />
                  {k.campaign_type && (
                    <>
                      {" · "}
                      <Vurgulu metin={k.campaign_type} terimler={terimler} />
                    </>
                  )}
                  {k.belge_turu === "sozlesme" && (
                    <span className="badge badge-sozlesme">sözleşme</span>
                  )}
                  {k.campaign_status === "expired" && (
                    <span className="badge badge-expired">süresi dolmuş</span>
                  )}
                </span>
                {k.ozet && (
                  <span className="belge-secici-ozet small muted">
                    <Vurgulu metin={k.ozet} terimler={terimler} />
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}

      {kayitlar.length > 0 && (
        <div className="belge-secici-alt">
          <p className="small muted" role="status">
            {toplam === null
              ? `${kayitlar.length} belge gösteriliyor.`
              : `${toplam} belgeden ${kayitlar.length} tanesi gösteriliyor.`}
          </p>
          {toplam !== null && kayitlar.length < toplam && (
            <button
              type="button"
              className="btn-ghost"
              onClick={() => setLimit((n) => n + SAYFA)}
            >
              {SAYFA} belge daha göster
            </button>
          )}
        </div>
      )}
    </div>
  );
}
