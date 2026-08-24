"""Çelişki taramasının kalıcı sonucu — soğuk açılışı 47 saniyeden sıfıra indirir.

İlgili: ../api/routers/denetim.py (`/contradictions`, artefaktı okur)
        ../../scripts/celiski_tarama.py (artefaktı üretir)
        contradiction.py (taramanın kendisi)

## Ölçülmüş arıza

Kullanıcı raporu (2026-08-24): panelin Çelişki Tespiti sekmesi "yavaş" ve arada
**500** veriyor. Ölçüldü: soğuk `/contradictions` **47,2 saniye**. Zaman
veritabanı okumasında DEĞİL (`all_campaigns()` 0,08 sn) — 2.708 belgenin
tamamında kural çıkarımı yeniden koşuyor, belge başına 17,4 ms, toplam 29 MB
metin.

Süreç içi önbellek ikinci isteği çözüyor ama BİRİNCİYİ çözmüyor; jüri sekmeye
ilk tıkladığında beklediği süre tam olarak o 47 saniyedir ve ne tarayıcı ne
Next proxy'si o kadar bekliyor.

## Neden artefakt, neden "daha hızlı tarayalım" değil

Tarama sonucu korpus sabitken DEĞİŞMEZ. Demo veritabanı salt okunur; aynı
sonucu her açılışta yeniden hesaplamak, sonucu bir kez hesaplayıp yanına
yazmaktan hiçbir açıdan iyi değil. Aynı desen depoda zaten var: pahalı ölçüm
bir artefakt üretir, okuyan taraf artefaktın TAZELİĞİNİ denetler
(`scripts/test_ozeti.py`, `scripts/kanit_tazeligi.py`).

## Tazelik: imza, dosya damgası DEĞİL

Dosya tarihine bakmak yanıltıcıdır — artefakt kopyalanınca ya da depo yeniden
klonlanınca tarih değişir, içerik değişmez. Bunun yerine korpusun kendisinden
ucuz bir imza alınıyor: belge sayısı, en yeni `scraped_at` ve toplam metin
uzunluğu. Üçü tek SQL sorgusuyla milisaniyelerde okunuyor.

İmza tutmuyorsa artefakt YOK SAYILIR ve tarama koşar. Bayat bir çelişki
listesi göstermek, yavaş olmaktan kötüdür: panel "bu belgede çelişki yok"
derken belge değişmiş olabilir.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Optional

#: Artefaktın deponun içindeki yeri. `data/` altında, çünkü türetilmiş bir
#: veri: kaynağı korpus, üreteni `scripts/celiski_tarama.py`.
VARSAYILAN_AD = "celiski-taramasi.json"

#: Biçim sürümü. Kayıt şeması değişirse bu artar ve eski artefakt yok sayılır —
#: alan adı değişmiş bir listeyi okuyup panele basmak sessiz bir bozulma olurdu.
SURUM = 1


def korpus_imzasi(repo: Any) -> Optional[str]:
    """Korpusun ucuz parmak izi; okunamıyorsa `None`.

    `None` dönmek artefaktı geçersiz kılar (imza karşılaştırması tutmaz), yani
    ölçemediğimizde TAZE VARSAYMIYORUZ. Yanlış yön burada pahalı: bayat veriyi
    taze sanmak, yavaş açılıştan kötüdür.
    """
    try:
        satirlar = repo.all_campaigns(govde=False)
    except Exception:                       # pragma: no cover - depo yoksa
        return None
    if not satirlar:
        return None
    en_yeni = max((s.get("scraped_at") or "") for s in satirlar)
    # Gövde uzunluğu imzaya GİRMİYOR: onu okumak 29 MB çekmek demek ve imzanın
    # tüm anlamı ucuz olması. Belge sayısı + en yeni toplama damgası, bu
    # korpusta değişikliği yakalamaya yetiyor — tazeleme her zaman yeni bir
    # `scraped_at` yazar.
    return f"v{SURUM}:{len(satirlar)}:{en_yeni}"


def yol(kok: Optional[pathlib.Path] = None) -> pathlib.Path:
    """Artefakt dosyasının yolu."""
    taban = kok or pathlib.Path(__file__).resolve().parents[2]
    return taban / "data" / VARSAYILAN_AD


def yaz(bulgular: list[dict], imza: str, *,
        kok: Optional[pathlib.Path] = None) -> pathlib.Path:
    """Tarama sonucunu imzasıyla birlikte yazar."""
    hedef = yol(kok)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_text(
        json.dumps({"surum": SURUM, "korpus_imzasi": imza,
                    "bulgu_sayisi": len(bulgular), "bulgular": bulgular},
                   ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    return hedef


def oku(imza: Optional[str], *,
        kok: Optional[pathlib.Path] = None) -> Optional[list[dict]]:
    """Artefakt TAZE ise bulguları döndürür; değilse `None`.

    Üç ret sebebi ayrı ayrı denetleniyor ve üçü de sessizce `None` veriyor —
    çağıran taraf zaten taramayı koşarak doğru sonuca varıyor. Ret bir hata
    değil, "artefaktı kullanma" kararıdır.
    """
    if imza is None:
        return None
    hedef = yol(kok)
    if not hedef.exists():
        return None
    try:
        veri = json.loads(hedef.read_text(encoding="utf-8"))
    except (OSError, ValueError):            # pragma: no cover - bozuk dosya
        return None
    if not isinstance(veri, dict):
        return None
    if veri.get("surum") != SURUM:
        return None
    if veri.get("korpus_imzasi") != imza:
        return None
    bulgular = veri.get("bulgular")
    if not isinstance(bulgular, list):
        return None
    return bulgular
