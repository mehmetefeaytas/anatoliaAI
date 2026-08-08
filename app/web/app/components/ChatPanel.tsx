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
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { ChatResp, ChatSource } from "../lib/api";
import { formatValue } from "../lib/format";
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

/** Ekranda duran tek bir soru-cevap turu. */
type Tur = {
  id: number;
  soru: string;
  cevap: ChatResp | null;
  hata: unknown;
};

type Props = {
  /** Belgeyi Jüri Audit Paneli'nde açar (page.tsx `inspect` deseni). */
  onInspect?: (campaignId: number) => void;
};

export default function ChatPanel({ onInspect }: Props) {
  const [q, setQ] = useState("");
  const [turlar, setTurlar] = useState<Tur[]>([]);
  const [busy, setBusy] = useState(false);
  const alanRef = useRef<HTMLTextAreaElement>(null);
  const sayacRef = useRef(0);

  // Otomatik yükseklik: içerik büyüdükçe alan büyür, `max-height`e kadar.
  useEffect(() => {
    const el = alanRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${el.scrollHeight}px`;
  }, [q]);

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      // Yarışan istek YOK: `busy` burada da kontrol edilir, yalnız düğmede değil.
      if (!text || busy) return;

      const id = (sayacRef.current += 1);
      setQ(text);
      setBusy(true);
      setTurlar((t) => [...t, { id, soru: text, cevap: null, hata: null }]);

      try {
        const cevap = await api.chat(text);
        setTurlar((t) => t.map((x) => (x.id === id ? { ...x, cevap } : x)));
      } catch (e) {
        setTurlar((t) => t.map((x) => (x.id === id ? { ...x, hata: e } : x)));
      } finally {
        setBusy(false);
      }
    },
    [busy],
  );

  return (
    <section className="card">
      <h2>Chatbot</h2>
      <p className="lede">
        Sayısal/karşılaştırmalı sorular yapısal sorguya, koşul/açıklama soruları
        RAG&apos;e yönlendirilir. Hangi yolun kullanıldığı cevabın yanında yazar.
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
      <p id="chat-ipucu" className="small faint" style={{ margin: "var(--sp-2) 0 0" }}>
        Enter gönderir · Shift+Enter yeni satır
      </p>

      <div className="chat-log" aria-live="polite" aria-busy={busy}>
        {turlar.map((t) => (
          <TurGorunumu key={t.id} tur={t} onInspect={onInspect} />
        ))}
      </div>
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
          </div>

          <Markdown metin={tur.cevap.answer} />

          <Kaynaklar cevap={tur.cevap} onInspect={onInspect} />
        </div>
      )}
    </div>
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
        belgenin denetim ekranı.
      </p>
      <div className="table-wrap">
        <table className="data stackable">
          <thead>
            <tr>
              <th scope="col">Banka</th>
              <th scope="col">Değer</th>
              <th scope="col">Kaynak metin parçası</th>
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
                <td data-label="Kaynak metin" className="small muted">
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

/**
 * Kaynak metin parçası.
 *
 * RAG pasajları `bank/value/source_span` şeklinde gelmeyebilir; birkaç bilinen
 * anahtar denenir. Hiçbiri yoksa eskiden `JSON.stringify(s)` basılıyordu —
 * jüri ekranına ham JSON dökmek, kaynağı kanıt olmaktan çıkarıp gürültüye
 * çevirir. Artık bilginin yokluğu SÖYLENİR.
 */
function Parca({ kaynak }: { kaynak: ChatSource }) {
  if (typeof kaynak.source_span === "string" && kaynak.source_span.trim()) {
    return <>…{kaynak.source_span.trim()}…</>;
  }
  for (const key of ["text", "chunk_text", "passage", "detail"]) {
    const v = kaynak[key];
    if (typeof v === "string" && v.trim()) return <>{v.trim()}</>;
  }
  return <span className="faint">kaynak metin parçası döndürülmedi</span>;
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
