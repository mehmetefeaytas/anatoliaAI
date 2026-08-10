"""Hibrit chatbot orkestrasyonu — güvenlik kapıları → router → yapısal sorgu / RAG.

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        ../../entities/chatbot.md, CLAUDE.md §5
        ../docs/katilim-bankaciligi-guvenligi.md (5 kapı)

Akış:
    soru → safety.screen_input (5 kapı)
         → durdurulduysa hazır politika yanıtı
         → aksi halde route(soru, bağlam) → structured / rag
         → yapısal yolda: LLM ile sözelleştirme + doğrulama kapısı
         → safety.guard_output (post-filter + düzeltme notu + feragatname)

## Sohbet hafızası

`ask()` isteğe bağlı bir `router.ChatContext` alır ve her cevabın yanında bir
sonraki tur için taşınacak durumu (`ChatAnswer.context`) döndürür. Sunucu bu
durumu SAKLAMAZ; istemci saklar ve geri gönderir. Gerekçe iki tane:

  1. Demo tek kullanıcılı değil — sunucuda oturum tutmak, iki tarayıcının
     birbirinin bağlamını görmesi demektir.
  2. Sunucu yeniden başlatıldığında (yerel LLM'li bir demoda sık) oturum
     kaybolur; istemcideki hafıza sayfayı yenilemeye bile dayanır.

Güvenlik sırası DEĞİŞMEDİ ve değişemez: kapılar o anki sorunun HAM metni
üzerinde, router'dan ve bağlamdan ÖNCE koşar. Bağlam bir kapıyı açamaz; en
fazla, zaten geçmiş bir sorunun eksik boyutunu tamamlar.

## Sözelleştirme (yapısal yol)

Yapısal sorgu şablon üretir: `"en düşük kâr payı oranı: **X** (%1,79)."`
Doğru ama robotik. Yerel LLM varsa bu cümle akıcı Türkçeye çevrilir — ancak
ÇEVİRİ, OLGUYU DEĞİŞTİREMEZ. Çıktı basılmadan önce programatik doğrulama
kapısından geçer (`_sozellestirme_gecerli`); geçemezse şablon basılır ve
düşüş loglanır. Ayrıntı: `_sozellestir` docstring'i.
"""

from __future__ import annotations

import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as _Zamanasimi
from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Optional

from ..db.repository import Repository
from . import rag, safety, structured
from .router import ChatContext, Route, route

logger = logging.getLogger(__name__)


@dataclass
class ChatAnswer:
    text: str
    handler: str           # 'structured' | 'rag' | 'safety'
    field: Optional[str]
    sources: list          # kaynak satırları / pasajlar (açıklanabilirlik)
    # Geriye uyumlu ek alanlar: /chat uç noktası bunları görmezden gelebilir,
    # ya da `safety_report.as_dict()` ile serileştirip yanıta ekleyebilir.
    safety_report: Optional[safety.SafetyReport] = None
    gates: list[str] = dc_field(default_factory=list)
    #: Bu turdan sonra taşınacak durum (istemci saklar, geri gönderir).
    context: dict = dc_field(default_factory=dict)
    #: Bu turda önceki turlardan devralınan boyutlar (kullanıcıya gösterilir).
    inherited: list[dict] = dc_field(default_factory=list)
    #: Sözelleştirme denetim kaydı — {attempted, applied, ms, note}.
    verbalize: dict = dc_field(default_factory=dict)
    #: KAPI 6 — talimat-devralma işareti taşıdığı için DÜŞÜRÜLEN pasajlar.
    #:
    #: `rag.RagAnswer.quarantined` bu bilgiyi zaten üretiyordu ama bot katmanı
    #: onu taşımıyordu: kapı çalışıyor, pasajı düşürüyor ve düşürdüğünü
    #: kimseye söylemiyordu. Korpusta talimat gömülü bir belge bulunduğunda
    #: `rag.py` bunu WARNING olarak loglar; ekranda hiçbir iz kalmıyordu.
    #: Projenin en güçlü güvenlik iddiasının sessiz kalması demekti.
    #:
    #: Yapısal (text-to-SQL) yolda her zaman boştur — o yol serbest metin
    #: getirmez, dolayısıyla karantinaya alınacak pasajı da yoktur.
    quarantined: list[dict] = dc_field(default_factory=list)


