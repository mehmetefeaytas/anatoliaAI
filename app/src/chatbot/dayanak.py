"""LLM cevabının kaynağa DAYANDIĞINI denetleyen ortak yardımcılar.

İlgili: ./bot.py (sözelleştirme kapısı), ./rag.py (RAG cevabı kapısı)
        CLAUDE.md §19 (halüsinasyon yasağı: bilgi yoksa null)

## Neden ayrı bir modül

Sayı denetimi iki ayrı yerde gerekiyor ve ikisi de LLM çıktısını kaynağıyla
karşılaştırıyor:

* `bot._sozellestirme_gecerli` — şablon cevabı LLM'e yeniden yazdırırken
  modelin yeni sayı UYDURMADIĞINI doğrular.
* `rag.answer` — getirilen pasajlardan sentezlenen cevabın, o pasajlarda
  bulunmayan bir sayı taşımadığını doğrular.

Yardımcı `bot.py` içindeydi; `rag.py` onu içe aktarsaydı döngüsel bağımlılık
olurdu (`bot` zaten `rag`'i içe aktarıyor). İkinci bir kopya yazmak ise bu
projede altı kez tekrarlayan "aynı bilgi iki yerde" kusuru olurdu: iki
denetim zamanla ayrışır ve biri gevşerken kimse fark etmez.

## Neden SAYILAR

Sayı, bu sistemde uydurulduğunda en pahalı şeydir: kâr payı oranı, vade,
tutar ve ücret kullanıcının karar verdiği değerlerdir. Bir cümlenin üslubu
yanlış olabilir, sayısı olmamalı. Denetim bu yüzden dar ve kesindir —
"anlamca benziyor mu" değil, "bu sayı kaynakta geçiyor mu".
"""

from __future__ import annotations

import re

#: Sayı belirteci — TR biçimi dâhil (`1.500,00`, `%1,79`, `120`).
#: Desen `bot.py`den TAŞINDI, yeniden yazılmadı: gevşetilmiş bir varyant
#: ("\\d[\\d.,]*") sondaki ayırıcıyı da yutar ve iki kapı farklı sayı listesi
#: görmeye başlardı.
_SAYI = re.compile(r"\d+(?:[.,]\d+)*")


def sayilari_ayikla(metin: str) -> list[str]:
    """Metindeki sayı belirteçleri — sondaki noktalama ayıklanmış hâlde.

    `"(%1,79)."` → `["1,79"]`. Cümle sonu noktası ondalık ayırıcı sanılırsa
    doğrulama kapısı yanlış yere düşerdi.
    """
    return [m.group(0).rstrip(".,") for m in _SAYI.finditer(metin or "")]


def dayanaksiz_sayilar(cevap: str, kaynak: str) -> list[str]:
    """Cevapta geçen ama kaynakta GEÇMEYEN sayılar (sıralı, tekil).

    Boş liste = cevabın her sayısı kaynakta var. Karşılaştırma dize
    düzeyindedir, sayısal değil: `%1,89` ile `1.89` aynı sayı olsa da farklı
    yazımdır ve kaynakta hangi yazımın geçtiği bilgidir. Gevşetmek, "kaynakta
    şöyle yazıyordu" iddiasını zayıflatırdı.
    """
    kaynak_sayilar = set(sayilari_ayikla(kaynak))
    gorulen: set[str] = set()
    disari: list[str] = []
    for s in sayilari_ayikla(cevap):
        if s in kaynak_sayilar or s in gorulen:
            continue
        gorulen.add(s)
        disari.append(s)
    return disari
