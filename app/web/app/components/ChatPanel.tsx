"use client";

/**
 * Hibrit chatbot arayüzü (CLAUDE.md §5 — router'lı text-to-SQL + RAG).
 *
 * İlgili: src/api/main.py `POST /chat`, src/chatbot/router.py,
 *         ./ui/Markdown.tsx, ../lib/markdown.ts
 *
 * Dört iyileştirme:
 *  1. HAZIR SORU BUTONLARI — 4 dakikalık sunumda soru yazmak zaman kaybı ve
 *     yazım hatası riski. Altı soru router'ın iki yolunu da (yapısal sorgu ve
 *     RAG) kapsayacak şekilde seçildi; demo sürtünmesi sıfırlanır.
 *  2. KAYNAKLAR ham JSON dökümü değil, okunur bir tablo. Kaynağı gösterebilmek
 *     açıklanabilirlik iddiasının kanıtıdır; `<pre>{JSON}</pre>` bunu kanıt
 *     olmaktan çıkarıp gürültüye çeviriyordu.
 *  3. DENETLENEBİLİR BAĞLANTI — kaynak metin parçası tek başına yetmez: jüri
 *     "bu bilgiyi nereden aldın" diye sorduğunda bankanın kendi sayfasına
 *     (`source_url`) ve belgenin denetim ekranına (`campaign_id` →
 *     Jüri Audit Paneli) gidebilmek gerekir.
 *  4. BİÇİMLENDİRME ve GEÇMİŞ (bu turda) — aşağıda.
 *
 * ## Bu turda düzeltilen dört kusur
 *
 * a) **Markdown render edilmiyordu.** Cevap `<p>{resp.answer}</p>` ile düz
 *    metin basılıyordu, oysa markdown'ı sunucunun kendi şablonları üretiyor
 *    (`structured.py:125,136,137`; `safety.py`'de 12 satır). Sonuç: her yapısal
 *    cevapta ekranda ham `**Kuveyt Türk**` görünüyordu. Artık `Markdown`
 *    bileşeni render ediyor — yeni bağımlılık olmadan, ayrıştırıcı testli.
 *
 * b) **Enter `busy` kontrol etmiyordu.** Düğmede `disabled={busy}` vardı ama
 *    `onKeyDown`'da yoktu; istek uçarken Enter'a basmak ikinci (ve üçüncü)
 *    `POST /chat` başlatıyor, `finally` blokları yarışıyor ve son dönen cevap
 *    ekrana yazılıyordu. Yerel LLM gecikmesi saniyelerle ölçüldüğü için bu
 *    demoda gerçekleşebilir bir arızaydı.
 *
 * c) **Tek satır `<input>`.** Çok satırlı soru yazmak imkânsızdı ve
 *    Shift+Enter ayrımı yoktu. Artık otomatik büyüyen `<textarea>`:
 *    Enter gönderir, Shift+Enter yeni satır açar.
 *
 * d) **Her cevap bir öncekini siliyordu** (tek `resp` state'i). Jüri arka
 *    arkaya soru sorduğunda önceki cevap kayboluyordu; artık konuşma listesi
 *    tutuluyor.
 *
 * ## Kaynak satırındaki «AI Özeti»
 *
 * RAG pasajının `text` alanı belgenin TAMAMIDIR ve tabloya olduğu gibi
 * basılıyordu: tek bir kaynak satırı üç satır boyunca 4.000+ karakter ham
 * kampanya metni döküyor, ekran okunmaz hâle geliyordu. Korpusta belge başına
 * ortalama 4.744 karakter var; 1774 belgenin 1005'i 2.000 karakteri aşıyor.
 *
 * Artık satır, belgenin önceden üretilmiş özetini basar (`ozet`, ortalama 259
 * karakter). İki kural bu görünümü bağlar:
 *
 *  - **Özet uydurulmaz.** `ozet` boşsa «AI Özeti» etiketi BASILMAZ; ham metnin
 *    kırpılmış başlangıcı gösterilir ve bunun özet olmadığı yazılır. İlk
 *    cümleleri özet diye sunmak, üretilmemiş bir yeteneği üretilmiş gibi
 *    göstermek olurdu (src/summarize/ozet.py aynı yasağı sunucuda koyuyor).
 *  - **Ham metne erişim kaybolmaz.** Tam metin katlanır bir kutuda durur;
 *    denetlenebilirlik iddiası kısaltmayla feda edilemez.
 *
 * ## Bu turdaki üç değişiklik
 *
 * e) **YENİ TUR EN ÜSTTE.** Turlar eskiden yeniye diziliyordu; üçüncü sorudan
 *    sonra yeni cevabı görmek için aşağı kaydırmak gerekiyordu — soru kutusu
 *    ise yukarıda kalıyordu, yani göz sürekli iki uç arasında gidip geliyordu.
 *    Liste artık ters basılır (durum listesi kronolojik kalır; yalnız görünüm
 *    tersine döner, böylece bağlam penceresi ve saklama mantığı sadeleşir).
 *    Ekran okuyucu duyurusu KAYBOLMAZ: `aria-live` bölgesi eklenen düğümü
 *    konumundan bağımsız duyurur, ayrıca ayrı bir `role="status"` satırı
 *    durumu ("cevap hazır" / "cevap bekleniyor") açıkça bildirir.
 *
 * f) **SOHBET HAFIZASI.** Her istek son turların durum kayıtlarını da taşır
 *    (`lib/sohbetOturumu.ts`), böylece takip soruları çözülür: "Peki vade?"
 *    artık önceki cevabın öznesine sorulmuş sayılır. Devralınan bağlam
 *    ROZET olarak gösterilir — kullanıcı hangi bağlamla cevaplandığını
 *    görmeden bağlam devralmak, sessiz bir varsayım olurdu.
 *
 * g) **OTURUM KALICILIĞI.** Sohbet `localStorage`'ta yaşar; sayfa yenilenince
 *    kaybolmaz, «Yeni sohbet» ile temizlenir. Hidrasyon uyuşmazlığı
 *    `juryMode.tsx` deseniyle önlenir: okuma render sırasında değil,
 *    `useEffect` içinde yapılır.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import type { ChatResp, ChatSource } from "../lib/api";
import { formatValue, trNum } from "../lib/format";
import {
  baglamListesi,
  oku as oturumOku,
  sonrakiKimlik,
  temizle as oturumTemizle,
  yaz as oturumYaz,
  type Tur,
} from "../lib/sohbetOturumu";
import { ErrorNotice } from "./ErrorNotice";
import Markdown from "./ui/Markdown";

/**
 * Hazır sorular. İlk beşi `router.py` anahtar kelimeleriyle yapısal sorguya
 * (toplama/sıralama), sonuncusu RAG'e (koşul/açıklama) düşecek şekilde yazıldı.
 */