# --------------------------------------------------------------------------- #
# Sözelleştirme ayarları
# --------------------------------------------------------------------------- #
#: Sözelleştirmeyi tamamen kapatan anahtar (`0` → kapalı). Varsayılan açık;
#: LLM yoksa zaten hiç denenmez.
_ACIK_ENV = "CHAT_SOZELLESTIRME"

#: Sözelleştirme için AZAMİ bekleme (saniye). Süre aşılırsa şablon basılır.
#:
#: ÖLÇÜLDÜ (2026-08-09, 16 GB geliştirme makinesi, ollama qwen2.5:7b-instruct
#: model bellekte yerleşik): sözelleştirme cevap başına 9,2–18,7 sn ekliyor
#: (ortanca ~10,5 sn); şablon yolu aynı sorularda 3–92 ms. Üretimin kendisi
#: hızlı (~20 belirteç/sn, cevap ~20 belirteç); maliyet makinenin yükü
#: altındaki çekişmeden geliyor.
#:
#: Bu yüzden sınır 12 sn: ölçülen ortancayı kapsar ama 4 dakikalık bir
#: sunumda en kötü hâli sınırlar (CLAUDE.md §11 — canlı LLM kritik yolda
#: olmamalı). Daha güçlü bir demo makinesinde `CHAT_SOZELLESTIRME_SANIYE`
#: ile yükseltilir, hiç istenmiyorsa `CHAT_SOZELLESTIRME=0` ile kapatılır.
#: Not: API varsayılan olarak `LLM_BACKEND` boş çalışır, yani sözelleştirme
#: operatör LLM'i açıkça açmadıkça HİÇ denenmez.
_SURE_ENV = "CHAT_SOZELLESTIRME_SANIYE"
_VARSAYILAN_SURE = 12.0

#: Yalnız TEK CÜMLELİK şablonlar sözelleştirilir. Liste cevabı (her satırda bir
#: banka) yeniden yazıldığında hem doğrulama kapısı anlamsızlaşır hem de
#: okunabilirlik düşer: tablo gibi okunan bir liste, paragrafa çevrilince
#: karşılaştırma işlevini kaybeder.
_AZAMI_KARAKTER = 400

#: Sayı belirteci — TR biçimi dâhil (`1.500,00`, `%1,79`, `120`).
_SAYI = re.compile(r"\d+(?:[.,]\d+)*")

_SOZ_SISTEM = (
    "Sen bir katılım bankacılığı asistanısın. Görevin, sana verilen HAZIR "
    "CEVABI daha akıcı ve doğal bir Türkçe cümleye çevirmektir.\n"
    "KURALLAR (ihlal edilemez):\n"
    "1. Verilen cevabın DIŞINA çıkma. Yeni bilgi, yeni banka adı, yeni ürün "
    "ya da yeni sayı EKLEME.\n"
    "2. Sayıları AYNEN koru: yuvarlama yok, birim değiştirme yok, biçim "
    "değiştirme yok. '%1,79' yazıyorsa çıktıda da '%1,79' geçmeli.\n"
    "3. Banka adlarını AYNEN koru.\n"
    "4. 'yaklaşık', 'genellikle', 'ortalama', 'civarında' gibi verilen "
    "cevapta olmayan nitelemeler kullanma.\n"
    "5. En fazla iki cümle yaz. Yorum yapma, tavsiye verme.\n"
    "Çıktı biçimi: {\"cevap\": \"...\"}"
)

_SOZ_SEMA = {"type": "object", "properties": {"cevap": {"type": "string"}},
             "required": ["cevap"]}

