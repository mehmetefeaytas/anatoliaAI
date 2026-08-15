"""Ortam probları — "bağımlılık yok" ile "kod bozuk" ayrımı.

İlgili: tests/test_api_startup.py (bu deseni ilk kuran dosya)
        docs/OFFLINE-KANIT.md (teslim imajında hangi bağımlılıkların
        BULUNMADIĞINI belgeleyen kanıt)

## Neden var

Teslim edilen imaj yalnız `requirements-api.txt` kurar. `git`, `httpx2` ve
üretilmiş bazı dosyalar orada **yoktur** ve bu bir kusur değil, kasıtlı bir
kapsam kararıdır: teslim edilen sistem test aracına ihtiyaç duymaz.

Bu ayrım ölçülmüş bir sorundan doğdu. 2026-08-15'te offline kanıtı 15 gün
sonra ilk kez koşuldu ve teslim imajının test paketi `errors=52` ile çöktü.
Hiçbiri gerçek kusur değildi — hepsi "bu ortamda o bağımlılık yok"tu. Ama
`ERROR` olarak sayıldıkları için kanıt adımı kırmızı yandı ve **gerçek bir
kusur çıksa aynı yığının içinde görünmezdi**.

Doğru sınıflandırma:

    bağımlılık yok  -> SKIP  (sayılır, raporlanır, gizlenmez)
    kod yanlış      -> FAIL  (kırmızı yanar)

## Atlamak gizlemek DEĞİLDİR — ama olabilir

Bu modül yalnız **ortam** probları taşır. Bir testi "şu an geçmiyor" diye
atlatmak için kullanılırsa, kapıyı kapatmak yerine kapıyı söker. Atlanan
test sayısı bu yüzden raporlanır (`README.md` "Test" satırı) ve
`scripts/kanit_tazeligi.py` onu bir iddia olarak denetler.
"""

from __future__ import annotations

import functools
import shutil
import unittest
from pathlib import Path

KOK = Path(__file__).resolve().parents[1]


@functools.cache
def git_var() -> bool:
    """`git` çalıştırılabilir mi? Teslim imajında YOKTUR."""
    return shutil.which("git") is not None


@functools.cache
def istemci_var() -> bool:
    """`starlette.testclient` kullanılabilir mi?

    `fastapi` kurulu olsa bile `TestClient` ayrıca `httpx2` ister ve o
    paket **yalnız test aracıdır**; teslim imajına bilerek girmez
    (`.github/workflows/ci.yml`, `test-with-deps` işi ayrıca kurar).

    Ad neden `testclient_var` DEĞİL: bu isimler test modüllerine import
    ediliyor ve `pytest` modül düzeyinde `test` ile başlayan her adı bir
    test işlevi sanıp toplar ("fixture 'sinif_ya_da_fonksiyon' not found"
    hatasıyla dört dosyada birden). Ölçüldü, 2026-08-15.
    """
    try:
        from starlette.testclient import TestClient  # noqa: F401
    except Exception:
        return False
    return True


@functools.cache
def arayuz_var() -> bool:
    """Next.js arayüz kaynakları (`web/app`) bu ortamda var mı?

    `Dockerfile.api` yalnız `src/ config/ data/ eval/ tests/ scripts/`
    kopyalar; `web/` **bilerek** girmez — API imajı arayüzü servis etmez.
    Arayüz metnini denetleyen testler CI'daki `test` işinde (depo tam
    olarak checkout edilir) ve yerel geliştirmede koşar.
    """
    return (KOK / "web" / "app").is_dir()


@functools.cache
def dosya_var(goreli: str) -> bool:
    """`app/` köküne göre bir dosya var mı? Üretilmiş artefaktlar için."""
    return (KOK / goreli).exists()


def git_gerekir(sinif_ya_da_fonksiyon):
    return unittest.skipUnless(
        git_var(),
        "git yok — bu ortamda sınanamaz (teslim imajı `git` içermez; "
        "denetim CI'da ve yerel geliştirmede koşar)")(sinif_ya_da_fonksiyon)


def istemci_gerekir(sinif_ya_da_fonksiyon):
    return unittest.skipUnless(
        istemci_var(),
        "httpx2 yok — API yüzeyi `test-with-deps` işinde sınanır")(
            sinif_ya_da_fonksiyon)


def arayuz_gerekir(sinif_ya_da_fonksiyon):
    return unittest.skipUnless(
        arayuz_var(),
        "web/ yok — Next.js arayüz kaynağı API imajına kopyalanmaz "
        "(`Dockerfile.api`); arayüz metni CI'daki `test` işinde ve yerel "
        "geliştirmede sınanır")(sinif_ya_da_fonksiyon)


def dosya_gerekir(goreli: str):
    return unittest.skipUnless(
        dosya_var(goreli),
        f"{goreli} yok — üretilmiş artefakt, teslim imajına kopyalanmaz "
        f"(`make sbom` / `make veri-seti` ile üretilir)")