const PRESETS = [
  "Hangi bankada en düşük kâr payı oranı var?",
  "En yüksek vade veren banka hangisi?",
  "36 ay ve üzeri vade veren konut finansmanlarını listele",
  "En düşük tahsis ücreti hangi bankada?",
  "Masrafsız kampanya sunan bankalar hangileri?",
  "Konut finansmanı kampanyasının koşulları neler?",
];

const HANDLER_LABELS: Record<string, string> = {
  structured: "yapısal sorgu (text-to-SQL)",
  rag: "RAG (anlamsal arama)",
};

/**
 * Özeti OLMAYAN belgede tabloya basılacak ham metin payı.
 *
 * Sunucudaki `rag.ALINTI_KARAKTER` ile aynı büyüklük seçildi ki cevap gövdesi
 * ile kaynak satırı aynı uzunlukta okunsun. Bu bir kırpmadır, özetleme değil —
 * kullanıcıya da öyle söylenir.
 */
const HAM_ONIZLEME_KARAKTER = 320;

/** Ham metinden okunur bir önizleme — sözcük ortasından kesmez. */
function kirp(metin: string, sinir: number): string {
  const tek = metin.replace(/\s+/g, " ").trim();
  if (tek.length <= sinir) return tek;
  const kesik = tek.slice(0, sinir);
  const bosluk = kesik.lastIndexOf(" ");
  const govde = bosluk > sinir / 2 ? kesik.slice(0, bosluk) : kesik;
  return `${govde.replace(/[ ,;:.]+$/, "")}…`;
}