#: Sözelleştirme çağrıları için ayrı iş parçacığı havuzu. Neden gerekli:
#: `generate_json()` bir zaman aşımı parametresi almaz ve istemcinin kendi
#: zaman aşımı ortam değişkeninden gelir (yüklü makinede 900 sn olabilir).
#: Cevabı o kadar bekletmek yerine `future.result(timeout=...)` ile kendi
#: son teslim tarihimizi koyarız; süre dolarsa şablon basılır, arka plandaki
#: çağrı kendi zaman aşımıyla sönümlenir.
_HAVUZ: Optional[ThreadPoolExecutor] = None


def _havuz() -> ThreadPoolExecutor:
    global _HAVUZ
    if _HAVUZ is None:
        _HAVUZ = ThreadPoolExecutor(max_workers=4,
                                    thread_name_prefix="sozellestirme")
    return _HAVUZ


def _sozellestirme_acik() -> bool:
    return os.environ.get(_ACIK_ENV, "1").strip().lower() not in {
        "0", "false", "hayir", "kapali"}


def _sozellestirme_suresi() -> float:
    try:
        deger = float(os.environ.get(_SURE_ENV, "") or _VARSAYILAN_SURE)
    except ValueError:
        return _VARSAYILAN_SURE
    return deger if deger > 0 else _VARSAYILAN_SURE


def sayilari_ayikla(metin: str) -> list[str]:
    """Metindeki sayı belirteçleri — sondaki noktalama ayıklanmış hâlde.

    `"(%1,79)."` → `["1,79"]`. Cümle sonu noktası ondalık ayırıcı sanılırsa
    doğrulama kapısı yanlış yere düşerdi.
    """
    return [m.group(0).rstrip(".,") for m in _SAYI.finditer(metin or "")]


def _sozellestirme_gecerli(sablon: str, aday: str) -> Optional[str]:
    """Sözelleştirilmiş cevabı olgu bazında denetler; hata gerekçesi döner.

    Üç denetim, üçü de tek yönlü değil ÇİFT yönlü:

    * Şablondaki her sayı adayda AYNEN geçmeli (bilgi düşürülmesin).
    * Adayda şablonda OLMAYAN sayı geçmemeli — en tehlikeli hata budur:
      uydurulmuş bir oran, doğru görünen bir cümlenin içinde fark edilmez.
    * Banka kümesi birebir aynı olmalı (ne eksik ne fazla).

    `None` dönerse aday temizdir; aksi hâlde dönen dize log ve arayüz için
    gerekçedir.
    """
    aday = (aday or "").strip()
    if not aday:
        return "boş çıktı"
    if len(aday) > len(sablon) * 3 + 200:
        return "çıktı şablona göre aşırı uzun"

    sablon_sayilar = sayilari_ayikla(sablon)
    aday_sayilar = sayilari_ayikla(aday)
    eksik = [s for s in set(sablon_sayilar) if s not in aday_sayilar]
    if eksik:
        return f"şablondaki sayı çıktıda yok: {', '.join(sorted(eksik))}"
    uydurma = [s for s in set(aday_sayilar) if s not in sablon_sayilar]
    if uydurma:
        return f"şablonda olmayan sayı üretildi: {', '.join(sorted(uydurma))}"

    # Tire boşluğa çevrilir: `RankRow.bank_name` boş olan kayıtlarda şablon
    # bankanın SLUG'ını basar ("kuveyt-turk") ve `detect_banks` ad sözlüğüyle
    # eşleştiği için tireli biçimi tanımaz. Tanımayınca şablonda banka yok
    # sayılır, modelin doğru yazdığı ad ise "uydurulmuş banka" diye
    # reddedilirdi — kapı doğru cevabı düşürürdü.
    sablon_bankalar = set(safety.detect_banks(sablon.replace("-", " ")))
    aday_bankalar = set(safety.detect_banks(aday.replace("-", " ")))
    if sablon_bankalar - aday_bankalar:
        return ("şablondaki banka çıktıda yok: "
                + ", ".join(sorted(sablon_bankalar - aday_bankalar)))
    if aday_bankalar - sablon_bankalar:
        return ("şablonda olmayan banka üretildi: "
                + ", ".join(sorted(aday_bankalar - sablon_bankalar)))
    return None


