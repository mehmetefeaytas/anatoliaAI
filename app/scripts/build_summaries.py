"""Korpus için LLM özetlerini ÖNCEDEN üretir ve `campaigns.ozet`'e yazar.

İlgili: ../src/summarize/ozet.py, ../src/preprocessing/blocks.py
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

Çıkış kodları: 0 başarılı · 2 hedef DB yok/boş · 3 LLM kapalı · 4 depo
sözleşmesi eksik (`set_ozet` yok — bkz. TODO(G)).

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
import time
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.comparison.compare import _HIGHER_IS_BETTER, _LOWER_IS_BETTER
from src.db.repository import Repository
from src.extraction.llm.extractor import default_extractor
from src.summarize.ozet import MAKS_GIRDI_KARAKTER, OzetSonucu, llm_hazir, ozetle

#: Kıyas tablosunu besleyen alanlar — `compare.py`'nin kendi kümeleri.
#: Burada liste KOPYALANMAZ; ayrışırsa kapsam sessizce kayardı.
KIYAS_ALANLARI: tuple[str, ...] = tuple(sorted(_LOWER_IS_BETTER | _HIGHER_IS_BETTER))

KAPSAMLAR = ("kiyas", "hepsi")


def kiyas_kampanyalari(repo: Repository) -> set[int]:
    """Kıyaslanabilir bir alanı çıkarılmış kampanya kimlikleri.

    `query_fields()` kullanılır, ham SQL değil: depo sözleşmesi tek yoldur ve
    aynı çağrı iki backend'de de çalışır. Sözleşme/akit belgelerinin elenmesi
    de bu metodun kendi işidir (`belge_turu` süzmesi, bkz. `src/db/base.py`).
    """
    ids: set[int] = set()
    for alan in KIYAS_ALANLARI:
        for satir in repo.query_fields(alan):
            cid = satir.get("campaign_id")
            if cid is not None:
                ids.add(int(cid))
    return ids


def hedef_kampanyalar(repo: Repository, *, kapsam: str, devam: bool,
                      limit: Optional[int]) -> tuple[list[dict], int]:
    """(işlenecek kampanyalar, korpustaki toplam belge sayısı)."""
    hepsi = repo.all_campaigns()
    toplam = len(hepsi)

    if kapsam == "kiyas":
        secili = kiyas_kampanyalari(repo)
        hepsi = [c for c in hepsi if int(c["id"]) in secili]
    if devam:
        hepsi = [c for c in hepsi if not (c.get("ozet") or "").strip()]
    if limit is not None:
        hepsi = hepsi[:limit]
    return hepsi, toplam


def _yaz(repo: Repository, atamalar: dict[int, str]) -> int:
    """Özetleri depoya yazar. `set_ozet` sözleşme metodudur (ajan G)."""
    if not atamalar:
        return 0
    yazici = getattr(repo, "set_ozet", None)
    if yazici is None:
        # TODO(G): `RepositoryProtocol.set_ozet()` sözleşmede tanımlı ama bu
        # backend'de henüz uygulanmamış. Ham SQL ile yazmak bu betiği tek bir
        # backend'e bağlardı; sessizce atlamak ise boş sütunu başarı gibi
        # raporlamak olurdu. Bu yüzden gürültülü biçimde durulur.
        raise AttributeError(
            "depo `set_ozet()` uygulamıyor — TODO(G): src/db/repository.py "
            "ve src/db/postgres.py içinde sözleşme metodunu uygulayın.")
    return int(yazici(atamalar))


def calistir(db_yolu: str, *, kapsam: str = "kiyas", devam: bool = False,
             limit: Optional[int] = None, kuru: bool = False,
             maks_karakter: int = MAKS_GIRDI_KARAKTER,
             llm=None) -> dict:
    """Toplu özet üretimi. Rapor sözlüğü döndürür (JSON'a yazılabilir)."""
    llm = llm if llm is not None else default_extractor()
    repo = Repository(db_yolu)
    try:
        hedefler, toplam = hedef_kampanyalar(repo, kapsam=kapsam, devam=devam,
                                             limit=limit)
        basladi = time.time()
        atamalar: dict[int, str] = {}
        sebepler: dict[str, int] = {}
        kirpilan = 0

        for camp in hedefler:
            sonuc: OzetSonucu = ozetle(camp.get("raw_text") or "", llm,
                                       maks_karakter=maks_karakter)
            kirpilan += 1 if sonuc.kirpildi else 0
            if sonuc.uretildi and sonuc.ozet:
                atamalar[int(camp["id"])] = sonuc.ozet
            else:
                anahtar = sonuc.sebep or "bilinmiyor"
                sebepler[anahtar] = sebepler.get(anahtar, 0) + 1

        yazilan = 0 if kuru else _yaz(repo, atamalar)
        return {
            "db": db_yolu,
            "kapsam": kapsam,
            "korpus_belge": toplam,
            "hedef_belge": len(hedefler),
            "ozetlenen": len(atamalar),
            "yazilan": yazilan,
            "kuru": kuru,
            "kirpilan_girdi": kirpilan,
            "uretilemeyen": sebepler,
            "sure_sn": round(time.time() - basladi, 2),
            "llm_acik": llm_hazir(llm),
        }
    finally:
        repo.close()


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
    ap.add_argument("--limit", type=int, default=None,
                    help="en fazla kaç belge işlensin")
    ap.add_argument("--kuru", action="store_true",
                    help="üret ama veri tabanına YAZMA")
    ap.add_argument("--maks-karakter", type=int, default=MAKS_GIRDI_KARAKTER,
                    help="modele verilecek en fazla karakter")
    ap.add_argument("--json-report", default=None, help="raporu JSON olarak yaz")
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

    try:
        rapor = calistir(a.db, kapsam=a.kapsam, devam=a.devam, limit=a.limit,
                         kuru=a.kuru, maks_karakter=a.maks_karakter, llm=llm)
    except AttributeError as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 4

    _rapor_bas(rapor)
    if a.json_report:
        with open(a.json_report, "w", encoding="utf-8") as fh:
            json.dump(rapor, fh, ensure_ascii=False, indent=2)
        print(f"JSON rapor         : {a.json_report}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
