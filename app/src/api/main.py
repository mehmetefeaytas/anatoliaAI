"""FastAPI uygulaması — dashboard + chatbot backend.

İlgili: ../../entities/dashboard.md, ../../entities/chatbot.md, CLAUDE.md §7
        ../../decisions/dashboard-ve-chatbot-arayuzu.md

Uçlar:
  GET  /health
  GET  /banks
  GET  /campaigns
  GET  /compare?field=kar_payi_orani&intent=lowest&type=Konut+Finansmanı
  POST /chat            {"question": "..."}
  POST /extract         {"text": "...", "bank": "..."}   (tek metin canlı çıkarım)
  GET  /contradictions

Veri kaynağı: önceden doldurulmuş DB (demo stratejisi). Uygulama açılışında
fixture'lardan in-memory DB kurulur; DATABASE_PATH verilirse kalıcı SQLite.
"""

from __future__ import annotations

import os
from typing import Optional

from ..chatbot.bot import Chatbot
from ..comparison.compare import rank
from ..comparison.contradiction import detect as detect_contradictions
from ..db.repository import Repository
from ..extraction.llm.extractor import default_extractor
from ..extraction.ner.classifier import default_classifier
from ..extraction.reconcile import build_campaign
from ..pipeline import run_pipeline
from ..preprocessing.clean import normalize_text

CONFIG = os.environ.get("BANKS_CONFIG", "config/banks.yaml")
RAW_DIR = os.environ.get("RAW_DIR", "data/raw")
DB_PATH = os.environ.get("DATABASE_PATH", ":memory:")


def build_app():
    """FastAPI uygulamasını kur. fastapi yoksa anlaşılır hata verir."""
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from pydantic import BaseModel
    except ModuleNotFoundError as e:  # pragma: no cover
        raise RuntimeError(
            "fastapi/pydantic kurulu değil. `pip install -r requirements.txt`") from e

    app = FastAPI(title="Anatolia AI — Katılım Bankacılığı Kampanya API")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"],
                       allow_headers=["*"])

    repo = Repository(DB_PATH)
    # demo verisini doldur (önceden doldurulmuş DB stratejisi)
    run_pipeline(repo, CONFIG, raw_dir=RAW_DIR, mode="fixture")
    llm = default_extractor()
    bot = Chatbot(repo, llm=llm)
    clf = default_classifier()

    class ChatReq(BaseModel):
        question: str

    class ExtractReq(BaseModel):
        text: str
        bank: str = "bilinmeyen"

    @app.get("/health")
    def health():
        return {"status": "ok", "llm": llm.available}

    @app.get("/banks")
    def banks():
        rows = repo.conn.execute(
            "SELECT slug, name, website_url, bddk_active FROM banks").fetchall()
        return [dict(r) for r in rows]

    @app.get("/campaigns")
    def campaigns():
        return repo.all_campaigns()

    @app.get("/compare")
    def compare(field: str, intent: Optional[str] = None, type: Optional[str] = None):
        rows = repo.query_fields(field)
        if type:
            rows = [r for r in rows if r.get("campaign_type") == type]
        ranked = rank(rows, field)
        return [
            {"bank": r.bank, "bank_name": r.bank_name, "value": r.value,
             "comparable": r.comparable, "note": r.note, "source_span": r.source_span}
            for r in ranked
        ]

    @app.post("/chat")
    def chat(req: ChatReq):
        a = bot.ask(req.question)
        return {"answer": a.text, "handler": a.handler, "field": a.field,
                "sources": a.sources}

    @app.post("/extract")
    def extract(req: ExtractReq):
        text = normalize_text(req.text)
        ctype, conf = clf.classify(text)
        c = build_campaign(text, bank_slug=req.bank, llm=llm, campaign_type=ctype)
        return {
            "bank": c.bank_slug, "campaign_type": c.campaign_type,
            "fields": [
                {"field": f.field_name, "value": f.canonical_value,
                 "confidence": f.confidence, "extractor": f.extractor.value,
                 "source_span": f.source_span}
                for f in c.fields
            ],
            "contradictions": [
                {"kind": k.kind, "detail": k.detail}
                for k in detect_contradictions(c)
            ],
        }

    @app.get("/contradictions")
    def contradictions():
        out = []
        for camp in repo.all_campaigns():
            text = camp.get("raw_text", "")
            c = build_campaign(text, bank_slug=camp["bank"])
            for k in detect_contradictions(c):
                out.append({"bank": camp["bank"], "kind": k.kind, "detail": k.detail})
        return out

    return app


# uvicorn src.api.main:app
try:  # pragma: no cover
    app = build_app()
except RuntimeError:
    app = None
