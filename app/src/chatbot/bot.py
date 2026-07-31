"""Hibrit chatbot orkestrasyonu — güvenlik kapıları → router → yapısal sorgu / RAG.

İlgili: ../../decisions/hibrit-chatbot-text-to-sql-rag.md
        ../../entities/chatbot.md, CLAUDE.md §5
        ../docs/katilim-bankaciligi-guvenligi.md (5 kapı)

Akış:
    soru → safety.screen_input (5 kapı)
         → durdurulduysa hazır politika yanıtı
         → aksi halde route() → structured / rag
         → safety.guard_output (post-filter + düzeltme notu + feragatname)
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dc_field
from typing import Optional

from ..db.repository import Repository
from . import rag, safety, structured
from .router import Route, route


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


class Chatbot:
    """Tek giriş noktası: ask(question) → ChatAnswer."""

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

    def ask(self, question: str) -> ChatAnswer:
        if not self.safety_enabled:
            return self._answer_unguarded(question)

        scr = safety.screen_input(question)

        # KAPI 2 (fıkhî hüküm) / KAPI 5 (kapsam dışı): hazır politika yanıtı;
        # veri sorgusu hiç yapılmaz.
        if scr.blocked:
            text, report = safety.guard_output(scr.reply or "", scr,
                                               has_sources=True)
            return ChatAnswer(text, "safety", scr.field_hint, [], report,
                              report.gates)

        handler, field, body, sources, has_rate = self._dispatch(question, scr)
        text, report = safety.guard_output(body, scr,
                                           has_sources=bool(sources),
                                           has_rate=has_rate)
        return ChatAnswer(text, handler, field, sources, report, report.gates)

    # --- iç yardımcılar ----------------------------------------------------
    def _dispatch(self, question: str, scr: safety.InputScreening
                  ) -> tuple[str, Optional[str], str, list, bool]:
        """Router'ı çalıştırıp (handler, alan, gövde, kaynaklar, oran-var-mı)."""
        r = route(question)

        # KAPI 3 — karşılaştırma ≠ tavsiye. "Hangi bankaya para yatırayım?"
        # sorusunda alan çıkarılamaz ve sistem RAG'a düşüp çekimser kalırdı.
        # Doğru davranış: tavsiye VERMEDEN karşılaştırmalı olgu tablosu sunmak.
        # Varsayılan karşılaştırma alanı kâr payı oranıdır (senaryonun kalbi).
        if scr.advice_intent and not (r.handler == "structured" and r.field):
            r = Route("structured", r.field or safety.INTEREST_FIELD_HINT,
                      r.intent or "list", r.filters)

        if r.handler == "structured" and r.field:
            ans = structured.answer(self.repo, r)
            sources = [{"bank": x.bank, "value": x.value,
                        "source_span": x.source_span} for x in ans.rows]
            has_rate = (r.field == "kar_payi_orani"
                        or safety.contains_rate(ans.text))
            return "structured", r.field, ans.text, sources, has_rate
        ans = rag.answer(self.repo, question, llm=self.llm,
                         retriever=self._ensure_retriever())
        return "rag", r.field, ans.text, ans.passages, safety.contains_rate(ans.text)

    def _answer_unguarded(self, question: str) -> ChatAnswer:
        """Güvenlik katmanı KAPALI yol — yalnızca ablasyon ölçümü için."""
        handler, field, body, sources, _ = self._dispatch(
            question, safety.InputScreening(question=question))
        return ChatAnswer(body, handler, field, sources)