type Props = {
  /** Belgeyi Jüri Audit Paneli'nde açar (page.tsx `inspect` deseni). */
  onInspect?: (campaignId: number) => void;
};

export default function ChatPanel({ onInspect }: Props) {
  const [q, setQ] = useState("");
  const [turlar, setTurlar] = useState<Tur[]>([]);
  const [busy, setBusy] = useState(false);
  // Saklanan sohbet OKUNDU mu. Okunmadan yazmak, ilk render'daki boş listeyi
  // diske basıp geçmişi silerdi.
  const [hazir, setHazir] = useState(false);
  const alanRef = useRef<HTMLTextAreaElement>(null);
  const sayacRef = useRef(0);

  // Otomatik yükseklik: içerik büyüdükçe alan büyür, `max-height`e kadar.
  useEffect(() => {
    const el = alanRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [q]);

  // Hidrasyon: sunucu ve ilk istemci render'ı AYNI (boş liste) olmalı; gerçek
  // değer mount sonrası okunur (juryMode.tsx ile aynı desen).
  useEffect(() => {
    const kayitli = oturumOku();
    sayacRef.current = sonrakiKimlik(kayitli) - 1;
    setTurlar(kayitli);
    setHazir(true);
  }, []);

  useEffect(() => {
    if (hazir) oturumYaz(turlar);
  }, [turlar, hazir]);

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      // Yarışan istek YOK: `busy` burada da kontrol edilir, yalnız düğmede değil.
      if (!text || busy) return;

      const id = (sayacRef.current += 1);
      // Kutu BOŞALTILIR. Eskiden `setQ(text)` ile soru kutuda kalıyordu:
      // kullanıcı ikinci soruyu yazmaya başlayınca eskisinin ARDINA ekleniyor,
      // Enter'a basınca da aynı soru yeniden gönderiliyordu. Ekranda hiçbir
      // şey değişmediği için "ikinci soru sorulamıyor, sayfayı yenilemek
      // gerekiyor" diye görünüyordu.
      setQ("");
      setBusy(true);
      // Bağlam, isteği AÇMADAN önce o anki geçmişten okunur: yeni turu
      // ekledikten sonra okumak, cevabı henüz gelmemiş turu da listeye
      // sokardı (bağlamı boş, faydası yok, gövdesi şişik).
      const baglam = baglamListesi(turlar);
      setTurlar((t) => [...t, { id, soru: text, cevap: null, hata: null }]);

      try {
        const cevap = await api.chat(text, baglam);
        setTurlar((t) => t.map((x) => (x.id === id ? { ...x, cevap } : x)));
      } catch (e) {
        setTurlar((t) => t.map((x) => (x.id === id ? { ...x, hata: e } : x)));
      } finally {
        setBusy(false);
      }
    },
    [busy, turlar],
  );

  const yeniSohbet = useCallback(() => {
    oturumTemizle();
    setTurlar([]);
    setQ("");
    alanRef.current?.focus();
  }, []);

  // GÖRÜNÜM tersine döner, durum listesi kronolojik kalır. Bağlam penceresi ve
  // saklama mantığı zaman sırasına dayandığı için ters çevirmeyi state'e
  // taşımak iki yerde birden sıralama düşünmeyi gerektirirdi.
  const gorunum = useMemo(() => [...turlar].reverse(), [turlar]);
  const sonCevap = turlar.length ? turlar[turlar.length - 1] : null;

  return (
    <section className="card">
      <h2>Chatbot</h2>
      <p className="lede">
        Sayısal/karşılaştırmalı sorular yapısal sorguya, koşul/açıklama soruları
        RAG&apos;e yönlendirilir. Hangi yolun kullanıldığı cevabın yanında yazar.
        Takip sorusu sorabilirsiniz: önceki turun alanı, süzgeci ve öznesi
        devralınır ve devralınan bağlam cevabın yanında rozet olarak yazar.
      </p>

      <div className="row" style={{ marginBottom: "var(--sp-3)" }}>
        {PRESETS.map((p) => (
          <button
            key={p}
            type="button"
            className="chip"
            disabled={busy}
            onClick={() => ask(p)}
          >
            {p}
          </button>
        ))}
      </div>

      <div className="row-tight" style={{ alignItems: "flex-end" }}>
        <textarea
          ref={alanRef}
          rows={1}
          className="textarea textarea-auto grow"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            // Enter gönderir, Shift+Enter yeni satır açar.
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              ask(q);
            }
          }}
          placeholder="ör. Hangi bankada en düşük kâr payı var? (Shift+Enter: yeni satır)"
          aria-label="Chatbot sorusu"
          aria-describedby="chat-ipucu"
        />
        <button type="button" className="btn" onClick={() => ask(q)} disabled={busy}>
          {busy ? "…" : "Sor"}
        </button>
      </div>
      <div className="chat-araclar">
        <p id="chat-ipucu" className="small faint" style={{ margin: 0 }}>
          Enter gönderir · Shift+Enter yeni satır · en yeni cevap en üstte
        </p>
        <button
          type="button"
          className="btn-link"
          onClick={yeniSohbet}
          disabled={busy || turlar.length === 0}
          title="Sohbeti temizler ve bağlam devralmayı sıfırlar"
        >
          Yeni sohbet
        </button>
      </div>

      {/* Durum satırı ekran okuyucu içindir. Turlar ters sırada basıldığı için
          «yeni bir şey eklendi» bilgisi tek başına konumdan okunamaz; durum
          burada AÇIKÇA söylenir. */}
      <p className="chat-durum" role="status">
        {busy
          ? "Cevap bekleniyor."
          : sonCevap?.cevap
            ? "Cevap hazır, listenin en üstünde."
            : ""}
      </p>

      <div className="chat-log" aria-live="polite" aria-busy={busy}>
        {gorunum.map((t) => (
          <TurGorunumu key={t.id} tur={t} onInspect={onInspect} />
        ))}
      </div>

      {hazir && turlar.length === 0 && (
        <p className="chat-bos small muted">
          Sohbet boş. Bir soru sorun; sohbet bu tarayıcıda saklanır ve sayfayı
          yenileseniz de kaybolmaz.
        </p>
      )}
    </section>
  );
}

