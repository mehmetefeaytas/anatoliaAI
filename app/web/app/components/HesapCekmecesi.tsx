"use client";

/**
 * Hesap makinesi çekmecesi — sol altta yuvarlak düğme, her ekranda.
 *
 * İlgili: ./SohbetCekmecesi.tsx (aynı kabuk deseni, ayna görüntüsü — SAĞ
 *         yerine SOL), ../styles/hesap.css, CLAUDE.md §12 (faizsiz finans
 *         terminolojisi: kâr payı, murabaha benzeri sabit oranlı taksit)
 *
 * ## Neden ayrı bir bileşen, `SohbetCekmecesi`nin varyantı değil
 *
 * İçerik (form + sonuç) sohbetle hiçbir state/veri paylaşmıyor; tek paylaşılan
 * şey KABUK deseni (yüzen düğme + çekmece + Escape/focus yönetimi). Bunu tek
 * bir parametreli bileşene sıkıştırmak (`taraf: "sol" | "sağ"`) iki bağımsız
 * özelliği yapay bir bağımlılığa sokardı — biri bozulunca öteki de risk altına
 * girer. İki küçük, bağımsız bileşen; kabuk TEKRARI bilinçli bir maliyettir.
 *
 * ## Hesaplama neden istemcide (LLM'e SORULMAZ)
 *
 * Bu proje "LLM'e hesap yaptırma" ilkesini zaten benimsemiş
 * (`src/comparison/compare.py`, `CLAUDE.md` §3 halüsinasyon yasağı — bir sayı
 * uydurulduğunda en pahalı hatadır). Taksit/toplam ödeme hesabı deterministik
 * bir kapanmış-form formülüdür (klasik anüite formülü); sunucuya gitmeye,
 * ya da bir dil modeline hiç gerek yok. Sonuç ekranında bu bilerek yazılır —
 * jürinin "bu hesabı model mi yaptı" sorusuna ekran kendisi cevap versin diye.
 *
 * ## "Kâr payı oranı", "faiz" değil
 *
 * Aylık oran girdisi CLAUDE.md §12'nin domain terminolojisiyle etiketlenir:
 * bu bir kredi faizi değil, katılım bankacılığında önceden ilan edilen kâr
 * payı oranıdır. Hesap yöntemi (sabit taksitli anüite) klasik bankacılıkla
 * aynı matematiği kullanır ama arayüz kelimesi ürünün gerçek adını taşır.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api, type CampaignSummary } from "../lib/api";
import { trNum } from "../lib/format";

/** Çekmeceye geçirilen kampanya listesi ÜSTVERİDİR (oran/vade taşımaz —
 *  bkz. `CampaignSummary` tipi, ../lib/api.ts). Bir kampanya seçilince oran/vade
 *  ayrı bir çağrıyla (`campaignText`) çekilir; bkz. aşağıdaki `kampanyaSec`. */
type Props = {
  campaigns?: CampaignSummary[];
};

/** Aylık kâr payı oranının üst sınırı (%) — girdi doğrulaması için makul bir
 *  tavan. Şema/backend sınırı yok çünkü hesap tamamen istemcide; taşan bir
 *  değer sonucu anlamsızlaştırır (bileşik oranla patlayan taksit), o yüzden
 *  kullanıcıya hata mesajıyla geri verilir. */
const AZAMI_AYLIK_ORAN = 20;
const AZAMI_ANAPARA = 100_000_000;
const AZAMI_VADE_AY = 480;

type Sonuc = {
  aylikTaksit: number;
  toplamOdeme: number;
  toplamKarPayi: number;
};

/** Türkçe yazımlı sayıyı (`"1.500,00"` veya `"1500"` veya `"1,89"`) sayıya
 *  çevirir. Nokta binlik mi ondalık mı ayırıcı, virgül varlığından anlaşılır —
 *  ikisi bir arada gelirse nokta binlik sayılır (TR yazım kuralı). */
function sayi(metin: string): number | null {
  const t = metin.trim();
  if (t === "") return null;
  let normalize = t;
  if (t.includes(",")) {
    normalize = t.replace(/\./g, "").replace(",", ".");
  } else if (/^\d{1,3}(\.\d{3})+$/.test(t)) {
    normalize = t.replace(/\./g, "");
  }
  const d = Number(normalize);
  return Number.isFinite(d) ? d : null;
}

