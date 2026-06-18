"""Uçtan uca pipeline — scrape → extract → classify → reconcile → store.

İlgili: ../syntheses/teknik-cozum-mimarisi.md, CLAUDE.md §3
Tüm katmanları birleştiren tek giriş. Offline (fixture + kural + null-LLM) koşar;
modeller/servisler varsa otomatik devreye girer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .chatbot.bot import Chatbot
from .comparison.contradiction import detect as detect_contradictions
from .db.repository import Repository
from .extraction.llm.extractor import LLMExtractor, default_extractor
from .extraction.ner.classifier import default_classifier
from .extraction.reconcile import build_campaign
from .preprocessing.clean import normalize_text
from .scraping.collector import collect
from .scraping.config import BankConfig, load_banks


@dataclass
class PipelineResult:
    campaigns_stored: int
    contradictions: list[dict]


def run_pipeline(repo: Repository, banks_yaml: str, raw_dir: str = "data/raw",
                 mode: str = "auto", llm: Optional[LLMExtractor] = None,
                 scraped_at: Optional[str] = None) -> PipelineResult:
    """Tüm bankalar için topla → çıkar → sınıflandır → kaydet."""
    banks = load_banks(banks_yaml)
    llm = llm if llm is not None else default_extractor()
    clf = default_classifier()

    stored = 0
    contradictions: list[dict] = []
    for bank in banks:
        repo.upsert_bank(bank.name, bank.slug, bank.website_url, bank.bddk_active)
        for doc in collect(bank, raw_dir=raw_dir, mode=mode, scraped_at=scraped_at):
            text = normalize_text(doc.clean_text)
            ctype, _conf = clf.classify(text)
            campaign = build_campaign(text, bank_slug=bank.slug,
                                      source_url=doc.source_url, llm=llm,
                                      campaign_type=ctype)
            for con in detect_contradictions(campaign):
                contradictions.append({"bank": bank.slug, "kind": con.kind,
                                       "detail": con.detail})
            repo.insert_campaign(campaign, clean_text=text, scraped_at=doc.scraped_at)
            stored += 1
    return PipelineResult(stored, contradictions)


def build_demo_repo(banks_yaml: str = "config/banks.yaml",
                    raw_dir: str = "data/raw") -> Repository:
    """Önceden doldurulmuş in-memory DB (demo stratejisi).

    İlgili: ../decisions/demo-onceden-doldurulmus-db.md
    """
    repo = Repository(":memory:")
    run_pipeline(repo, banks_yaml, raw_dir=raw_dir, mode="fixture")
    return repo


def make_chatbot(repo: Repository, llm: Optional[LLMExtractor] = None) -> Chatbot:
    return Chatbot(repo, llm=llm)