function TurGorunumu({
  tur,
  onInspect,
}: {
  tur: Tur;
  onInspect?: (campaignId: number) => void;
}) {
  const bekliyor = !tur.cevap && !tur.hata;

  return (
    <div className="chat-turn">
      <div className="chat-q">{tur.soru}</div>

      {bekliyor && (
        <div className="chat-a">
          {/* İskelet gösterge: eskiden yükleniyor durumu yalnız düğme
              yazısındaki "…" ile belliydi; ekran okuyucu ve hızlı kullanıcı
              için "bir şey oluyor mu" belirsizdi. */}
          <div className="skeleton" role="status">
            <span />
            <span />
            <span />
          </div>
        </div>
      )}

      {!!tur.hata && <ErrorNotice error={tur.hata} />}

      {tur.cevap && (
        <div className="chat-a">
          <div className="row" style={{ marginBottom: "var(--sp-2)" }}>
            <span className="badge">
              {HANDLER_LABELS[tur.cevap.handler] ?? tur.cevap.handler}
            </span>
            {tur.cevap.field && (
              <span className="badge" title="Router'ın çıkardığı alan">
                alan: <span className="mono">{tur.cevap.field}</span>
              </span>
            )}
            {/* Devralınan bağlam GÖRÜNÜR olmalı: kullanıcı sormadığı bir
                süzgeçle cevaplandığını göremezse, cevabı yanlış okur. */}
            {(tur.cevap.inherited ?? []).map((d, i) => (
              <span
                key={`${d.kind}-${i}`}
                className="badge badge-baglam"
                title="Bu bilgi sizin bu turdaki sorunuzda yoktu, önceki turdan devralındı"
              >
                önceki sorudan: {d.label}
              </span>
            ))}
            <SozellestirmeRozeti bilgi={tur.cevap.verbalize} />
          </div>

          <Markdown metin={tur.cevap.answer} />

          <Kaynaklar cevap={tur.cevap} onInspect={onInspect} />
        </div>
      )}
    </div>
  );
}

