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
 *    kaybolmaz. Hidrasyon uyuşmazlığı `juryMode.tsx` deseniyle önlenir: okuma
 *    render sırasında değil, `useEffect` içinde yapılır.
 *
 * ## Sohbeti kapatmanın İKİ ayrı yolu (bu tur)
 *
 * Eskiden tek bir «Yeni sohbet» düğmesi vardı ve tek yaptığı şey geçmişi
 * geri dönülemez biçimde SİLMEKTİ. İki ayrı ihtiyacı tek düğmeye bindiriyordu
 * ve ikisini de kötü karşılıyordu: temiz bir sayfa isteyen kullanıcı önceki
 * sohbetini kaybediyor, gerçekten silmek isteyen kullanıcı ise yanlışlıkla
 * basma riskine karşı hiçbir koruma bulamıyordu.
 *
 * Artık iki düğme var ve ayrım tek cümleyle kurulur — **biri taşır, öteki
 * siler**:
 *
 *  - **«Yeni sohbet»** yürüyen sohbeti ikinci göze taşır ve boş bir sayfa
 *    açar. Hiçbir şey kaybolmaz: kenara alınan sohbet bir şeritte durur ve
 *    «Önceki sohbete dön» ile geri gelir (dönüş bir TAKASTIR, o an ekranda
 *    olan sohbet ikinci göze geçer — yani gidiş de dönüş de kayıpsızdır).
 *  - **«Sohbeti temizle»** her iki gözü de siler. Geri alınamaz tek işlem
 *    budur, bu yüzden yerinde bir onay adımı ister. Onay `window.confirm`
 *    ile değil, kartın içinde sorulur: tarayıcı diyaloğu sayfayı dondurur,
 *    stil taşımaz ve otomatik doğrulanamaz.
 *
 * Sohbet HAFIZASI da bu ayrımı izler: sunucuya gönderilen bağlam yalnız
 * ekrandaki turlardan üretilir (`baglamListesi`), kenara alınan sohbetten
 * DEĞİL. Yeni sohbet bu yüzden gerçekten yeni başlar — takip sorusu eski
 * sohbetin öznesini devralmaz.
 *
 * ## Güvenlik kapılarının görünürlüğü (bu tur)
 *
 * Sunucu her cevapta beş kapı + içerik karantinası koşturuyor ama bunun
 * ARAYÜZDE hiçbir izi yoktu: düzeltme notu ve feragatname cevabın gövdesine
 * karışıyor, düşürülen belge ise tamamen sessiz kalıyordu. "Kapılar gerçekten
 * çalışıyor mu" sorusunun cevabı ekranda kurulamıyordu.
 *
 * Gösterim üç kademeli ve kademeler bir kurala dayanıyor: **kullanıcı
 * cevabın metninden okuyamayacağı bir şey olduysa görünür.**
 *
 *  1. **Karantina — HER ZAMAN, jüri modu beklemez.** Korpustan bir belgenin
 *     talimat devralma işareti yüzünden düşürülmesi bir güvenlik OLAYIDIR;
 *     cevabın dayanağını değiştirir ve metinden okunamaz. Uyarı cevabın
 *     ÜSTÜNDE durur, çünkü cevabın neden daha az kaynağa dayandığını açıklar.
 *  2. **Sessiz yeniden yazma — HER ZAMAN.** Çıktı süzgeci bir terimi doğru
 *     karşılığıyla değiştirdiyse ekrandaki cümle artık modelin/belgenin
 *     yazdığı cümle değildir; bunu söylememek sessiz bir düzenleme olurdu.
 *  3. **Tam kapı tablosu — YALNIZ jüri modunda** (`?juri=1`, bkz.
 *     ../lib/juryMode.tsx). Terminoloji ve garanti kapıları neredeyse her
 *     oran sorusunda ateşlenir ve etkileri zaten cevabın içinde yazılıdır;
 *     her cevaba altı satırlık bir kapı tablosu basmak bilgi değil gürültü
 *     üretirdi. Jürinin ihtiyacı ise tam tersi: ateşlenmeyenleri de görmek.
 */

