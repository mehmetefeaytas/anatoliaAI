"""Çelişki tespiti `source_url` olmadan KÖRDÜR.

İlgili: ../src/api/main.py (`_campaign_contradictions`)
        ../src/comparison/contradiction.py (`_rule_expired_but_published`)
        ../src/extraction/reconcile.py (`build_campaign`)

## Bu testin varlık sebebi

`_campaign_contradictions` `build_campaign(text, bank_slug=...)` çağırıyordu —
**`source_url` geçirmeden**. `_rule_expired_but_published` ise ilk satırında
`campaign.source_url or ""` üzerinde URL araması yapıyor:

    url = campaign.source_url or ""
    if not _CAMPAIGN_URL.search(url) or _ARCHIVE_URL.search(url):
        return []

URL boş gelince kural HER ZAMAN boş dönüyordu. Yani "süresi dolmuş ama sayfa
hâlâ yayında" çelişkisi API'nin hiçbir ucunda görünmüyordu: `/contradictions`,
`/campaigns/{id}/text` ve `/compare`'in `contradiction_count` alanı hepsi kör.

Bu, projenin üç yenilikçilik hedefinden birini (bankalar arası çelişki
tespiti) sessizce yarıya indiriyordu. Ölçüldü (2026-08-09, `data/demo.db`):

    düzeltme öncesi   6 çelişki · suresi_dolmus_kampanya  0
    düzeltme sonrası 16 çelişki · suresi_dolmus_kampanya 10

`main.py`'nin kendi docstring'i bu kuralın "`as_of` geçilmediği için kapalıydı"
diye düzeltildiğini yazıyordu — iki eksikten biri kapatılmış, öteki atlanmıştı.
İşte bu yüzden düzeltme notu yetmez, kapı gerekir.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.contradiction import detect as detect_contradictions
from src.extraction.reconcile import build_campaign

#: Süresi dolmuş bir kampanya sayfası: bitiş tarihi toplama gününden ÖNCE ve
#: metin kendini "süresi doldu" diye işaretlemiyor.
#: İfade biçimi `contradiction._END_PATTERNS`'e uymak ZORUNDA — "Kampanya
#: Tarihleri 01.01.2024 - 31.03.2024" biçimi `end_date_claims` tarafından
#: TANINMIYOR (ölçüldü). Test uydurma bir cümleyle değil, ayrıştırıcının
#: gerçekten tanıdığı biçimle kurulur; aksi hâlde kuralı değil kendi
#: varsayımımı ölçerdim.
METIN = (
    "Konut Finansmanı Kampanyası. Kampanya 31.03.2024 tarihine kadar "
    "geçerlidir. Kâr payı oranı %2,05'ten başlar. Kampanya Koşulları: "
    "Yalnız yeni müşteriler için geçerlidir."
)
URL = "https://ornek-katilim.com.tr/kampanyalar/konut-finansmani-kampanyasi"
TOPLAMA = "2026-08-01"


def _api_kaynagi() -> str:
    """`src/api/main.py` kaynağı.

    `inspect.getsource` kullanılmıyor: uçlar bir fabrika fonksiyonu içinde
    değil, modül düzeyinde kuruluyor. Dosyayı doğrudan okumak tek doğruluk
    kaynağıdır ve modülü içe aktarma yan etkisi de doğurmaz.
    """
    return (Path(__file__).resolve().parents[1]
            / "src" / "api" / "main.py").read_text(encoding="utf-8")


def _kinds(source_url, as_of=TOPLAMA):
    c = build_campaign(METIN, bank_slug="ornek", source_url=source_url)
    return {k.kind for k in detect_contradictions(c, as_of=as_of)}


class TestSourceUrlZorunlu(unittest.TestCase):
    def test_URL_YOKSA_kural_KOR(self) -> None:
        """Kusurun kendisi: URL boşken kural hiç ateşlenmez."""
        self.assertNotIn("suresi_dolmus_kampanya", _kinds(None),
                         "URL'siz çağrıda kuralın ateşlenmemesi BEKLENEN "
                         "davranış — bu test kusuru değil, sebebini belgeler")

    def test_URL_VARSA_kural_ATESLENIR(self) -> None:
        self.assertIn("suresi_dolmus_kampanya", _kinds(URL))

    def test_arsiv_URLsi_ateslemez(self) -> None:
        """Arşiv klasöründeki kampanyanın süresinin dolması çelişki değildir."""
        arsiv = "https://ornek-katilim.com.tr/kampanyalar/kampanya-arsivi/konut"
        self.assertNotIn("suresi_dolmus_kampanya", _kinds(arsiv))

    def test_toplama_gununden_SONRA_biten_ateslemez(self) -> None:
        """İddia 'biz topladığımızda dolmuştu' olmalı; duvar saati değil."""
        self.assertNotIn("suresi_dolmus_kampanya", _kinds(URL, as_of="2024-01-15"))


class TestApiUcuTasiyor(unittest.TestCase):
    """API `source_url`'i çelişki yoluna GERÇEKTEN iletiyor mu."""

    def test_campaign_contradictions_source_url_kabul_ediyor(self) -> None:
        kaynak = _api_kaynagi()
        self.assertIn("source_url=source_url", kaynak,
                      "`build_campaign` çağrısı `source_url` almıyor — kural "
                      "yine kör kalır")

    def test_dort_cagri_yeri_de_iletiyor(self) -> None:
        """Bir çağrı yeri unutulursa o uç kör kalır; sayıyı kilitle."""
        kaynak = _api_kaynagi()
        self.assertGreaterEqual(
            kaynak.count("_campaign_contradictions("), 5,
            "çağrı yeri sayısı beklenenden az — biri silinmiş olabilir")
        # `source_url` iletmeyen bir çağrı kalmamalı: her çağrı ya
        # `source_url` ya da `get("source_url")` içermeli.
        for parca in kaynak.split("_campaign_contradictions(")[1:]:
            govde = parca[:220]
            if govde.startswith(")"):
                continue              # docstring içindeki anımsatma, çağrı değil
            if "def " in govde[:40]:
                continue              # imzanın kendisi
            self.assertIn("source_url", govde,
                          f"`source_url` iletmeyen çağrı: …{govde[:120]}")


if __name__ == "__main__":
    unittest.main()
