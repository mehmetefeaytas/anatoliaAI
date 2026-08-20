"""Yeniden kurulan DB'ye, ESKİ DB'deki hâlâ GEÇERLİ özetleri taşır.

İlgili: build_demo_db.py (DB'yi sıfırdan kurar, `ozet` sütunu boş gelir)
        build_summaries.py (eksik özetleri LLM ile üretir)
        check_demo_db.py (bayatlama kapısı)
        ../src/summarize/ozet.py (özetin kural tabanlı üretilmesi YASAK)

## Neden var — ölçülmüş maliyet

`build_demo_db --force` DB'yi sıfırdan kurar ve `campaigns.ozet` sütunu boş
gelir. Korpustaki 1.750 özeti yeniden üretmek yerel modelle ~4 saat sürer;
bu yüzden korpus tazelendiği hâlde DB günlerce bayat bırakıldı — chatbot ve
dashboard 8 yeni belgeyi hiç görmedi.

Oysa ölçüldü (2026-08-12, `data/demo.db` ve `data/raw`):

    DB metni diskle AYNI  : 1.724 belge   -> özeti HÂLÂ GEÇERLİ
    metni değişmiş        :    48 belge   -> özeti bayat
    DB'de hiç yok (yeni)  :     8 belge   -> özeti yok

Yani gerçekte yeniden üretilmesi gereken özet sayısı 1.750 değil **56**;
~4 saat değil ~8 dakika. Bu betik o 1.724 özeti taşıyarak farkı kapatır.

## Taşıma ölçütü: METİN BİREBİR AYNI olmalı

`source_url` eşleşmesi YETMEZ. Bir kampanya sayfasının metni değiştiğinde
eski özet artık o belgeyi anlatmıyordur; onu taşımak, düzeltmek istediğimiz
bayatlığı sessizce korumak olurdu — üstelik bu kez görünmez biçimde, çünkü
sütun dolu görünür.

Ölçüt bu yüzden `raw_text` karşılaştırmasıdır (kenar boşlukları kırpılmış).
Metni değişen belge BİLEREK özetsiz bırakılır; `build_summaries` onu üretir.

## `ozet_sebep` de taşınır

Özet üretilmediğinde nedeni bu sütunda durur ("belge çok kısa", "LLM
reddetti" gibi). Yalnız `ozet`i taşımak, "neden özet yok" bilgisini
kaybettirir ve arayüz boş bir kutu gösterir.

## Kullanım

    python3 -m scripts.ozet_tasi --kaynak data/demo.db.yedek \\
                                 --hedef data/demo.yeni.db
    python3 -m scripts.ozet_tasi --kaynak eski.db --hedef yeni.db --kuru

Çıkış kodları: 0 başarılı · 2 kaynak/hedef DB yok · 3 şema uyumsuz.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass
class TasimaSonucu:
    tasinan: int = 0
    metni_degisti: int = 0
    hedefte_yok: int = 0
    kaynakta_ozet_yok: int = 0

    #: Terminoloji kapısına takılıp taşınMAYAN özet sayısı. Ayrı sayılır:
    #: "kaynakta özet yoktu" ile "kaynaktaki özet REDDEDİLDİ" farklı olgular
    #: ve ikincisi kaynağın kalitesi hakkında bilgi taşır.
    terminoloji_reddi: int = 0

    @property
    def aday(self) -> int:
        return (self.tasinan + self.metni_degisti + self.hedefte_yok)

    def rapor(self, kuru: bool) -> str:
        baslik = "KURU KOŞU (yazılmadı)" if kuru else "ÖZET TAŞIMA"
        return "\n".join([
            f"=== {baslik} ===",
            f"taşınan özet          : {self.tasinan}",
            f"metni değişmiş (atlandı): {self.metni_degisti}"
            "   <- bayat özet taşınmaz, build_summaries üretecek",
            f"hedefte bulunamayan   : {self.hedefte_yok}"
            "   <- kaynakta olup hedefte olmayan belge",
            f"kaynakta özeti yoktu  : {self.kaynakta_ozet_yok}",
            f"terminoloji reddi    : {self.terminoloji_reddi}"
            "   <- kaynaktaki özet konvansiyonel/uydurma terim taşıyordu",
        ])


from src.summarize.ozet import _terminoloji_ihlali


def _kolonlar(conn: sqlite3.Connection) -> set[str]:
    return {r[1] for r in conn.execute("PRAGMA table_info(campaigns)")}


def tasi(kaynak_yolu: Path, hedef_yolu: Path, *,
         kuru: bool = False) -> TasimaSonucu:
    """Geçerli özetleri kaynaktan hedefe taşır."""
    kaynak = sqlite3.connect(f"file:{kaynak_yolu}?mode=ro", uri=True)
    kaynak.row_factory = sqlite3.Row
    hedef = sqlite3.connect(hedef_yolu)
    hedef.row_factory = sqlite3.Row

    for ad, conn in (("kaynak", kaynak), ("hedef", hedef)):
        eksik = {"source_url", "raw_text", "ozet"} - _kolonlar(conn)
        if eksik:
            raise SystemExit(
                f"HATA: {ad} DB şeması uyumsuz, eksik kolon: {sorted(eksik)}")

    sebep_var = "ozet_sebep" in _kolonlar(kaynak) and \
                "ozet_sebep" in _kolonlar(hedef)

    # Anahtar (source_url, raw_text) ÇİFTİDİR — `source_url` tek başına DEĞİL.
    #
    # Ölçüldü (2026-08-12): korpusta **95 tekrarlı URL** var; aynı sayfada
    # birden çok ürün tanımlanabiliyor (ör. bir dış ticaret sayfasında dört
    # ayrı finansman kalemi). URL'yi tek anahtar sayan ilk sürüm her URL için
    # yalnız SON kaydı tutuyordu ve **93 özet sessizce düşüyordu** — üstelik
    # betik "1726 taşındı" diye başarı raporluyordu.
    #
    # Aynı çiftten birden çok satır olabileceği için değer bir LİSTEDİR ve
    # sırayla tüketilir; böylece kaynaktaki her satır hedefte ayrı bir satıra
    # gider, ikisi de aynı kayda yazılmaz.
    hedef_kayit: dict[tuple[str, str], list[int]] = {}
    for r in hedef.execute("SELECT id, source_url, raw_text FROM campaigns"):
        if not r["source_url"]:
            continue
        anahtar = (r["source_url"], (r["raw_text"] or "").strip())
        hedef_kayit.setdefault(anahtar, []).append(r["id"])

    # Metni değişmiş kaydı ayırt edebilmek için URL bazlı varlık kümesi.
    hedef_urller = {u for u, _ in hedef_kayit}

    sonuc = TasimaSonucu()
    yazilacak: list[tuple] = []
    sec = ("SELECT source_url, raw_text, ozet, ozet_sebep FROM campaigns"
           if sebep_var else
           "SELECT source_url, raw_text, ozet FROM campaigns")
    for r in kaynak.execute(sec):
        url = r["source_url"]
        ozet = (r["ozet"] or "").strip()
        sebep = (r["ozet_sebep"] if sebep_var else None)
        if not url or (not ozet and not sebep):
            sonuc.kaynakta_ozet_yok += 1
            continue
        metin = (r["raw_text"] or "").strip()
        adaylar = hedef_kayit.get((url, metin))
        if not adaylar:
            # URL hedefte var ama bu METİNLE yok -> içerik değişmiş.
            # URL hiç yoksa belge hedeften düşmüş demektir; ikisi ayrı ayrı
            # sayılır, çünkü biri beklenen (tazeleme), diğeri şüphelidir.
            if url in hedef_urller:
                sonuc.metni_degisti += 1
            else:
                sonuc.hedefte_yok += 1
            continue
        # TERMİNOLOJİ KAPISI — yedekten geri yükleme, kapı EKLENMEDEN ÖNCE
        # üretilmiş özetleri geri getirebilir. Ölçüldü (2026-08-20): korpustaki
        # 2.455 özetin 41'i konvansiyonel/uydurma banka terimi taşıyordu
        # ("kapitalizm bankacılığı" 25 · "Kâr Payı Bankası X" 9 · çıplak
        # "faiz" 7). Onları DB'den temizlemek yetmez: bu betik bir sonraki
        # yeniden kurulumda yedekten AYNI metni geri yazardı.
        # Kapı üretim anında da var (`src/summarize/ozet.py`); burada ikinci
        # kez uygulanması gereksiz değil, çünkü bu yolun girdisi ESKİ bir
        # artefakttır ve o artefakt kapıyı hiç görmemiştir.
        if ozet:
            ihlal = _terminoloji_ihlali(ozet)
            if ihlal:
                sonuc.terminoloji_reddi += 1
                continue
        hedef_id = adaylar.pop(0)   # aynı çiftten birden çok satır olabilir
        sonuc.tasinan += 1
        yazilacak.append((ozet or None, sebep, hedef_id) if sebep_var
                         else (ozet or None, hedef_id))

    if not kuru and yazilacak:
        sql = ("UPDATE campaigns SET ozet=?, ozet_sebep=? WHERE id=?"
               if sebep_var else "UPDATE campaigns SET ozet=? WHERE id=?")
        hedef.executemany(sql, yazilacak)
        hedef.commit()
    kaynak.close()
    hedef.close()
    return sonuc


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Yeniden kurulan DB'ye hâlâ geçerli özetleri taşır.")
    ap.add_argument("--kaynak", required=True, help="eski (özetli) DB")
    ap.add_argument("--hedef", required=True, help="yeni kurulan DB")
    ap.add_argument("--kuru", action="store_true",
                    help="yazma, yalnız ne olacağını raporla")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    kaynak, hedef = Path(args.kaynak), Path(args.hedef)
    for ad, p in (("kaynak", kaynak), ("hedef", hedef)):
        if not p.is_file():
            print(f"HATA: {ad} DB yok: {p}", file=sys.stderr)
            return 2

    sonuc = tasi(kaynak, hedef, kuru=args.kuru)
    print(sonuc.rapor(args.kuru))
    if sonuc.metni_degisti or sonuc.hedefte_yok:
        print("\nSonraki adım — eksik özetleri üret:")
        print(f"    python3 -m scripts.build_summaries --db {hedef} --devam")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