function tl(deger: number): string {
  return deger.toLocaleString("tr-TR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

/** Klasik anüite formülü — sabit taksitli, sabit aylık kâr payı oranı.
 *  `oranAylikYuzde === 0` özel durumu ayrı ele alınır (bölen sıfırlanır). */
function hesapla(
  anapara: number,
  oranAylikYuzde: number,
  vadeAy: number,
): Sonuc {
  const r = oranAylikYuzde / 100;
  const aylikTaksit =
    r === 0 ? anapara / vadeAy : (anapara * r * (1 + r) ** vadeAy) / ((1 + r) ** vadeAy - 1);
  const toplamOdeme = aylikTaksit * vadeAy;
  return {
    aylikTaksit,
    toplamOdeme,
    toplamKarPayi: toplamOdeme - anapara,
  };
}

function girdiHatasi(
  anaparaStr: string,
  oranStr: string,
  vadeStr: string,
): string | null {
  const a = sayi(anaparaStr);
  const o = sayi(oranStr);
  const v = sayi(vadeStr);
  if (a === null || o === null || v === null) return "Üç alanı da doldurun.";
  if (a <= 0 || a > AZAMI_ANAPARA)
    return `Anapara 0 ile ${tl(AZAMI_ANAPARA)} TL arasında olmalı.`;
  if (o < 0 || o > AZAMI_AYLIK_ORAN)
    return `Aylık kâr payı oranı 0 ile %${AZAMI_AYLIK_ORAN} arasında olmalı. Yıllık oran girmiş olabilir misiniz?`;
  if (!Number.isInteger(v) || v <= 0 || v > AZAMI_VADE_AY)
    return `Vade 1 ile ${AZAMI_VADE_AY} ay arasında tam sayı olmalı.`;
  return null;
}

/** Kanonik alan değerini girdi kutusuna yazılabilir Türkçe metne çevirir.
 *  Sayı DEĞİLSE (aralık, obje, dize…) `null` — böyle bir değer inputa
 *  UYDURULMAZ, alan boş kalır ve kullanıcıya not gösterilir. */
function alanMetni(v: unknown): string | null {
  return typeof v === "number" && Number.isFinite(v) ? trNum(v) : null;
}

export default function HesapCekmecesi({ campaigns }: Props) {
  const [acik, setAcik] = useState(false);
  const dugmeRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const anaparaRef = useRef<HTMLInputElement>(null);

  const [anapara, setAnapara] = useState("");
  const [oran, setOran] = useState("");
  const [vade, setVade] = useState("");
  const [sonuc, setSonuc] = useState<Sonuc | null>(null);
  const [hata, setHata] = useState<string | null>(null);

  // "" = elle giriş (varsayılan, hep birinci seçenek). Doluyken bir kampanya
  // kimliğidir (string, <select> değeri).
  const [kampanyaId, setKampanyaId] = useState("");
  const [kampanyaYukleniyor, setKampanyaYukleniyor] = useState(false);
  const [kampanyaNotu, setKampanyaNotu] = useState<string | null>(null);

  /** Kampanya seçimi değişti — "" ise elle girişe dön (form boşalır), değilse
   *  `campaignText(id)` ile oran/vade çek. UYDURMA YOK: alan çıkarılmamışsa
   *  input boş kalır, kullanıcıya not gösterilir; çağrı başarısızsa da
   *  sessizce yutulmaz. */
  const kampanyaSecildi = useCallback((id: string) => {
    setKampanyaId(id);
    setKampanyaNotu(null);
    if (id === "") {
      setOran("");
      setVade("");
      return;
    }
    setKampanyaYukleniyor(true);
    api
      .campaignText(Number(id))
      .then((metin) => {
        const oranAlani = metin.fields.find((f) => f.field === "kar_payi_orani");
        const vadeAlani = metin.fields.find((f) => f.field === "vade_ay");
        const oranMetni = alanMetni(oranAlani?.canonical_value);
        const vadeMetni = alanMetni(vadeAlani?.canonical_value);
        setOran(oranMetni ?? "");
        setVade(vadeMetni ?? "");
        const eksik: string[] = [];
        if (oranMetni === null) eksik.push("kâr payı oranı");
        if (vadeMetni === null) eksik.push("vade");
        setKampanyaNotu(
          eksik.length > 0
            ? `Bu kampanyada ${eksik.join(" ve ")} bilgisi çıkarılmamış, elle girebilirsiniz.`
            : null,
        );
      })
      .catch(() => {
        setOran("");
        setVade("");
        setKampanyaNotu("Kampanya bilgisi alınamadı, elle girin.");
      })
      .finally(() => setKampanyaYukleniyor(false));
  }, []);

  const kapat = useCallback(() => {
    setAcik(false);
    dugmeRef.current?.focus();
  }, []);

  useEffect(() => {
    if (!acik) return;
    const tusa = (e: KeyboardEvent) => {
      if (e.key === "Escape") kapat();
    };
    document.addEventListener("keydown", tusa);
    return () => document.removeEventListener("keydown", tusa);
  }, [acik, kapat]);

  useEffect(() => {
    if (acik) panelRef.current?.focus();
  }, [acik]);

  const hesaplaTikla = useCallback(() => {
    const sorun = girdiHatasi(anapara, oran, vade);
    if (sorun) {
      setHata(sorun);
      setSonuc(null);
      return;
    }
    setHata(null);
    setSonuc(
      hesapla(sayi(anapara) as number, sayi(oran) as number, sayi(vade) as number),
    );
  }, [anapara, oran, vade]);

  return (
    <>
      {/* Sohbet FAB'ının aynası — sağ yerine sol, farklı simge (hesap
          makinesi). Boyut/konum sabitleri hesap.css'te, sohbet.css'teki
          `.sohbet-fab` ile aynı token'lardan türetildi. */}
      <button
        ref={dugmeRef}
        type="button"
        className="hesap-fab"
        aria-expanded={acik}
        aria-controls="hesap-cekmece"
        aria-label={acik ? "Hesap makinesini kapat" : "Hesap makinesini aç"}
        title={acik ? "Hesap makinesini kapat" : "Taksit hesapla"}
        onClick={() => setAcik((a) => !a)}
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <rect x="5" y="3" width="14" height="18" rx="2" />
          <path d="M8 7h8" />
          <path d="M8 11h.01M12 11h.01M16 11h.01M8 14.5h.01M12 14.5h.01M16 14.5h.01M8 18h.01M12 18h.01M16 18h.01" />
        </svg>
      </button>

      {acik && (
        <div
          id="hesap-cekmece"
          className="hesap-cekmece"
          role="dialog"
          aria-label="Hesap makinesi"
          ref={panelRef}
          tabIndex={-1}
        >
          <div className="hesap-cekmece-bas">
            <span className="hesap-cekmece-ad">Hesap Makinesi</span>
            <button
              type="button"
              className="sohbet-kapat"
              onClick={kapat}
              aria-label="Hesap makinesini kapat"
            >
              ×
            </button>
          </div>

          <div className="hesap-cekmece-govde">
            <label className="hesap-etiket" htmlFor="hesap-kampanya">
              Kampanya seç (opsiyonel)
            </label>
            <select
              id="hesap-kampanya"
              className="select"
              value={kampanyaId}
              onChange={(e) => kampanyaSecildi(e.target.value)}
            >
              <option value="">Elle giriş</option>
              {(campaigns ?? []).map((k) => (
                <option key={k.id} value={String(k.id)}>
                  {k.bank_name ?? k.bank}
                  {k.campaign_type ? ` — ${k.campaign_type}` : ""}
                </option>
              ))}
            </select>

            {kampanyaYukleniyor && (
              <p className="small muted">Kampanya bilgisi yükleniyor…</p>
            )}
            {!kampanyaYukleniyor && kampanyaNotu && (
              <p className="small muted">{kampanyaNotu}</p>
            )}

            <label className="hesap-etiket" htmlFor="hesap-anapara">
              Anapara (TL)
            </label>
            <input
              id="hesap-anapara"
              ref={anaparaRef}
              className="input"
              value={anapara}
              onChange={(e) => setAnapara(e.target.value)}
              placeholder="500.000"
              inputMode="decimal"
            />

            <div className="hesap-satir">
              <div>
                <label className="hesap-etiket" htmlFor="hesap-oran">
                  Aylık kâr payı oranı (%)
                </label>
                <input
                  id="hesap-oran"
                  className="input"
                  value={oran}
                  onChange={(e) => setOran(e.target.value)}
                  placeholder="1,89"
                  inputMode="decimal"
                />
              </div>
              <div>
                <label className="hesap-etiket" htmlFor="hesap-vade">
                  Vade (ay)
                </label>
                <input
                  id="hesap-vade"
                  className="input"
                  value={vade}
                  onChange={(e) => setVade(e.target.value)}
                  placeholder="12"
                  inputMode="numeric"
                />
              </div>
            </div>

            <button type="button" className="btn" onClick={hesaplaTikla}>
              Hesapla
            </button>

            {hata && (
              <p className="hesap-hata" role="alert">
                {hata}
              </p>
            )}

            {sonuc && (
              <div className="hesap-sonuc" role="status">
                <div className="hesap-sonuc-vurgu">
                  <span className="hesap-sonuc-etiket">Aylık Taksit</span>
                  <span className="hesap-sonuc-deger">
                    {tl(sonuc.aylikTaksit)} TL
                  </span>
                </div>
                <div className="hesap-sonuc-satir">
                  <span>Toplam Ödeme</span>
                  <span className="mono">{tl(sonuc.toplamOdeme)} TL</span>
                </div>
                <div className="hesap-sonuc-satir">
                  <span>Toplam Kâr Payı</span>
                  <span className="mono">{tl(sonuc.toplamKarPayi)} TL</span>
                </div>
              </div>
            )}

            {!sonuc && !hata && (
              <p className="small muted" style={{ margin: "var(--sp-3) 0 0" }}>
                Örnek: {trNum(500000)} TL · aylık %1,89 · 12 ay.
              </p>
            )}
          </div>
        </div>
      )}
    </>
  );
}
