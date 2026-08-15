"""Veri seti paketini Hugging Face Hub'a yükler — VARSAYILAN KURU KOŞU.

İlgili: scripts/veri_seti_paketle.py (yüklenecek paketi üreten betik)
        data/yayin/anatolia-ai-gold/ (varsayılan girdi dizini)

## ⛔ `huggingface_hub` neden `requirements.txt`'te DEĞİL

Teslim edilen sistem bu paketi **kullanmıyor**. `requirements.txt` çalışan
sistemin bağımlılık listesidir (şartname §9 "bağımlılıkların eksiksiz
listesi") ve oraya konan her satır iki şey iddia eder: "bu paket çalışma
zamanında gereklidir" ve "bu paketin lisansı denetlenmiştir".

`huggingface_hub` ikisini de karşılamaz:

  * **Çalışma zamanında gerekmez.** Sistem tamamen çevrimdışı çalışır
    (CLAUDE.md §1, `docs/OFFLINE-KANIT.md`). Ağa çıkan bir kütüphaneyi
    teslim imajına koymak, "internetsiz çalışır" iddiasını zayıflatır —
    üstelik `docker-compose up` bu betiği hiç çağırmaz.
  * **Bu bir YAYIN aracıdır**, ürünün parçası değil. Yayın araçları
    (`pip-licenses`, `cyclonedx-py`, bu betik) geliştiricinin makinesinde
    ad hoc kurulur; `Makefile` hedefleri de böyle çalışır.

Bu yüzden paket **eksikse kurulmaz, açık bir hata verilir** ve kurulum
komutu gösterilir. Sessizce `pip install` çalıştırmak, bağımlılık listesini
gizlice büyütmek olurdu.

## Sır yönetimi (CLAUDE.md §19 — "repoda API anahtarı olmasın")

Token **yalnızca** `HF_TOKEN` ortam değişkeninden okunur. Betikte:

  * `--token` gibi bir bayrak **yoktur** — komut satırı argümanları `ps`
    çıktısında ve kabuk geçmişinde görünür.
  * Token hiçbir yere **yazılmaz**: log yok, dosya yok, hata mesajı yok.
    Yalnızca "var/yok" ve uzunluğu bildirilir.
  * `huggingface_hub` istisnaları **yeniden paketlenir**; kütüphanenin
    kendi mesajı token parçası taşıyabileceği için olduğu gibi basılmaz.

## Kuru koşu neden VARSAYILAN

Yükleme geri alınamaz: indirilen kopya geri çağrılamaz ve yanlış bir
dataset card gerçek bir dürüstlük hatasına dönüşür. Bu yüzden betiğin
varsayılan davranışı **ne yükleyeceğini göstermektir**. Gerçek yükleme
açık bir bayrak (`--gercekten-yukle`) VE etkileşimli onay ister.

## Kullanım

    # 1) Ne yükleneceğini gör (varsayılan, ağa ÇIKMAZ)
    .venv/bin/python -m scripts.veri_seti_yukle

    # 2) Gerçekten yükle
    export HF_TOKEN=hf_...            # kabuk geçmişine düşmesin diye ` ` ile başlat
    .venv/bin/python -m scripts.veri_seti_yukle \\
        --depo anatolia-ai/katilim-bankaciligi-gold --gercekten-yukle
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

VARSAYILAN_DIZIN = "data/yayin/anatolia-ai-gold"
# Token `mehmetefeaytas` kullanıcısına ait ve hiçbir organizasyona üye
# değil (2026-08-15 `whoami` ile doğrulandı), bu yüzden hedef kullanıcı
# ad alanıdır. GitHub deposu da aynı hesapta — köken tutarlı kalıyor.
# Bir `anatolia-ai` organizasyonu açılırsa depo taşınabilir; HF eski
# adresten yönlendirme bırakır.
VARSAYILAN_DEPO = "mehmetefeaytas/katilim-bankaciligi-kampanya-gold"
TOKEN_DEGISKENI = "HF_TOKEN"

# Pakette bulunması ZORUNLU dosyalar. Eksikse yükleme başlamaz: dataset
# card'sız bir veri seti, dürüstlük uyarılarını taşımadan yayılır.
ZORUNLU = ("README.md", "LISANS.md", "gold.round1.jsonl", "gold.v2.jsonl",
           "train.jsonl", "val.jsonl", "test.jsonl")

KURULUM_MESAJI = f"""HATA: `huggingface_hub` kurulu değil.

