"""Alfabesi kaymış özetleri korpustan temizler — yeniden üret, olmazsa `NULL`.

İlgili: ../src/summarize/ozet.py (alfabe kapısı), ./build_summaries.py (üretim)
        ./ozet_geri_yukle.py (yedekleme/geri yükleme)
        CLAUDE.md §19 (halüsinasyon yasağı: bilgi yoksa null)

## Neden gerekli

Alfabe kapısı `ozet.py`'de BUNDAN SONRA üretilecek özetleri korur. Kapı
konulmadan önce üretilmiş korpus ise elde duruyor ve ekranda "AI özeti"
etiketiyle görünüyor. Ölçüm (2026-08-11, `data/demo.db`): 1751 özetin 67'si
Türkçenin kullanmadığı bir alfabeye taşmış — 65'i Çince ideogram taşıyor,
biri Kiril harfi, ikisi yalnız Çin noktalaması. Bu betik o kaydı düzeltir.

## Uydurma yok — üç seçenek, üçü de dürüst

Kirli bir özet için yapılabilecek üç şey vardır ve bu betik yalnız ikisini
yapar:

1. **Yeniden üret** (yapılır) — aynı belgeyi modele tekrar verip kapıdan geçen
   bir özet almak. Üretilen metin baştan sona modelindir.
2. **`NULL`'a çek** (yapılır) — denemeler tükendiğinde özet SİLİNİR. Arayüz
   özeti olmayan belgeyi zaten sorunsuz gösteriyor (`ozet.py`: özet hiçbir
   karar yolunun girdisi değildir).
3. **Elle düzelt / çevir / kirli parçayı kırp** (YAPILMAZ) — kaymış harfleri
   silip kalanı özet diye sunmak, modelin yazmadığı bir metni model çıktısı
   gibi göstermektir. Bir cümlenin yarısını atmak anlamını da değiştirir.

## Sonsuz döngü yok: sıcaklık merdiveni + sabit tavan

`OllamaClient` varsayılan sıcaklığı 0.0'dır, yani üretim GREEDY ve
belirlenimcidir: aynı belgeyi aynı sıcaklıkta yeniden sormak bayt-aynı kirli
çıktıyı geri getirir ve deneme sayısı ne olursa olsun sonuç değişmez. Bu
yüzden her deneme sıcaklığı bir kademe yükseltir (`SICAKLIK_MERDIVENI`):
ikinci deneme ilkinden farklı bir örnekleme yolu izler.

Merdiven sonlu, deneme tavanı sabittir (`VARSAYILAN_DENEME`). Tavan dolduğunda
kayıt `NULL`'a çekilir ve raporlanır — koşu her hâlükârda biter.

## Kullanım

    # 1) ÖNCE yedek (bu betik DB'ye yazar)
    .venv/bin/python -m scripts.ozet_geri_yukle --yedekle \\
        --db data/demo.db --yedek data/ozet-yedegi.json

    # 2) Yazmadan tara — kaç kayıt kirli, hangi alfabe
    .venv/bin/python -m scripts.ozet_dil_temizligi --db data/demo.db --kuru

    # 3) Temizle (yerel model açık olmalı)
    OLLAMA_NUM_CTX=8192 LLM_BACKEND=ollama \\
        .venv/bin/python -m scripts.ozet_dil_temizligi --db data/demo.db

    # Model kapalıyken: yeniden üretme YOK, kirli kayıtlar yalnızca NULL'a çekilir
    .venv/bin/python -m scripts.ozet_dil_temizligi --db data/demo.db --yalniz-null

Çıkış kodları: 0 tamam · 2 hedef veri tabanı yok · 3 yerel model kapalı
(`--yalniz-null` verilmedi).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.repository import Repository
from src.extraction.llm.extractor import default_extractor
from src.summarize.ozet import (
    MAKS_GIRDI_KARAKTER,
    SEBEP_YABANCI_ALFABE,
    alfabe_disi_karakterler,
    llm_hazir,
    ozetle,
)

#: Deneme başına sıcaklık. İlk deneme belirlenimci (0.0) — kaymanın tesadüfi
#: mi yoksa bu belgede kararlı mı olduğunu gösterir. Sonraki denemeler
#: örneklemeyi açar, aksi halde aynı çıktı tekrarlanırdı.
SICAKLIK_MERDIVENI: tuple[float, ...] = (0.0, 0.35, 0.7)

#: Bir belge için azami deneme. Merdivenin boyundan uzun olamaz: fazlası aynı
#: sıcaklıkta tekrar demek olurdu ve zaman yakmaktan başka işe yaramazdı.
VARSAYILAN_DENEME = len(SICAKLIK_MERDIVENI)

#: Kaç belgede bir depoya yazılacağı — `build_summaries.YAZMA_PARCASI` ile aynı
#: gerekçe: uzun koşu tek bir kesintide tüm ilerlemesini kaybetmesin.
YAZMA_PARCASI = 20


def kirli_kayitlar(repo: Repository) -> list[dict[str, Any]]:
    """Alfabesi kaymış özeti olan kampanyalar — sırayla, kanıtıyla.

    Dönen her kayıt `disari` alanında kaymanın KANITINI taşır (metinde geçen
    Türkçe alfabe dışı karakterler). Rapor bu kanıtı basar; "67 kayıt kirliydi"
    demek, hangi karakterlerin yakalandığını göstermeden yarım bir iddiadır.
    """
    out: list[dict[str, Any]] = []
    for camp in repo.all_campaigns():
        ozet = (camp.get("ozet") or "").strip()
        if not ozet:
            continue
        disari = alfabe_disi_karakterler(ozet)
        if disari:
            out.append({"id": int(camp["id"]), "ozet": ozet,
                        "raw_text": camp.get("raw_text") or "",
                        "disari": disari})
    return out


def _sicaklik_ayarla(llm: Any, deger: float) -> Optional[float]:
    """İstemcinin sıcaklığını ayarlar; eski değeri döndürür (yoksa None).

    `getattr`/`setattr` ile yoklanır çünkü sıcaklık istemciye ait bir ayardır
    ve her istemcide bulunmak zorunda değildir (sahte istemciler, ileride
    başka bir sunucu). Ayar yoksa denemeler yine koşar — yalnız çeşitlenmez.
    """
    istemci = getattr(llm, "client", None)
    if istemci is None or not hasattr(istemci, "temperature"):
        return None
    eski = istemci.temperature
    istemci.temperature = deger
    return eski


def yeniden_uret(camp: dict[str, Any], llm: Any, *, denemeler: int,
                 maks_karakter: int = MAKS_GIRDI_KARAKTER) -> dict[str, Any]:
    """Tek belge için kapıdan geçen bir özet arar.

    Dönen sözlük: `ozet` (None = bulunamadı), `deneme` (kaç kez denendi),
    `sebepler` (her denemenin `OzetSonucu.sebep` değeri — boş özet, alfabe
    kayması ve ağ hatası birbirinden ayrı görünsün diye).
    """
    sebepler: list[str] = []
    onceki: Optional[float] = None
    try:
        for i in range(max(1, denemeler)):
            sicaklik = SICAKLIK_MERDIVENI[min(i, len(SICAKLIK_MERDIVENI) - 1)]
            geri = _sicaklik_ayarla(llm, sicaklik)
            if onceki is None:
                onceki = geri
            sonuc = ozetle(camp.get("raw_text") or "", llm,
                           maks_karakter=maks_karakter)
            if sonuc.uretildi and sonuc.ozet:
                return {"ozet": sonuc.ozet, "deneme": i + 1, "sebepler": sebepler}
            sebepler.append(sonuc.sebep or "bilinmiyor")
    finally:
        if onceki is not None:
            _sicaklik_ayarla(llm, onceki)
    return {"ozet": None, "deneme": len(sebepler), "sebepler": sebepler}


def calistir(db_yolu: str, *, kuru: bool = False, yalniz_null: bool = False,
             denemeler: int = VARSAYILAN_DENEME,
             maks_karakter: int = MAKS_GIRDI_KARAKTER,
             llm: Any = None, parca: int = YAZMA_PARCASI,
             ilerleme=None) -> dict:
    """Korpusu tarar, kirli özetleri yeniden üretir ya da `NULL`'a çeker."""
    if llm is None and not yalniz_null:
        llm = default_extractor()
    repo = Repository(db_yolu)
    try:
        basladi = time.time()
        toplam = len(repo.all_campaigns())
        kirli = kirli_kayitlar(repo)

        bekleyen: dict[int, Optional[str]] = {}
        yazilan = 0
        yeniden = 0
        null_cekilen = 0
        deneme_dagilimi: dict[str, int] = {}
        sebepler: dict[str, int] = {}
        alfabe_kaniti: dict[str, int] = {}
        kayitlar: list[dict[str, Any]] = []

        def bosalt() -> None:
            nonlocal bekleyen, yazilan
            if kuru or not bekleyen:
                return
            yazilan += int(repo.set_ozet(bekleyen))
            bekleyen = {}

        for i, camp in enumerate(kirli, start=1):
            for ch in camp["disari"]:
                anahtar = f"U+{ord(ch):04X}"
                alfabe_kaniti[anahtar] = alfabe_kaniti.get(anahtar, 0) + 1

            if yalniz_null:
                sonuc = {"ozet": None, "deneme": 0, "sebepler": []}
            else:
                sonuc = yeniden_uret(camp, llm, denemeler=denemeler,
                                     maks_karakter=maks_karakter)
            for sebep in sonuc["sebepler"]:
                sebepler[sebep] = sebepler.get(sebep, 0) + 1

            bekleyen[camp["id"]] = sonuc["ozet"]
            if sonuc["ozet"] is None:
                null_cekilen += 1
                anahtar = "null"
            else:
                yeniden += 1
                anahtar = f"{sonuc['deneme']}. denemede"
            deneme_dagilimi[anahtar] = deneme_dagilimi.get(anahtar, 0) + 1
            kayitlar.append({
                "id": camp["id"],
                "eski_ozet": camp["ozet"][:160],
                "disari": "".join(camp["disari"])[:40],
                "sonuc": "yeniden_uretildi" if sonuc["ozet"] else "null",
                "deneme": sonuc["deneme"],
            })

            if parca > 0 and i % parca == 0:
                bosalt()
                if ilerleme is not None:
                    ilerleme(i, len(kirli), yazilan)

        bosalt()
        return {
            "db": db_yolu,
            "korpus_belge": toplam,
            "kirli_ozet": len(kirli),
            "yeniden_uretilen": yeniden,
            "null_cekilen": null_cekilen,
            "yazilan": yazilan,
            "kuru": kuru,
            "yalniz_null": yalniz_null,
            "deneme_tavani": denemeler,
            "deneme_dagilimi": deneme_dagilimi,
            "denemelerin_sebebi": sebepler,
            # Kaç denemenin ALFABE KAPISINDAN döndüğü. Ağ hatasıyla (`llm_hatasi`)
            # aynı sepete konsaydı "model bu belgede ısrarla dil değiştiriyor"
            # ile "servis düştü" ayırt edilemezdi.
            "alfabe_kapisindan_dusen": sebepler.get(SEBEP_YABANCI_ALFABE, 0),
            "alfabe_kaniti": alfabe_kaniti,
            "kayitlar": kayitlar,
            "sure_sn": round(time.time() - basladi, 2),
            "llm_acik": bool(llm is not None and llm_hazir(llm)),
        }
    finally:
        repo.close()