import { Fragment, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../lib/api";
import type { ChatResp, ChatSafety, ChatSource } from "../lib/api";
import { formatValue, trNum } from "../lib/format";
import { useJuryMode } from "../lib/juryMode";
import {
  baglamListesi,
  oku as oturumOku,
  okuOnceki as oturumOkuOnceki,
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
  /**
   * Ekrana özel hazır sorular.
   *
   * Sabit bir liste her ekranda aynı altı soruyu gösteriyordu; oysa kullanıcı
   * «En Avantajlı» ekranındayken bileşik skoru, banka sayfasındayken o
   * bankayı sormak istiyor. Çekmece açıldığı rotayı bilir ve listeyi ona göre
   * verir (bkz. ./SohbetCekmecesi.tsx `HAZIR_SORULAR`).
   */
  presets?: readonly string[];
  /**
   * Geniş yerleşim (tam sayfa) mı, dar mı (sağ çekmece).
   *
   * Dar hâlde başlık ve açıklama basılmaz — çekmecenin kendi başlığı var ve
   * 420px'de dört satırlık bir lede, sorulacak kutuyu katlamanın altına iter.
   */
  genis?: boolean;
};

export default function ChatPanel({
  onInspect,
  presets = PRESETS,
  genis = true,
}: Props) {
  const [q, setQ] = useState("");
  const [turlar, setTurlar] = useState<Tur[]>([]);
  // Kenara alınmış sohbet. Ekrana basılmaz, bağlama da girmez; yalnız şeritte
  // sayısıyla durur ve istendiğinde geri çağrılır.
  const [onceki, setOnceki] = useState<Tur[]>([]);
  // Temizleme onayı beklerken açık. Onay adımı olmadan tek tıkla iki sohbet
  // birden silinirdi.
  const [onayBekliyor, setOnayBekliyor] = useState(false);
  // «Yeni konu»ya basıldı ama henüz soru sorulmadı. Bayrak bir SONRAKİ tura
  // yazılır ve orada tüketilir.
  const [konuBasiBekliyor, setKonuBasiBekliyor] = useState(false);
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
    const kenara = oturumOkuOnceki();
    // Sayaç HER İKİ gözün üstünden geçer: önceki sohbete dönüldüğünde o
    // turlar yeniden listelenir ve kimlikleri çakışmamalıdır.
    sayacRef.current = sonrakiKimlik([...kayitli, ...kenara]) - 1;
    setTurlar(kayitli);
    setOnceki(kenara);
    setHazir(true);
  }, []);

  useEffect(() => {
    if (hazir) oturumYaz(turlar, onceki);
  }, [turlar, onceki, hazir]);

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
      setTurlar((t) => [
        ...t,
        // Konu sınırı bir SONRAKİ soruya yazılır: «Yeni konu»ya basmak
        // geçmişi değiştirmez, yalnız bundan sonrasının neyi devralacağını
        // belirler. Bayrak tüketilir — sınır tek turluktur.
        { id, soru: text, cevap: null, hata: null, konuBasi: konuBasiBekliyor },
      ]);
      if (konuBasiBekliyor) setKonuBasiBekliyor(false);

      try {
        const cevap = await api.chat(text, baglam);
        setTurlar((t) => t.map((x) => (x.id === id ? { ...x, cevap } : x)));
      } catch (e) {
        setTurlar((t) => t.map((x) => (x.id === id ? { ...x, hata: e } : x)));
      } finally {
        setBusy(false);
      }
    },
    [busy, turlar, konuBasiBekliyor],
  );

  /**
   * Bağlam devralmayı keser — geçmişi SİLMEDEN.
   *
   * «Yeni sohbet»ten farkı burada: o, sohbeti kenara alıp ekranı boşaltır.
   * Konu değiştirmek geçmişi silmeyi gerektirmiyor — kullanıcı önceki
   * soruları okumaya devam edebilmeli ama bot onları devralmamalı.
   *
   * Bağlam sızması bildirildi (konut finansmanı soruldu, taşıt finansmanı
   * cevabı geldi) ve bu düğme onun kullanıcı tarafındaki emniyet valfi: kod
   * tarafındaki devralma mantığı düzelene kadar bile işe yarar.
   *
   * Bayrak SONRAKİ soruya yazılır, o anki geçmişe değil: basmak yazılmış bir
   * şeyi değiştirmez, yalnız bundan sonrasını etkiler.
   */
  const yeniKonu = useCallback(() => {
    setKonuBasiBekliyor(true);
    alanRef.current?.focus();
  }, []);

  /**
   * Yürüyen sohbeti ikinci göze taşır ve boş sayfa açar.
   *
   * Kenara alınan sohbet SİLİNMEZ; ikinci gözde zaten bir sohbet varsa onun
   * yerini alır ve bu, şeritte tek bir sohbetin beklediği söylendiği için
   * sürpriz değildir. Boş bir sohbeti kenara almak anlamsız olurdu — düğme o
   * durumda zaten kapalıdır.
   */
  const yeniSohbet = useCallback(() => {
    setOnceki(turlar);
    setTurlar([]);
    setQ("");
    setOnayBekliyor(false);
    alanRef.current?.focus();
  }, [turlar]);

  /**
   * İki sohbetin yerini DEĞİŞTİRİR.
   *
   * Geri dönüş bir takastır, bir geri yükleme değil: ekrandaki sohbet ikinci
   * göze geçer. Böylece kullanıcı ileri geri gidip gelebilir ve hiçbir yönde
   * veri kaybetmez.
   */
  const oncekineDon = useCallback(() => {
    setTurlar(onceki);
    setOnceki(turlar);
    setQ("");
    setOnayBekliyor(false);
    alanRef.current?.focus();
  }, [onceki, turlar]);

  /** Onaylanmış temizleme: her iki göz de silinir. */
  const temizle = useCallback(() => {
    oturumTemizle();
    setTurlar([]);
    setOnceki([]);
    setQ("");
    setOnayBekliyor(false);
    alanRef.current?.focus();
  }, []);

  // GÖRÜNÜM tersine döner, durum listesi kronolojik kalır. Bağlam penceresi ve
  // saklama mantığı zaman sırasına dayandığı için ters çevirmeyi state'e
  // taşımak iki yerde birden sıralama düşünmeyi gerektirirdi.
  const gorunum = useMemo(() => [...turlar].reverse(), [turlar]);
  const sonCevap = turlar.length ? turlar[turlar.length - 1] : null;

  return (
    <section className={genis ? "card" : "sohbet-dar"}>
      {/* Dar hâlde başlık ve lede basılmaz: çekmecenin kendi başlığı var ve
          420px'de dört satırlık bir açıklama, soru kutusunu katlamanın altına
          iter — düzeltilen kusurun aynısını çekmecede tekrarlardı. */}
      {genis && (
        <>
          <h2>Chatbot</h2>
          <p className="lede">
            Sayısal/karşılaştırmalı sorular yapısal sorguya, koşul/açıklama
            soruları RAG&apos;e yönlendirilir. Hangi yolun kullanıldığı cevabın
            yanında yazar. Takip sorusu sorabilirsiniz: önceki turun alanı,
            süzgeci ve öznesi devralınır ve devralınan bağlam cevabın yanında
            rozet olarak yazar.
          </p>
        </>
      )}

      <div className="row" style={{ marginBottom: "var(--sp-3)" }}>
        {presets.map((p) => (
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
        <div className="row-tight">
          {/* «Yeni konu» ile «Yeni sohbet» BİLEREK ayrı: ilki bağlamı keser
              ve geçmişi ekranda bırakır, ikincisi sohbeti kenara alır. Tek
              düğmeye indirmek, konu değiştirmek isteyen kullanıcıyı geçmişini
              kaybetmeye zorlardı. */}
          <button
            type="button"
            className="btn-link"
            onClick={yeniKonu}
            disabled={busy || turlar.length === 0 || konuBasiBekliyor}
            title="Sonraki soru önceki turların alanını, süzgecini ve öznesini devralmaz; geçmiş ekranda kalır"
          >
            Yeni konu
          </button>
          <button
            type="button"
            className="btn-link"
            onClick={yeniSohbet}
            disabled={busy || turlar.length === 0}
            title="Bu sohbeti kenara alır, boş bir sayfa açar ve bağlam devralmayı sıfırlar; kenara alınan sohbet silinmez"
          >
            Yeni sohbet
          </button>
          <button
            type="button"
            className="btn-link"
            onClick={() => setOnayBekliyor(true)}
            disabled={busy || (turlar.length === 0 && onceki.length === 0)}
            title="Bu tarayıcıda saklanan sohbetlerin tamamını siler"
          >
            Sohbeti temizle
          </button>
        </div>
      </div>

      {/* Onay yerinde sorulur. `window.confirm` sayfayı dondurur, ekranın
          stilini taşımaz ve otomatik olarak doğrulanamaz. */}
      {onayBekliyor && (
        <div className="sohbet-onay" role="alert">
          <p className="sohbet-onay-metin">
            {onceki.length > 0
              ? "Yürüyen sohbet ve kenara alınan sohbet birlikte silinecek."
              : "Bu tarayıcıda saklanan sohbet silinecek."}{" "}
            İşlem geri alınamaz.
          </p>
          <div className="row-tight">
            <button type="button" className="btn btn-tehlike" onClick={temizle}>
              Evet, temizle
            </button>
            <button
              type="button"
              className="btn-link"
              onClick={() => setOnayBekliyor(false)}
            >
              Vazgeç
            </button>
          </div>
        </div>
      )}

      {/* Kenara alınan sohbetin varlığı GÖRÜNÜR olmalı: görünmeyen bir yedek,
          kullanıcı açısından silinmiş sayılır. */}
      {onceki.length > 0 && (
        <div className="sohbet-arsiv">
          <span>
            Kenara alınan sohbet: {trNum(onceki.length)} tur. Siz temizleyene
            kadar burada bekler ve cevaplara bağlam olarak karışmaz.
          </span>
          <button
            type="button"
            className="btn-link"
            onClick={oncekineDon}
            disabled={busy}
            title="İki sohbetin yerini değiştirir; hiçbiri silinmez"
          >
            Önceki sohbete dön
          </button>
        </div>
      )}

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

      {/* «Yeni konu»ya basıldı, soru henüz sorulmadı. Basmanın ekranda
          hiçbir izi olmasaydı kullanıcı basıp basmadığını bilemezdi. */}
      {konuBasiBekliyor && (
        <p className="sohbet-konu-bekliyor small" role="status">
          Sonraki soru yeni bir konu olarak sorulacak — önceki turların alanı,
          süzgeci ve öznesi devralınmayacak.
        </p>
      )}

      <div className="chat-log" aria-live="polite" aria-busy={busy}>
        {gorunum.map((t) => (
          <Fragment key={t.id}>
            <TurGorunumu tur={t} onInspect={onInspect} />
            {/* Ayırıcı turun ALTINA basılır çünkü liste ters sıralı: işaretli
                tur yeni konunun ilkidir, yani ekranda ondan AŞAĞIDA kalanlar
                eski konudur. Bu, botun bağlamı yönettiğini jüriye görsel
                olarak kanıtlayan tek işaret. */}
            {t.konuBasi && (
              <div className="sohbet-konu-ayirici" role="separator">
                <span>yeni konu{t.cevap?.field ? `: ${t.cevap.field}` : ""}</span>
              </div>
            )}
          </Fragment>
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
  const { jury } = useJuryMode();
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
            <YenidenYazmaRozeti guvenlik={tur.cevap.safety} />
          </div>

          {/* Karantina cevabın ÜSTÜNDE: cevabı okumadan önce, dayanağının
              eksildiğini bilmek gerekir. */}
          <KarantinaUyarisi
            guvenlik={tur.cevap.safety}
            onInspect={onInspect}
          />

          <Markdown metin={tur.cevap.answer} />

          <Kaynaklar cevap={tur.cevap} onInspect={onInspect} />

          {jury && <GuvenlikKapilari guvenlik={tur.cevap.safety} />}
        </div>
      )}
    </div>
  );
}

/**
 * Çıktı süzgecinin bir terimi SESSİZCE değiştirdiğini söyleyen rozet.
 *
 * Neden jüri modunu beklemiyor: ekrandaki cümle artık kaynağın yazdığı cümle
 * değildir. Bunu söylememek, kullanıcıya düzenlenmiş bir metni ham metin gibi
 * göstermek olurdu. Terimin kendisi BASILMAZ (sunucu da göndermez) — onu geri
 * yazmak, kapının az önce yaptığı işi geri almak demektir.
 *
 * Ateşlenmeyen kapılar burada gürültü üretmez: sayı sıfırsa rozet yoktur.
 */
function YenidenYazmaRozeti({ guvenlik }: { guvenlik?: ChatSafety }) {
  const adet = guvenlik?.rewritten_terms ?? 0;
  if (adet <= 0) return null;
  return (
    <span
      className="badge badge-warn"
      title="Katılım bankacılığında karşılığı olmayan terim, cevap basılmadan önce doğru karşılığıyla değiştirildi"
    >
      terminoloji düzeltildi ({trNum(adet)})
    </span>
  );
}

/**
 * KARANTİNA — düşürülen kaynak belgeler.
 *
 * Bu blok jüri modundan bağımsız görünür. Gerekçe: burada olan şey bir
 * güvenlik olayıdır — üçüncü taraf bir banka sayfasına gömülmüş talimat
 * cümlesi yakalanmış ve belge tümüyle kaynak kümesinden çıkarılmıştır. Cevap
 * o belgeye dayanmıyor; bunu söylememek, kullanıcıya eksik bir dayanağı tam
 * gibi göstermek olurdu.
 *
 * Belgenin METNİ gösterilmez, yalnız yakalanan işaret ve belgeye giden
 * denetim bağlantısı. Metni basmak, az önce düşürdüğümüz içeriği ekrana geri
 * koymak olurdu; incelemek isteyen belgeye gider.
 */
function KarantinaUyarisi({
  guvenlik,
  onInspect,
}: {
  guvenlik?: ChatSafety;
  onInspect?: (campaignId: number) => void;
}) {
  const kayitlar = guvenlik?.quarantined ?? [];
  if (kayitlar.length === 0) return null;

  return (
    <div className="karantina" role="alert">
      <p className="karantina-baslik">
        İçerik karantinası: {trNum(kayitlar.length)} belge cevabın dışında
        bırakıldı
      </p>
      <p className="karantina-gerekce small">
        Bu belgelerde, asistanın kurallarını devralmaya çalışan bir talimat
        metni bulundu. Kaynaklar bankaların kendi sayfalarından toplanır ve
        içerikleri bizim denetimimizde değildir; işaret taşıyan belge satır
        ayıklanarak değil, TÜMÜYLE düşürülür. Aşağıdaki cevap bu belgelere
        dayanmıyor.
      </p>
      <ul className="karantina-liste">
        {kayitlar.map((k, i) => (
          <li key={i} className="karantina-kayit">
            <span className="karantina-banka">{k.bank || "banka bilinmiyor"}</span>
            {k.isaret && (
              <span className="karantina-isaret" title="Belgede yakalanan parça">
                “{k.isaret}”
              </span>
            )}
            <span className="karantina-baglanti">
              {typeof k.source_url === "string" && k.source_url.trim() && (
                <a
                  className="btn-link"
                  href={k.source_url}
                  target="_blank"
                  rel="noreferrer noopener"
                  title={k.source_url}
                >
                  banka sayfası ↗
                </a>
              )}
              {typeof k.campaign_id === "number" && onInspect && (
                <button
                  type="button"
                  className="btn-link"
                  onClick={() => onInspect(k.campaign_id as number)}
                >
                  belgeye git (#{k.campaign_id})
                </button>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * Tam kapı tablosu — YALNIZ jüri modunda.
 *
 * Ateşlenmeyen kapılar da listelenir; bu listenin işi "hangi kapı ateşlendi"
 * kadar "hangi kapılar var" sorusuna da cevap vermektir. Yalnız ateşlenenleri
 * göstermek, sessiz kalan kapıların varlığını gizlerdi ve tam da o sessizlik
 * kanıtlanmak istenen şeydir.
 */
function GuvenlikKapilari({ guvenlik }: { guvenlik?: ChatSafety }) {
  if (!guvenlik?.gates?.length) return null;

  const atesli = guvenlik.gates.filter((g) => g.fired).length;
  const durduran = guvenlik.blocked_gate
    ? guvenlik.gates.find((g) => g.id === guvenlik.blocked_gate)
    : undefined;

  return (
    <details className="guvenlik-panel">
      <summary>
        Güvenlik kapıları — {trNum(atesli)}/{trNum(guvenlik.gates.length)}{" "}
        ateşlendi
      </summary>
      <p className="small muted guvenlik-ozet">
        Her kapı her soruda koşar. Ateşlenmeyen kapı da burada listelenir:
        sessiz kalması, çalışmaması demek değildir.
        {durduran && (
          <>
            {" "}
            Bu cevap <strong>{durduran.label}</strong> kapısında durduruldu ve
            veri sorgusu hiç yapılmadı.
          </>
        )}
        {guvenlik.abstained && !durduran && (
          <> Kaynak bulunamadığı için değer üretilmedi.</>
        )}
      </p>
      <ul className="kapi-listesi">
        {guvenlik.gates.map((g) => (
          <li
            key={g.id}
            className={g.fired ? "kapi-satiri kapi-atesli" : "kapi-satiri"}
          >
            <span className="kapi-durum" aria-hidden="true">
              {g.fired ? "●" : "○"}
            </span>
            <span className="kapi-ad">
              {g.label}
              <span className="kapi-etiket small faint">
                {g.fired ? " ateşlendi" : " ateşlenmedi"}
              </span>
            </span>
            <span className="kapi-aciklama small muted">{g.aciklama}</span>
          </li>
        ))}
      </ul>
    </details>
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
