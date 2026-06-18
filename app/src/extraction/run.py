"""CLI: tek metin dosyası üzerinde çıkarım (debug/inceleme).

Kullanım:
    python -m src.extraction.run --input data/processed/sample.txt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..extraction.llm.extractor import default_extractor
from ..extraction.ner.classifier import default_classifier
from ..extraction.reconcile import build_campaign
from ..preprocessing.clean import normalize_text


def main() -> None:
    ap = argparse.ArgumentParser(description="Tek metin çıkarımı")
    ap.add_argument("--input", required=True)
    ap.add_argument("--bank", default="bilinmeyen")
    args = ap.parse_args()

    text = normalize_text(Path(args.input).read_text(encoding="utf-8"))
    ctype, conf = default_classifier().classify(text)
    campaign = build_campaign(text, bank_slug=args.bank, llm=default_extractor(),
                              campaign_type=ctype)

    out = {
        "bank": campaign.bank_slug,
        "campaign_type": campaign.campaign_type,
        "fields": [
            {"field": f.field_name, "value": f.canonical_value,
             "confidence": f.confidence, "extractor": f.extractor.value,
             "source_span": f.source_span}
            for f in campaign.fields
        ],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