def _rapor_bas(rapor: dict) -> None:
    print(f"veri tabanı        : {rapor['db']}")
    print(f"korpus belge       : {rapor['korpus_belge']}")
    print(f"kirli özet         : {rapor['kirli_ozet']}")
    print(f"yeniden üretilen   : {rapor['yeniden_uretilen']}")
    print(f"NULL'a çekilen     : {rapor['null_cekilen']}")
    print(f"yazılan satır      : {rapor['yazilan']}"
          + ("  (kuru koşu — DB'ye yazılmadı)" if rapor["kuru"] else ""))
    print(f"deneme tavanı      : {rapor['deneme_tavani']}")
    print(f"süre (sn)          : {rapor['sure_sn']}")
    if rapor["deneme_dagilimi"]:
        print("sonuç dağılımı     :")
        for ad, adet in sorted(rapor["deneme_dagilimi"].items()):
            print(f"  {ad:<24} {adet}")
    if rapor["denemelerin_sebebi"]:
        print("düşen denemeler    :")
        for sebep, adet in sorted(rapor["denemelerin_sebebi"].items()):
            print(f"  {sebep:<24} {adet}")
        print(f"  (bunun {rapor['alfabe_kapisindan_dusen']}'i alfabe kapısı)")
    if rapor["alfabe_kaniti"]:
        ilk = sorted(rapor["alfabe_kaniti"].items(),
                     key=lambda kv: (-kv[1], kv[0]))[:12]
        print("alfabe kanıtı      : "
              + ", ".join(f"{k}×{v}" for k, v in ilk))
    print(f"UYDURMA YOK        : kirli özet düzeltilmedi; {rapor['yeniden_uretilen']} "
          f"yeniden üretildi, {rapor['null_cekilen']} silindi")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--db", default="data/demo.db", help="hedef SQLite dosyası")
    ap.add_argument("--kuru", action="store_true",
                    help="tara ve raporla ama veri tabanına YAZMA")
    ap.add_argument("--yalniz-null", action="store_true",
                    help="yeniden üretme; kirli özetleri doğrudan NULL'a çek")
    ap.add_argument("--deneme", type=int, default=VARSAYILAN_DENEME,
                    help=f"belge başına azami deneme (öntanım {VARSAYILAN_DENEME})")
    ap.add_argument("--maks-karakter", type=int, default=MAKS_GIRDI_KARAKTER,
                    help="modele verilecek en fazla karakter")
    ap.add_argument("--parca", type=int, default=YAZMA_PARCASI,
                    help=f"kaç belgede bir yazılsın (öntanım {YAZMA_PARCASI})")
    ap.add_argument("--json-report", default=None, help="raporu JSON olarak yaz")
    a = ap.parse_args(argv)

    # Ollama varsayılan bağlamı 2048'dir ve fazlasını SESSİZCE baştan kırpar.
    os.environ.setdefault("OLLAMA_NUM_CTX", "8192")

    if not os.path.exists(a.db):
        print(f"HATA: veri tabanı yok: {a.db}", file=sys.stderr)
        return 2

    llm = None
    if not a.yalniz_null:
        llm = default_extractor()
        if not llm_hazir(llm):
            print("HATA: yerel model kapalı. Kirli özetler yeniden ÜRETİLEMEZ "
                  "ve elle düzeltilmez (src/summarize/ozet.py). Açmak için: "
                  "LLM_BACKEND=ollama (model: qwen2.5:7b-instruct). Yalnızca "
                  "silmek için: --yalniz-null.", file=sys.stderr)
            return 3

    def _ilerleme(islenen: int, hedef: int, yazilan: int) -> None:
        print(f"  ... {islenen}/{hedef} kayıt · {yazilan} satır yazıldı",
              flush=True)

    rapor = calistir(a.db, kuru=a.kuru, yalniz_null=a.yalniz_null,
                     denemeler=a.deneme, maks_karakter=a.maks_karakter,
                     llm=llm, parca=a.parca, ilerleme=_ilerleme)
    _rapor_bas(rapor)
    if a.json_report:
        with open(a.json_report, "w", encoding="utf-8") as fh:
            json.dump(rapor, fh, ensure_ascii=False, indent=2)
        print(f"JSON rapor         : {a.json_report}")
    # Yeniden üretilemeyen kayıt bir KOŞU hatası değildir: modelin o belgede
    # ısrarla dil değiştirdiğinin ölçülmüş sonucudur ve raporda görünür.
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
