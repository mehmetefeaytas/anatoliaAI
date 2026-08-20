"""Demo DB korpusla güncel mi? — sessiz bayatlamaya karşı kapı.

İlgili: build_demo_db.py, ../src/pipeline.py, ../docs/rapor/rag-terim-kapsama.md

## Neden var — gerçekleşmiş bir vaka

`data/demo.db` **31 Temmuz'da** kuruldu (849 belge). Korpus **3 Ağustos'ta**
1761 belgeye çıktı ve `docs/` bölümü (sözleşme + tarife) o gün eklendi.
Arada geçen bir haftada:

- chatbot, dashboard ve RAG korpusun **%48'ini** hiç görmedi,
- fıkhî terim yoğunluğu en yüksek bölümün **tamamı** erişilemez kaldı,
- hiçbir yerde uyarı çıkmadı, hiçbir test kırılmadı.

Fark ancak terim kapsaması elle ölçülünce görüldü. Bu betik o boşluğu
kapatır: DB'deki kampanya sayısı ile korpustaki belge sayısı ayrışırsa
**gürültülü** biçimde başarısız olur.

## Neden dosya zaman damgası DEĞİL

`mtime` klon/checkout sonrası yeniden yazılır ve git zaman bilgisini
korumaz. Belge SAYISI ise hem sağlam hem de tam olarak yaşanan hatayı
yakalar (849 ≠ 1761).

## Kullanım

    python -m scripts.check_demo_db                     # varsayılan yollar
    python -m scripts.check_demo_db --db data/demo.db --raw-dir data/raw
    python -m scripts.check_demo_db --tolerans 5        # N belgelik sapmayı hoş gör

Çıkış kodları: 0 güncel · 1 BAYAT · 2 DB yok / okunamıyor.

CI'da `lint` işine eklenebilir. `data/demo.db` git'te izlenmediği için CI'da
tipik olarak kod 2 döner — bu yüzden CI'da `--db-yoksa-gec` ile koşulmalı.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))

VARSAYILAN_DB = "data/demo.db"
VARSAYILAN_RAW = "data/raw"
CORPUS_SUFFIX = ".txt"


def korpus_belge_sayisi(raw_dir: str) -> int:
    """`collect_corpus` ile AYNI ölçütü kullanır: özyinelemeli `.txt`.

    Ölçüt burada elle tekrarlanıyor çünkü bu betiğin işi pipeline'ı
    doğrulamak; pipeline'ı import edip ona sormak, denetlenen şeyle
    denetleyeni aynı kaynağa bağlardı.
    """
    return sum(1 for p in Path(raw_dir).rglob(f"*{CORPUS_SUFFIX}") if p.is_file())


def db_kampanya_sayisi(db: str) -> int:
    conn = sqlite3.connect(db)
    try:
        return conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    finally:
        conn.close()


def icerik_bayatligi(db: str, raw_dir: str) -> tuple[int, int, int]:
    """(metni değişmiş, özeti de bayat, karşılaştırılan) sayılarını döndürür.

    ## Neden SAYI kapısı yetmiyor — ölçülmüş vaka (2026-08-12)

    Bu betik yalnız belge SAYISINI karşılaştırıyordu ve 11 Ağustos
    tazelemesinden sonra "8 belge eksik" dedi. Doğruydu ama EKSİKTİ: aynı
    tazelemede **48 belgenin İÇERİĞİ de değişmişti** ve sayı değişmediği
    için kapı bunu hiç görmedi.

    İçerik bayatlığı sayı bayatlığından daha sinsidir: bir kampanya sayfası
    güncellenip oranı değiştiğinde DB eski oranı göstermeye devam eder,
    üstelik `ozet` sütunu DOLU olduğu için arayüzde her şey normal görünür.
    Kullanıcı, kaynağında artık bulunmayan bir sayıyı okur.

    Karşılaştırma `raw_text` üzerinden yapılır. `.meta.json`'daki
    `content_hash` HAM HTML'in özetidir, çıkarılmış metnin değil; bu iş için
    kullanılamaz (denendi ve ölçüldü: 1.759 belgeyi yanlışlıkla "değişmiş"
    gösteriyordu).

    DB tarafı URL başına KÜME tutar: korpusta 95 tekrarlı URL var (aynı
    sayfada birden çok ürün tanımlanabiliyor). Soru "eşleşen kayıt hangisi"
    değil, "diskteki metin bu URL'nin DB'deki metinlerinden herhangi biriyle
    tutuyor mu" olduğu için küme yeterli ve doğrudur.
    """
    import json
    from collections import defaultdict

    def _sadelestir(s: str) -> str:
        """Boşluk ve TİPOGRAFİK TIRNAK düzenini eşitler — YANLIŞ POZİTİF kaynağı.

        `build_demo_db` metni DB'ye yazarken satır sonlarını boşluğa
        çeviriyor ("...\\nMobil Bankacılık\\nAç\\n" -> "... Mobil Bankacılık
        Aç "). Ham karşılaştırma bunu "içerik değişti" sanıyordu ve kapı
        tazelenmiş bir DB'de bile bayat raporluyordu.

        ## Tipografik tırnak — ikinci ölçülmüş yanlış pozitif (2026-08-12)

        Kapı, TAM `--force` yeniden inşadan SONRA bile 1 belgeyi bayat
        gösteriyordu ve hiçbir yeniden inşa bunu düzeltemiyordu. Fark tek
        karakterdi:

            DB   : ... "Sağlık Kampanyası" kampanyası için ...
            disk : ... "Sağlık Kampanyası” kampanyası için ...   (U+201D)

        Sebep: yazma yolu `preprocessing.clean` üzerinden geçiyor ve o modül
        kıvrık tırnakları düzleştiriyor (`clean.py:127`:
        `.replace("’","'").replace("“",'"').replace("”",'"')`). Denetçi ise
        yalnız boşluğu eşitliyordu, dolayısıyla kalıcı bir yalancı bayatlık
        raporluyordu — yani kapı, kapatılamayan bir alarm çalıyordu.

        Kapatılamayan alarm, kapalı alarmla aynı sonucu verir: kimse bakmaz.

        Dönüşüm burada da ELLE yazılır; `preprocessing.clean` import
        EDİLMEZ. Gerekçe modül başlığında: denetleyeni denetlenenin koduna
        bağlamak, ikisi birlikte bozulduğunda kapıyı kör eder. Boşluk düzeni
        ve tırnak BİÇİMİ anlam taşımaz, bu yüzden eşitlemek gerçek bir
        içerik değişikliğini gizlemez — oranın, tutarın, tarihin değişmesi
        hâlâ yakalanır.
        """
        s = (s or "")
        for kivrik, duz in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"')):
            s = s.replace(kivrik, duz)
        return " ".join(s.split())

    db_metin: dict[str, set[str]] = defaultdict(set)
    ozetli: dict[str, bool] = {}
    conn = sqlite3.connect(db)
    try:
        # Eksik şemada ÇÖKMEK yerine içerik denetimini atla. Bu kapı bir
        # yardımcıdır; sayı kapısını çalışmaz hâle getirmemeli. Eski şemalı
        # ya da kısmi bir DB (kolonu olmayan test fikstürü dâhil) sayı
        # denetiminden yine geçebilmelidir.
        kolonlar = {r[1] for r in conn.execute("PRAGMA table_info(campaigns)")}
        if not {"source_url", "raw_text"} <= kolonlar:
            return 0, 0, 0
        ozet_var = "ozet" in kolonlar
        sec = ("SELECT source_url, raw_text, ozet FROM campaigns" if ozet_var
               else "SELECT source_url, raw_text, NULL FROM campaigns")
        for url, metin, ozet in conn.execute(sec):
            if not url:
                continue
            db_metin[url].add(_sadelestir(metin))
            if (ozet or "").strip():
                ozetli[url] = True
    finally:
        conn.close()

    degisen = ozeti_bayat = karsilastirilan = 0
    for meta in Path(raw_dir).rglob(f"*{CORPUS_SUFFIX}.meta.json"):
        try:
            d = json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        url = d.get("source_url")
        txt = Path(str(meta)[: -len(".meta.json")])
        if not url or url not in db_metin or not txt.is_file():
            continue
        try:
            disk = _sadelestir(
                txt.read_text(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        karsilastirilan += 1
        if disk not in db_metin[url]:
            degisen += 1
            if ozetli.get(url):
                ozeti_bayat += 1
    return degisen, ozeti_bayat, karsilastirilan



def ozet_kapsami(db: str) -> tuple[int, int]:
    """`(ozetli, toplam)` — kaç kampanyanın AI özeti var.

    ## Bu kapı NİÇİN var — ölçülmüş bir test/üretim ayrışması

    20 Ağustos 2026: teslim edilen `data/demo.db`de 1.782 belgenin
    **tamamında** `ozet` NULL'du. Panel ve sohbet her belgede "AI Özeti
    üretilmedi" diyor ve kullanıcıya ham metnin başı — bazı sayfalarda site
    gezinme şeridi (`"Anasayfa Kendim Için Içerik…"`) — gösteriliyordu.

    Sebep: `scripts/build_demo_db` `campaigns.ozet` sütununu BİLMEZ ve boş
    bırakır; geri yükleme adımı (`scripts/ozet_tasi`) kurulum belgesinde
    yazılı değildi.

    Niçin testler yakalamadı: `tests/test_chat_ai_ozeti.py` **sözleşmeyi**
    denetliyor (`ozet` anahtarı her zaman var, yoksa `None`) — kapsamı değil.
    Sözleşme kusursuz çalışıyordu; üretimde ölçülecek özet yoktu. Bir
    davranışın doğru olması, o davranışın *tetiklendiği* anlamına gelmiyor.

    `metin_bos` sebepli belgeler (içeriği olmayan sayfa) sayıma girer ve
    kapsamı düşürür; eşik bu yüzden %100 değildir. Ölçüldü: 23 belge.
    """
    with sqlite3.connect(f"file:{db}?mode=ro", uri=True) as conn:
        kolonlar = {r[1] for r in conn.execute("PRAGMA table_info(campaigns)")}
        if "ozet" not in kolonlar:
            return 0, 0
        (toplam,) = conn.execute("SELECT COUNT(*) FROM campaigns").fetchone()
        (ozetli,) = conn.execute(
            "SELECT COUNT(*) FROM campaigns "
            "WHERE ozet IS NOT NULL AND TRIM(ozet) <> ''").fetchone()
    return int(ozetli), int(toplam)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m scripts.check_demo_db",
        description="Demo DB korpusla güncel mi? Bayatsa gürültülü başarısız olur.")
    ap.add_argument("--db", default=VARSAYILAN_DB)
    ap.add_argument("--raw-dir", default=VARSAYILAN_RAW)
    ap.add_argument("--tolerans", type=int, default=0,
                    help="hoş görülen belge farkı (varsayılan 0)")
    ap.add_argument("--db-yoksa-gec", action="store_true",
                    help="DB dosyası yoksa 2 yerine 0 dön (CI için)")
    ap.add_argument("--icerik-tolerans", type=int, default=0,
                    help="hoş görülen İÇERİK farkı (varsayılan 0)")
    ap.add_argument("--ozet-kapsam-asgari", type=float, default=0.90,
                    help="asgari AI özeti kapsamı (0-1, varsayılan 0,90); "
                         "0 verilirse kapı kapatılır")
    ap.add_argument("--sayi-yeter", action="store_true",
                    help="yalnız belge sayısına bak, içerik karşılaştırma "
                         "(eski davranış; 48 belgelik bayatlığı kaçırmıştı)")
    args = ap.parse_args(argv)

    if not Path(args.db).is_file():
        if args.db_yoksa_gec:
            print(f"DB yok, atlanıyor: {args.db}")
            return 0
        print(f"HATA: DB bulunamadı: {args.db}\n"
              f"  Kurmak için: python -m scripts.build_demo_db --out {args.db}",
              file=sys.stderr)
        return 2
    if not Path(args.raw_dir).is_dir():
        print(f"HATA: korpus dizini yok: {args.raw_dir}", file=sys.stderr)
        return 2

    try:
        db_n = db_kampanya_sayisi(args.db)
    except sqlite3.Error as e:
        print(f"HATA: DB okunamadı ({args.db}): {e}", file=sys.stderr)
        return 2
    korpus_n = korpus_belge_sayisi(args.raw_dir)
    fark = korpus_n - db_n

    print(f"DB kampanya   : {db_n}")
    print(f"korpus belge  : {korpus_n}")
    print(f"fark          : {fark:+d}")

    # İÇERİK kapısı — sayı tutsa bile metin değişmiş olabilir.
    degisen = ozeti_bayat = 0
    if not args.sayi_yeter:
        degisen, ozeti_bayat, karsilastirilan = icerik_bayatligi(
            args.db, args.raw_dir)
        print(f"içerik denetimi: {karsilastirilan} belge karşılaştırıldı, "
              f"{degisen} metin değişmiş ({ozeti_bayat} tanesinin özeti de bayat)")

    # ÖZET KAPSAMI — sayı ve içerik güncel olsa bile özetler boş olabilir;
    # 20 Ağustos'ta tam bu oldu (bkz. `ozet_kapsami` docstring'i).
    # `ozet_toplam == 0` iki şeyin ikisinde de olur: (a) `campaigns` boş,
    # (b) şemada `ozet` kolonu hiç yok (eski DB ya da test kurgusu). İkisinde
    # de ÖLÇÜLECEK ŞEY YOKTUR ve payda sıfırdır — oranı 0,0 sayıp "bayat"
    # demek, olmayan bir kusuru rapor etmek olurdu. Kapı bu durumda SUSAR.
    # Ölçüldü: bu kontrol olmadan `tests/test_demo_db_tazelik.py`nin iki
    # testi düşüyordu; kurgu DB'lerinde `ozet` kolonu yok ve kapı boş tabloyu
    # bayat ilan ediyordu.
    ozet_bayat = False
    if args.ozet_kapsam_asgari > 0:
        ozetli, ozet_toplam = ozet_kapsami(args.db)
        if ozet_toplam == 0:
            print("özet kapsamı  : ölçülemedi (kampanya yok ya da `ozet` "
                  "kolonu şemada yok) — kapı atlandı")
        else:
            oran = ozetli / ozet_toplam
            print(f"özet kapsamı  : {ozetli}/{ozet_toplam} "
                  f"({oran:.1%}, asgari {args.ozet_kapsam_asgari:.0%})")
            ozet_bayat = oran < args.ozet_kapsam_asgari

    sayi_bayat = abs(fark) > args.tolerans
    icerik_bayat = degisen > args.icerik_tolerans

    if not sayi_bayat and not icerik_bayat and not ozet_bayat:
        print("\nGÜNCEL.")
        return 0

    if ozet_bayat:
        print(f"\nBAYAT: AI özeti kapsamı {oran:.1%} < "
              f"{args.ozet_kapsam_asgari:.0%}.\n"
              f"  Geri yüklemek için: python -m scripts.ozet_tasi "
              f"--kaynak data/demo.db.yedek-1202 --hedef {args.db}\n"
              f"  (LLM istemez, saniyeler sürer. Kural tabanlı sahte özet "
              f"BASILMAZ — bkz. src/summarize/ozet.py)", file=sys.stderr)

    if sayi_bayat:
        print(f"\nBAYAT: DB korpusun {abs(fark)} belgesini "
              f"{'görmüyor' if fark > 0 else 'fazladan taşıyor'}.",
              file=sys.stderr)
        if fark > 0:
            print("  Chatbot, dashboard ve RAG bu belgeleri hiç görmez — sessizce.",
                  file=sys.stderr)
    if icerik_bayat:
        # Bu dal 2026-08-12'ye kadar YOKTU ve 48 belgelik bayatlık bu yüzden
        # görünmedi. Sayı kapısı tuttuğu hâlde içerik ayrışabilir.
        print(f"\nBAYAT (İÇERİK): {degisen} belgenin metni korpustaki hâlinden "
              f"farklı.", file=sys.stderr)
        if ozeti_bayat:
            print(f"  Bunların {ozeti_bayat} tanesinin ÖZETİ de bayat — sütun "
                  f"dolu olduğu için arayüzde normal görünür.", file=sys.stderr)
        print("  Kullanıcı, kaynağında artık bulunmayan bir değeri okuyabilir.",
              file=sys.stderr)

    print("\n  Düzeltme (özetleri KORUYARAK, ~dakikalar):", file=sys.stderr)
    print(f"    python -m scripts.build_demo_db --out {args.db}.yeni --force",
          file=sys.stderr)
    print(f"    python -m scripts.ozet_tasi --kaynak {args.db} "
          f"--hedef {args.db}.yeni", file=sys.stderr)
    print(f"    python -m scripts.build_summaries --db {args.db}.yeni --devam",
          file=sys.stderr)
    print(f"    mv {args.db} {args.db}.yedek && mv {args.db}.yeni {args.db}",
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