/**
 * Cevabın LLM ile sözelleştirilip sözelleştirilmediği.
 *
 * Üç hâl vardır ve ikisi kullanıcıya söylenir:
 *
 *  - LLM hiç denenmedi (kapalı / yok / liste cevabı) → rozet YOK. Şablon
 *    cevap zaten varsayılandır; her cevabın yanına "şablon" yazmak gürültü
 *    olurdu.
 *  - Denendi ve UYGULANDI → «LLM ile sözelleştirildi».
 *  - Denendi ama doğrulama kapısı REDDETTİ (uydurulmuş sayı, kaybolan banka
 *    adı, zaman aşımı) → «şablon cevap» + gerekçe. Bu hâli gizlemek, kapının
 *    çalıştığını gizlemek olurdu; oysa kapının düşmesi iyi haberdir.
 */
function SozellestirmeRozeti({ bilgi }: { bilgi?: ChatResp["verbalize"] }) {
  if (!bilgi?.attempted) return null;
  if (bilgi.applied) {
    return (
      <span
        className="badge badge-llm"
        title="Olgular şablon cevapla birebir doğrulandı; LLM yalnız yeniden ifade etti"
      >
        LLM ile sözelleştirildi
      </span>
    );
  }
  return (
    <span
      className="badge badge-warn"
      title={`Doğrulama kapısı LLM çıktısını reddetti: ${bilgi.reason ?? "bilinmiyor"}`}
    >
      şablon cevap
    </span>
  );
}

