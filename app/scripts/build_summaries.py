"""Korpus için LLM özetlerini ÖNCEDEN üretir ve `campaigns.ozet`'e yazar.

**Bu dosya ince bir kabuktur.** Üretim döngüsünün gövdesi
`src/summarize/toplu.py` içindedir; arayüzdeki «LLM ile özet üret» düğmesi de
aynı gövdeyi çağırır (`src/summarize/ozet_isi.py`). Buradan yeniden dışa
verilen adlar geriye uyum içindir.

İlgili: ../src/summarize/toplu.py (gövde), ../src/summarize/ozet.py,
        ../src/preprocessing/blocks.py
        ../src/api/main.py (`GET /campaigns/{id}/text` -> `ozet`, `ozet_kaynak`)
        CLAUDE.md §11 (demo doldurulmuş DB'den okur)

## Neden önceden

CLAUDE.md §11: 4 dakikalık sunumda canlı yerel model = donma riski. Özet
gösterim katmanının parçası olduğu için istek anında üretilseydi her belge
açılışı model çağrısı kadar beklerdi. Bu betik özetleri kalıcı DB'ye yazar;
demo yalnız okur.

## Kullanım

    OLLAMA_NUM_CTX=8192 LLM_BACKEND=ollama LLM_STRICT=1 \\
        python3 -m scripts.build_summaries --db data/demo.db --limit 50

    python3 -m scripts.build_summaries --db data/demo.db --devam   # kaldığı yerden
    python3 -m scripts.build_summaries --db data/demo.db --kapsam hepsi
    python3 -m scripts.build_summaries --db data/demo.db --kuru    # yazmadan dene

Çıkış kodları: 0 başarılı · 2 hedef DB yok/boş · 3 LLM kapalı.

Kod 3 neden ayrı ve neden GÜRÜLTÜLÜ: LLM kapalıyken bu betik hiçbir şey
üretmez ve **üretmemesi gerekir** (`src/summarize/ozet.py`: kural tabanlı
sahte özet yasak). Sessizce 0 dönüp "tamamlandı" demek, boş bir özet
sütununu başarı gibi raporlamak olurdu.

## Kapsam: önce kıyasta görünen alt küme

Korpus 1761 belge; hepsini tek koşuda özetlemek uzun sürer. Varsayılan kapsam
(`--kapsam kiyas`) kıyaslanabilir bir alanı ÇIKARILMIŞ belgelerdir — yani
dashboard'un karşılaştırma tablosunda ve demo akışında gerçekten görünenler.
Betik `--devam` ile tekrar tekrar koşulabilir; her koşu yalnız özeti olmayan
belgeleri işler, böylece kapsam kademeli büyür.

**Kısmi kapsama tam gibi raporlanmaz:** rapor hem işlenen hem de korpustaki
toplam belge sayısını basar.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extraction.llm.extractor import default_extractor
from src.summarize.ozet import MAKS_GIRDI_KARAKTER, llm_hazir

# Gövde `src/summarize/toplu.py`de. Buradan yeniden dışa veriliyor: eski
# çağrı yolu (`scripts.build_summaries.calistir`) kırılmasın diye — testler ve
# belgelenmiş komutlar onu kullanıyor.
from src.summarize.toplu import (  # noqa: F401  (yeniden dışa verim)
    KAPSAMLAR,
    KIYAS_ALANLARI,
    YAZMA_PARCASI,
    calistir,
    hedef_kampanyalar,
    kiyas_kampanyalari,
)


def _rapor_bas(rapor: dict) -> None:
    print(f"veri tabanı        : {rapor['db']}")
    print(f"kapsam             : {rapor['kapsam']}")
    print(f"korpus belge       : {rapor['korpus_belge']}")
    print(f"hedeflenen belge   : {rapor['hedef_belge']}")
    print(f"özetlenen belge    : {rapor['ozetlenen']}")
    print(f"yazılan satır      : {rapor['yazilan']}" + ("  (kuru koşu)" if rapor["kuru"] else ""))
    print(f"kırpılan girdi     : {rapor['kirpilan_girdi']}")
    print(f"süre (sn)          : {rapor['sure_sn']}")
    if rapor["uretilemeyen"]:
        print("üretilemeyen       :")
        for sebep, adet in sorted(rapor["uretilemeyen"].items()):
            print(f"  {sebep:<24} {adet}")
    kapsandi = rapor["ozetlenen"]
    print(f"KAPSAMA            : {kapsandi}/{rapor['korpus_belge']} belge "
          "(kısmi kapsama tam kapsama değildir)")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="data/demo.db", help="hedef SQLite dosyası")
    ap.add_argument("--kapsam", choices=KAPSAMLAR, default="kiyas",
                    help="kiyas = kıyas tablosunda görünen belgeler (öntanım)")
    ap.add_argument("--devam", action="store_true",
                    help="özeti zaten olan belgeleri atla (tekrar koşulabilir)")
    ap.add_argument("--kalici-atla", action="store_true",
                    help="özetlenecek içeriği olmadığı ÖLÇÜLMÜŞ belgeleri de "
                         "atla (sebebi `metin_bos` olanlar); tekrar denemek "
                         "aynı sonucu verir")
    ap.add_argument("--limit", type=int, default=None,
                    help="en fazla kaç belge işlensin")
    ap.add_argument("--kuru", action="store_true",
                    help="üret ama veri tabanına YAZMA")
    ap.add_argument("--maks-karakter", type=int, default=MAKS_GIRDI_KARAKTER,
                    help="modele verilecek en fazla karakter")
    ap.add_argument("--json-report", default=None, help="raporu JSON olarak yaz")
    ap.add_argument("--parca", type=int, default=YAZMA_PARCASI,
                    help=f"kaç belgede bir DB'ye yazılsın (öntanım {YAZMA_PARCASI}; "
                         "0 = yalnız sonda yaz)")
    a = ap.parse_args(argv)

    # Ollama varsayılan bağlamı 2048'dir ve fazlasını SESSİZCE baştan kırpar —
    # yani sistem yönergesi kaybolur. Değer açıkça verilir (çağıran zaten
    # vermişse ezilmez).
    os.environ.setdefault("OLLAMA_NUM_CTX", "8192")

    if not os.path.exists(a.db):
        print(f"HATA: veri tabanı yok: {a.db}. Önce "
              "`python3 -m scripts.build_demo_db --out data/demo.db`.",
              file=sys.stderr)
        return 2

    llm = default_extractor()
    if not llm_hazir(llm):
        print("HATA: LLM kapalı. Özet ÜRETİLMEDİ ve kural tabanlı sahte bir "
              "özet basılmadı (src/summarize/ozet.py). Açmak için: "
              "LLM_BACKEND=ollama LLM_STRICT=1 (model: qwen2.5:7b-instruct).",
              file=sys.stderr)
        return 3

    def _ilerleme(islenen: int, hedef: int, yazilan: int) -> None:
        # Uzun koşuda tek çıktı sondaki rapor olmamalı: ilerleme görünmezse
        # "takıldı mı, çalışıyor mu" ayırt edilemez. `flush` şart — çıktı bir
        # dosyaya yönlendirildiğinde satır tamponlaması devreye girmez.
        print(f"  ... {islenen}/{hedef} belge · {yazilan} satır yazıldı",
              flush=True)

    # `AttributeError` yakalayıp 4 döndüren dal KALDIRILDI: yakaladığı durum
    # (depoda `set_ozet()` yok) artık oluşamaz — gerekçe `_yaz()` içinde.
    rapor = calistir(a.db, kapsam=a.kapsam, devam=a.devam, limit=a.limit,
                     kuru=a.kuru, maks_karakter=a.maks_karakter, llm=llm,
                     parca=a.parca, kalici_atla=a.kalici_atla,
                     ilerleme=_ilerleme)

    _rapor_bas(rapor)
    if a.json_report:
        with open(a.json_report, "w", encoding="utf-8") as fh:
            json.dump(rapor, fh, ensure_ascii=False, indent=2)
        print(f"JSON rapor         : {a.json_report}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