@dataclass
class _Dagitim:
    """Seçilen yolun (yapısal / RAG) tüm çıktısı — tek taşıyıcı.

    Neden nesne, neden 8'li demet değil: `rows` alanı bağlam üretimi için
    gerekiyordu ve onu `self._son_rows` gibi bir örnek alanında taşımak
    THREAD GÜVENLİ DEĞİLDİ — FastAPI `def` uçlarını bir iş parçacığı
    havuzunda koşturur, iki eşzamanlı soru birbirinin satırlarını okurdu.
    """

    handler: str
    field: Optional[str]
    body: str
    sources: list
    has_rate: bool
    route: Route
    verbalize: dict
    rows: list
    #: KAPI 6'nın düşürdüğü pasajlar (yalnız RAG yolunda dolabilir).
    quarantined: list = dc_field(default_factory=list)


def _yeni_baglam(d: _Dagitim) -> dict:
    """Bir sonraki tura taşınacak durum.

    `subject_banks` yalnız cevabın ÖZNESİ tek bir bankaya indiğinde
    doldurulur. On bankalı bir liste cevabında özne yoktur; oraya keyfî bir
    banka yazmak, kullanıcının sormadığı bir süzgeci sonraki tura miras
    bırakırdı.
    """
    ozne: list[str] = []
    if d.handler == "structured":
        if d.route.intent in ("lowest", "highest"):
            kiyas = [x for x in d.rows if x.comparable and x.bank]
            if kiyas:
                ozne = [kiyas[0].bank]
        if not ozne:
            slugs = {x.bank for x in d.rows if x.bank}
            if len(slugs) == 1:
                ozne = list(slugs)
    return ChatContext(field=d.route.field, intent=d.route.intent,
                       filters=dict(d.route.filters),
                       subject_banks=ozne).as_dict()