function Kaynaklar({
  cevap,
  onInspect,
}: {
  cevap: ChatResp;
  onInspect?: (campaignId: number) => void;
}) {
  if (!cevap.sources?.length) {
    return (
      <p className="small muted" style={{ marginTop: "var(--sp-3)" }}>
        Bu cevap için kaynak satırı döndürülmedi.
      </p>
    );
  }

  return (
    <>
      <h3>Kaynaklar ({cevap.sources.length})</h3>
      <p className="small muted" style={{ margin: "0 0 var(--sp-2)" }}>
        Her satır, cevabın dayandığı belgeye götürür: bankanın kendi sayfası ve
        belgenin denetim ekranı. Uzun belgelerde önce AI Özeti gösterilir; ham
        metnin tamamı satırın içinde açılır.
      </p>
      <div className="table-wrap">
        <table className="data stackable">
          <thead>
            <tr>
              <th scope="col">Banka</th>
              <th scope="col">Değer</th>
              <th scope="col">AI Özeti / kaynak metin</th>
              <th scope="col">Kaynak</th>
            </tr>
          </thead>
          <tbody>
            {cevap.sources.map((s, i) => (
              <tr key={i}>
                <td data-label="Banka">
                  {typeof s.bank === "string" ? s.bank : "—"}
                </td>
                <td data-label="Değer" className="num">
                  {"value" in s ? formatValue(s.value, cevap.field ?? undefined) : "—"}
                </td>
                <td data-label="AI Özeti / kaynak metin" className="small muted">
                  <Parca kaynak={s} />
                </td>
                <td data-label="Kaynak">
                  <SourceLinks source={s} onInspect={onInspect} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

/** Kaynak kaydındaki ilk dolu ham metin alanı (RAG pasajları farklı adlar kullanır). */
function hamMetin(kaynak: ChatSource): string {
  for (const key of ["text", "chunk_text", "passage", "detail"]) {
    const v = kaynak[key];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}

/**
 * Kaynak satırının gövdesi: varsa AI Özeti, yoksa kırpılmış ham metin.
 *
 * Sıra bilinçli. `source_span` yapısal sorgu yolunun dar kanıt penceresidir
 * (değerin çıkarıldığı yer) ve özet ondan daha iyi bir kanıt DEĞİLDİR; bu
 * yüzden özet yalnızca elde dar pencere yokken, yani belgenin tamamı kaynak
 * olarak geldiğinde öne geçer.
 *
 * Hiçbir alan yoksa eskiden `JSON.stringify(s)` basılıyordu — jüri ekranına
 * ham JSON dökmek, kaynağı kanıt olmaktan çıkarıp gürültüye çevirir. Artık
 * bilginin yokluğu SÖYLENİR.
 */
function Parca({ kaynak }: { kaynak: ChatSource }) {
  const span = typeof kaynak.source_span === "string" ? kaynak.source_span.trim() : "";
  if (span) return <>…{span}…</>;

  const ham = hamMetin(kaynak);
  const ozet = typeof kaynak.ozet === "string" ? kaynak.ozet.trim() : "";

  if (ozet) {
    return (
      <div className="kaynak-govde">
        <span className="badge badge-llm">AI Özeti</span>
        <p className="kaynak-ozet">{ozet}</p>
        {ham && <HamMetin metin={ham} />}
      </div>
    );
  }

  if (ham) {
    return (
      <div className="kaynak-govde">
        {/* Özet YOK: etiket bunu söyler. «AI Özeti» rozeti burada basılmaz,
            çünkü aşağıdaki metin özet değil, belgenin ilk cümleleridir. */}
        <span className="badge">AI Özeti yok</span>
        <p className="kaynak-ozet-yok">
          Bu belge için AI Özeti üretilmedi. Aşağıdaki satır özet değil, ham
          metnin kırpılmış başlangıcıdır.
        </p>
        <p className="kaynak-onizleme">{kirp(ham, HAM_ONIZLEME_KARAKTER)}</p>
        <HamMetin metin={ham} />
      </div>
    );
  }

  return <span className="faint">kaynak metin parçası döndürülmedi</span>;
}

/**
 * Ham metnin tamamı — katlanmış, ama erişilebilir.
 *
 * Kısaltma denetlenebilirliği azaltmamalı: jüri «kırptın, gerisinde ne var»
 * diye sorabilmeli ve cevap aynı satırda, ağ isteği olmadan açılmalı. Yerel
 * `<details>` kullanılır; yeni bağımlılık yok, klavye ve ekran okuyucu desteği
 * tarayıcıdan gelir.
 */
function HamMetin({ metin }: { metin: string }) {
  return (
    <details className="kaynak-ham">
      <summary>Ham metnin tamamı ({trNum(metin.length)} karakter)</summary>
      <p className="kaynak-ham-govde">{metin}</p>
    </details>
  );
}

/**
 * Kaynak bağlantıları — alan eksikse SESSİZCE atlanır, uydurulmaz.
 *
 * `source_url` ve `campaign_id` API sözleşmesinde opsiyoneldir; ikisi de yoksa
 * satır "bağlantı yok" der. Bu, bilgiyi gizlemek değil, elimizde denetlenebilir
 * bir bağlantı OLMADIĞINI söylemektir.
 */
function SourceLinks({
  source,
  onInspect,
}: {
  source: ChatSource;
  onInspect?: (campaignId: number) => void;
}) {
  const url = typeof source.source_url === "string" ? source.source_url.trim() : "";
  const id =
    typeof source.campaign_id === "number" && Number.isFinite(source.campaign_id)
      ? source.campaign_id
      : null;

  if (!url && id === null) {
    return (
      <span className="small faint" title="API bu kaynak için bağlantı döndürmedi">
        bağlantı yok
      </span>
    );
  }

  return (
    <div className="row-tight" style={{ flexWrap: "wrap" }}>
      {url && (
        <a
          className="btn-link"
          href={url}
          target="_blank"
          rel="noreferrer noopener"
          title={url}
        >
          banka sayfası ↗
        </a>
      )}
      {id !== null && onInspect && (
        <button type="button" className="btn-link" onClick={() => onInspect(id)}>
          belgeye git (#{id})
        </button>
      )}
      {id !== null && !onInspect && <span className="small faint mono">#{id}</span>}
    </div>
  );
}