Bu paket BİLEREK `requirements.txt`'e konmamıştır — teslim edilen sistem onu
kullanmaz, yalnızca bu yayın aracı kullanır (gerekçe: betik başlığı).

Kurmak için:

    {Path(sys.executable).parent}/pip install huggingface_hub

Sonra bu komutu tekrar çalıştırın. Kurulum yapmak istemiyorsanız kuru koşu
(varsayılan mod) `huggingface_hub` OLMADAN da çalışır — yalnızca gerçek
yükleme bu paketi gerektirir."""


def sha256(yol: Path) -> str:
    ozet = hashlib.sha256()
    with yol.open("rb") as h:
        for parca in iter(lambda: h.read(1 << 20), b""):
            ozet.update(parca)
    return ozet.hexdigest()


def _boyut(bayt: int) -> str:
    birim = float(bayt)
    for ad in ("B", "KB", "MB", "GB"):
        if birim < 1024 or ad == "GB":
            return f"{birim:.1f} {ad}" if ad != "B" else f"{int(birim)} B"
        birim /= 1024
    return f"{birim:.1f} GB"


def envanter(dizin: str) -> list[dict]:
    """Yüklenecek dosyaların listesi: yol + boyut + sha256.

    Gizli dosyalar ve `__pycache__` dışlanır; alfabetik sıralanır ki iki
    koşunun çıktısı diff'lenebilsin.
    """
    kok = Path(dizin)
    if not kok.is_dir():
        raise FileNotFoundError(
            f"paket dizini yok: {kok}\n"
            "Önce paketi üretin:  .venv/bin/python -m scripts.veri_seti_paketle")
    dosyalar = []
    for yol in sorted(kok.rglob("*")):
        if not yol.is_file():
            continue
        if any(p.startswith(".") or p == "__pycache__" for p in yol.relative_to(kok).parts):
            continue
        dosyalar.append({
            "ad": str(yol.relative_to(kok)),
            "bayt": yol.stat().st_size,
            "sha256": sha256(yol),
        })
    return dosyalar


def eksikler(dosyalar: list[dict]) -> list[str]:
    var = {d["ad"] for d in dosyalar}
    return [ad for ad in ZORUNLU if ad not in var]


def token_durumu() -> tuple[bool, str]:
    """Token'ın KENDİSİNİ değil, yalnızca durumunu döndürür.

    Değer hiçbir koşulda çağırana verilmez — bu fonksiyonun dönüşü doğrudan
    ekrana basılıyor.
    """
    ham = os.environ.get(TOKEN_DEGISKENI) or ""
    token = ham.strip()
    if not token:
        return False, f"{TOKEN_DEGISKENI} tanımlı değil"
    return True, f"{TOKEN_DEGISKENI} tanımlı ({len(token)} karakter)"


def hub_var() -> bool:
    """`huggingface_hub` kurulu mu — İÇE AKTARMADAN bakar.

    İçe aktarma modül tepesinde değil: kuru koşunun paket olmadan da
    çalışması gerekiyor (bu betiğin ana kullanım biçimi kuru koşudur).
    Buradaki kontrol ayrıca ONAY SORULMADAN ÖNCE koşar — kullanıcıya
    "yukle" yazdırıp sonra "paket kurulu değil" demek kötü bir sıralamadır.
    """
    from importlib.util import find_spec
    return find_spec("huggingface_hub") is not None


def _yukle(dizin: str, depo: str, ozel: bool) -> None:
    """Gerçek yükleme."""
    try:
        from huggingface_hub import HfApi
    except ImportError:
        raise SystemExit(KURULUM_MESAJI) from None

    token = (os.environ.get(TOKEN_DEGISKENI) or "").strip()
    api = HfApi(token=token)
    try:
        api.create_repo(repo_id=depo, repo_type="dataset",
                        private=ozel, exist_ok=True)
        api.upload_folder(folder_path=dizin, repo_id=depo,
                          repo_type="dataset",
                          commit_message="Anatolia AI gold veri seti")
    except Exception as hata:
        # Kütüphanenin mesajı istek başlıklarını (dolayısıyla token'ı)
        # taşıyabilir. Tür adı tanı için yeter; gövde basılmaz.
        raise SystemExit(
            f"HATA: yükleme başarısız ({type(hata).__name__}). "
            "Ayrıntı bilerek basılmıyor — hata gövdesi token taşıyabilir. "
            f"Depo adını ve {TOKEN_DEGISKENI} yetkisini kontrol edin.") from None


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Veri seti paketini Hugging Face'e yükler (varsayılan: kuru koşu).")
    ap.add_argument("--dizin", default=VARSAYILAN_DIZIN, help="paket dizini")
    ap.add_argument("--depo", default=VARSAYILAN_DEPO, help="hedef HF dataset deposu")
    ap.add_argument("--ozel", action="store_true",
                    help="depoyu private aç (varsayılan: public)")
    ap.add_argument("--kuru", action="store_true", default=True,
                    help="kuru koşu — VARSAYILAN, ağa çıkmaz")
    ap.add_argument("--gercekten-yukle", dest="gercek", action="store_true",
                    help="kuru koşuyu kapatır ve GERÇEKTEN yükler (onay ister)")
    ap.add_argument("--onaysiz", action="store_true",
                    help="etkileşimli onayı atlar; yalnız --gercekten-yukle ile anlamlı")
    a = ap.parse_args(argv)

    try:
        dosyalar = envanter(a.dizin)
    except FileNotFoundError as hata:
        print(f"HATA: {hata}")
        return 1

    toplam = sum(d["bayt"] for d in dosyalar)
    print(f"paket   : {a.dizin}")
    print(f"hedef   : https://huggingface.co/datasets/{a.depo}"
          f"  ({'private' if a.ozel else 'public'})")
    var, durum = token_durumu()
    print(f"token   : {durum}")
    print(f"dosya   : {len(dosyalar)} · toplam {_boyut(toplam)}")
    print("")
    print(f"{'DOSYA':<26} {'BOYUT':>10}  SHA256")
    for d in dosyalar:
        print(f"{d['ad']:<26} {_boyut(d['bayt']):>10}  {d['sha256']}")
    print("")

    eksik = eksikler(dosyalar)
    if eksik:
        print(f"HATA: zorunlu dosya eksik: {', '.join(eksik)}")
        print("Paketi yeniden üretin: .venv/bin/python -m scripts.veri_seti_paketle")
        return 1

    if not a.gercek:
        print("KURU KOŞU — hiçbir şey yüklenmedi, ağa çıkılmadı.")
        print("Gerçekten yüklemek için: --gercekten-yukle")
        if not hub_var():
            print("")
            print("NOT: `huggingface_hub` kurulu değil — kuru koşu için gerekmiyor, "
                  "gerçek yükleme için gerekiyor.")
        return 0

    # Onay SORULMADAN önce: eksik paketle "yukle" yazdırmak anlamsız.
    if not hub_var():
        print(KURULUM_MESAJI)
        return 1

    if not var:
        print(f"HATA: {TOKEN_DEGISKENI} tanımlı değil. Token YALNIZCA ortam "
              "değişkeninden okunur; bayrak olarak verilemez (kabuk geçmişine düşer).")
        print(f"    export {TOKEN_DEGISKENI}=...   # satırı boşlukla başlatın")
        return 1

    if not a.onaysiz:
        print(f"⚠️  {len(dosyalar)} dosya ({_boyut(toplam)}) "
              f"{'private' if a.ozel else 'PUBLIC'} olarak yüklenecek.")
        print("Yükleme geri alınamaz: indirilen kopya geri çağrılamaz.")
        try:
            cevap = input("Devam etmek için 'yukle' yazın: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\niptal edildi.")
            return 1
        if cevap != "yukle":
            print("iptal edildi.")
            return 1

    _yukle(a.dizin, a.depo, a.ozel)
    print(f"yüklendi: https://huggingface.co/datasets/{a.depo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