class Chatbot:
    """Tek giriş noktası: ask(question, context) → ChatAnswer."""

    def __init__(self, repo: Repository, llm=None, safety_enabled: bool = True):
        self.repo = repo
        self.llm = llm
        # Güvenlik katmanı varsayılan olarak AÇIK. Kapatma seçeneği yalnızca
        # ablasyon/ölçüm içindir (kapıların gerçekten fark yarattığını
        # göstermek); üretimde kapatılmaz.
        self.safety_enabled = safety_enabled
        # RAG dizini bot ömrü boyunca BİR kez kurulur. Eskiden `rag.answer`
        # her soruda yeni bir retriever yaratıyordu; 1696 belgelik korpusta
        # bu soru başına ~300 ms'ydi ve chatbot p99'unu tek başına üretiyordu.
        self._retriever: Optional[rag.KeywordRetriever] = None
        # Depo kurulum anında zaten doluysa dizini HEMEN kur: maliyet açılışta
        # ödenir, jüri önündeki ilk soruda değil (CLAUDE.md §11 — önceden
        # doldurulmuş DB). Depo boşsa (önce bot, sonra seed eden testler)
        # dizin ilk RAG sorusunda tembel kurulur.
        self._ensure_retriever(require_data=True)

    def _ensure_retriever(self, require_data: bool = False
                          ) -> Optional[rag.KeywordRetriever]:
        """RAG retriever'ını (ters dizin) döner; gerekiyorsa kurar.

        `require_data=True` iken boş depo için dizin kurulmaz ve None dönülür —
        böylece sonradan doldurulan depolarda bayat (stale) dizin kalmaz.
        """
        if self._retriever is None:
            candidate = rag.KeywordRetriever(self.repo)
            if require_data and candidate.document_count == 0:
                return None
            self._retriever = candidate
        return self._retriever

    def reindex(self) -> None:
        """Depo kurulumdan sonra değiştiyse RAG dizinini yeniden kur."""
        self._retriever = None
        self._ensure_retriever(require_data=True)

    def ask(self, question: str,
            context: Optional[ChatContext] = None) -> ChatAnswer:
        if not self.safety_enabled:
            return self._answer_unguarded(question, context)

        # KAPILAR ÖNCE, BAĞLAM SONRA. Taranan dize her zaman kullanıcının bu
        # turda yazdığı HAM sorudur; bağlam kanalı taramaya hiç girmez.
        # Böylece "önceki turdan gelen bir şey kapıyı açtı" senaryosu yapısal
        # olarak imkânsızdır.
        scr = safety.screen_input(question)

        # KAPI 2 (fıkhî hüküm) / KAPI 5 (kapsam dışı): hazır politika yanıtı;
        # veri sorgusu hiç yapılmaz.
        if scr.blocked:
            text, report = safety.guard_output(scr.reply or "", scr,
                                               has_sources=True)
            # Durdurulan tur bağlam ÜRETMEZ: reddedilmiş bir sorunun alanını
            # sonraki turlara taşımak, reddi dolaylı olarak geri alırdı.
            return ChatAnswer(text, "safety", scr.field_hint, [], report,
                              report.gates)

        d = self._dispatch(question, scr, context)
        text, report = safety.guard_output(d.body, scr,
                                           has_sources=bool(d.sources),
                                           has_rate=d.has_rate)
        return ChatAnswer(text, d.handler, d.field, d.sources, report,
                          report.gates, context=_yeni_baglam(d),
                          inherited=list(d.route.inherited),
                          verbalize=d.verbalize,
                          quarantined=list(d.quarantined))

    # --- iç yardımcılar ----------------------------------------------------
    def _dispatch(self, question: str, scr: safety.InputScreening,
                  context: Optional[ChatContext] = None) -> "_Dagitim":
        """Router'ı çalıştırıp seçilen yolun tüm çıktısını toplar."""
        r = route(question, context)

        # KAPI 3 — karşılaştırma ≠ tavsiye. "Hangi bankaya para yatırayım?"
        # sorusunda alan çıkarılamaz ve sistem RAG'a düşüp çekimser kalırdı.
        # Doğru davranış: tavsiye VERMEDEN karşılaştırmalı olgu tablosu sunmak.
        # Varsayılan karşılaştırma alanı kâr payı oranıdır (senaryonun kalbi).
        if scr.advice_intent and not (r.handler == "structured" and r.field):
            r = Route("structured", r.field or safety.INTEREST_FIELD_HINT,
                      r.intent or "list", r.filters, r.inherited)

        if r.handler == "structured" and r.field:
            ans = structured.answer(self.repo, r)
            sources = [{"bank": x.bank, "value": x.value,
                        "source_span": x.source_span} for x in ans.rows]
            has_rate = (r.field == "kar_payi_orani"
                        or safety.contains_rate(ans.text))
            govde, soz = self._sozellestir(ans.text, bool(sources))
            return _Dagitim("structured", r.field, govde, sources, has_rate,
                            r, soz, list(ans.rows))
        ans = rag.answer(self.repo, question, llm=self.llm,
                         retriever=self._ensure_retriever())
        # RAG yolu ZATEN LLM'den geçiyor (`rag.answer` bağlamdan cevap
        # sentezliyor). Orada bir kez daha sözelleştirmek hem ikinci bir
        # gecikme ekler hem de LLM çıktısını LLM'e yeniden yazdırmak olur:
        # doğrulama kapısı bu durumda "kaynak" olarak zaten üretilmiş bir
        # metni alır ve hiçbir şey garanti etmez.
        return _Dagitim("rag", r.field, ans.text, ans.passages,
                        safety.contains_rate(ans.text), r,
                        {"attempted": False, "applied": False,
                         "ms": None, "reason": "RAG yolu"}, [],
                        quarantined=list(getattr(ans, "quarantined", []) or []))

    def _sozellestir(self, sablon: str, kaynak_var: bool) -> tuple[str, dict]:
        """Şablon cevabı LLM ile yeniden ifade eder; kapıyı geçemezse şablon.

        Sıra bilinçli: bu işlem `safety.guard_output`tan ÖNCE yapılır. Yani
        LLM'e giden metin, feragatname ve düzeltme notu EKLENMEDEN önceki
        çıplak gövdedir; notlar sonradan eklenir ve sözelleştirme onları
        yutamaz. Ayrıca LLM çıktısı da `sanitize_output` (KAPI 1) post-filter'ından
        geçmiş olur — model yasak terim üretse bile ekrana çıkamaz.
        """
        rapor = {"attempted": False, "applied": False, "ms": None,
                 "reason": None}
        if not kaynak_var:
            rapor["reason"] = "kaynak yok"
            return sablon, rapor
        if not _sozellestirme_acik():
            rapor["reason"] = "kapalı"
            return sablon, rapor
        if self.llm is None or not getattr(self.llm, "available", False):
            rapor["reason"] = "LLM yok"
            return sablon, rapor
        if "\n" in sablon.strip() or len(sablon) > _AZAMI_KARAKTER:
            rapor["reason"] = "liste cevabı"
            return sablon, rapor

        client = getattr(self.llm, "client", None)
        if client is None:
            rapor["reason"] = "LLM istemcisi yok"
            return sablon, rapor

        rapor["attempted"] = True
        basladi = time.perf_counter()
        try:
            gelecek = _havuz().submit(
                client.generate_json, _SOZ_SISTEM,
                f"Hazır cevap: {sablon}\nBunu akıcı Türkçe ile yeniden yaz.",
                _SOZ_SEMA)
            cikti = gelecek.result(timeout=_sozellestirme_suresi())
            aday = (cikti or {}).get("cevap", "") if isinstance(cikti, dict) else ""
        except _Zamanasimi:
            rapor["ms"] = int((time.perf_counter() - basladi) * 1000)
            rapor["reason"] = "zaman aşımı"
            logger.warning("sozellestirme zaman asimi (%s ms) -> sablon",
                           rapor["ms"])
            return sablon, rapor
        except Exception as exc:                       # LLM/ağ/ayrıştırma
            rapor["ms"] = int((time.perf_counter() - basladi) * 1000)
            rapor["reason"] = f"LLM hatası: {type(exc).__name__}"
            logger.warning("sozellestirme basarisiz (%s) -> sablon", exc)
            return sablon, rapor

        rapor["ms"] = int((time.perf_counter() - basladi) * 1000)
        gerekce = _sozellestirme_gecerli(sablon, aday)
        if gerekce is not None:
            rapor["reason"] = gerekce
            # SESSİZ düşüş yok: kapının kaç kez ve neden düştüğü ölçülebilir
            # olmalı, yoksa "kapı hiç düşmüyor" ile "kapı hiç çalışmıyor"
            # ayırt edilemez.
            logger.warning("sozellestirme dogrulama kapisi DUSURDU (%s); "
                           "sablon=%r aday=%r", gerekce, sablon, aday)
            return sablon, rapor

        rapor["applied"] = True
        return aday.strip(), rapor

    def _answer_unguarded(self, question: str,
                          context: Optional[ChatContext] = None) -> ChatAnswer:
        """Güvenlik katmanı KAPALI yol — yalnızca ablasyon ölçümü için."""
        d = self._dispatch(question, safety.InputScreening(question=question),
                           context)
        return ChatAnswer(d.body, d.handler, d.field, d.sources,
                          context=_yeni_baglam(d),
                          inherited=list(d.route.inherited),
                          verbalize=d.verbalize,
                          quarantined=list(d.quarantined))
