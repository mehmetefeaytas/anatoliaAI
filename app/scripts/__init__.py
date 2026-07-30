"""Gold set anotasyon hattı — çalıştırılabilir betikler.

Bu paket üretim kodu (`src/`) DEĞİLDİR; anotasyon iş akışının araçlarıdır:

    scripts/gold_schema.py     Gold şema v1: yükle / doğrula / kanonikleştir
    scripts/preannotate.py     data/raw → hibrit çıkarım → ön-anotasyon JSON
    scripts/to_review_csv.py   ön-anotasyon → alan-başına-satır inceleme CSV'si
    scripts/build_gold.py      doldurulmuş CSV'ler → data/gold/gold.v1.json
    scripts/report_iaa.py      iki/çok anotatör CSV'si → kappa + uyuşmazlık raporu

Hepsi saf stdlib ve offline çalışır (LLM_BACKEND boşsa kural-only).
"""
