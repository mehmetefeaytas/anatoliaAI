"""Kullanıcıya GÖRÜNEN metinde iç belge referansı olmamalı.

İlgili: ../web/app/components/*.tsx, ../src/chatbot/safety.py, ../src/api/main.py

## Bu testin varlık sebebi

Jüri ekranında şu cümle görünüyordu:

    "Kâr payı oranı beklenen / gerçekleşmiş bir orandır… oran garanti anlamı
     taşımaz (CLAUDE.md §12)."

`CLAUDE.md §12` bizim iç geliştirme belgemizin bölüm numarası. Kullanıcı için
anlamsız, jüri için ise ürünün içinden geliştirme notu sızdığının işareti.
Yedi ayrı yerde vardı: chatbot feragatnamesinde, API'nin `fairness_note`
alanlarında ve dört arayüz bileşeninin görünür metninde.

Yorum satırlarında referans SERBESTTİR ve teşvik edilir — kodun neden öyle
olduğunu anlatır. Yasak olan yalnız **kullanıcının okuduğu dizge**.

## Nasıl ayırt ediliyor

- `.tsx`: JSX gövdesindeki düz metin taranır; `//` ve blok yorumları elenir.
- `.py`: yalnız DİZGE SABİTLERİ taranır (`ast` ile), docstring'ler hariç.
  Yorum satırları `ast` tarafından zaten görülmez.
"""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

_KOK = Path(__file__).resolve().parents[1]

#: Kullanıcıya görünen metinde geçmemesi gereken iç referanslar.
YASAK = re.compile(r"CLAUDE\.md|ANNOTATION_GUIDE\.md|TODO\(|docs/rapor/")

#: Kullanıcıya dönük metin üreten dosyalar.
PY_HEDEFLER = ("src/chatbot/safety.py", "src/chatbot/structured.py",
               "src/api/main.py", "src/comparison/compare.py")

_BLOK_YORUM = re.compile(r"/\*.*?\*/", re.DOTALL)
_SATIR_YORUM = re.compile(r"^\s*(//|\*).*$", re.MULTILINE)


class TestTsx(unittest.TestCase):
    """Arayüz bileşenlerinin GÖRÜNÜR metni."""

    def test_gorunur_metinde_ic_referans_YOK(self) -> None:
        bulgular = []
        for p in sorted((_KOK / "web" / "app").rglob("*.tsx")):
            govde = _BLOK_YORUM.sub("", p.read_text(encoding="utf-8"))
            govde = _SATIR_YORUM.sub("", govde)
            for m in YASAK.finditer(govde):
                satir = govde[:m.start()].count("\n") + 1
                bulgular.append(f"{p.relative_to(_KOK)}:~{satir} {m.group()}")
        self.assertEqual(
            bulgular, [],
            "kullanıcıya görünen metinde iç belge referansı: "
            + "; ".join(bulgular))


class TestPython(unittest.TestCase):
    """Sunucunun ÜRETTİĞİ metinler (feragatname, fairness_note, cevap şablonu)."""

    def test_dizge_sabitlerinde_ic_referans_YOK(self) -> None:
        bulgular = []
        for ad in PY_HEDEFLER:
            p = _KOK / ad
            if not p.exists():
                continue
            agac = ast.parse(p.read_text(encoding="utf-8"))
            # Docstring'ler muaf: kod okuyana yazılmışlardır, kullanıcıya değil.
            docstringler = set()
            for d in ast.walk(agac):
                if isinstance(d, (ast.Module, ast.FunctionDef,
                                  ast.AsyncFunctionDef, ast.ClassDef)):
                    ds = ast.get_docstring(d, clean=False)
                    if ds:
                        docstringler.add(ds)
            for d in ast.walk(agac):
                if not (isinstance(d, ast.Constant) and isinstance(d.value, str)):
                    continue
                if d.value in docstringler:
                    continue
                m = YASAK.search(d.value)
                if m:
                    bulgular.append(f"{ad}:{d.lineno} {m.group()}")
        self.assertEqual(
            bulgular, [],
            "kullanıcıya dönen dizgede iç belge referansı: "
            + "; ".join(bulgular))


class TestYakalar(unittest.TestCase):
    """Denetçi gerçek bir sızıntıyı bulmalı."""

    def test_yasak_desen_calisir(self) -> None:
        self.assertTrue(YASAK.search("oran garanti değildir (CLAUDE.md §12)."))
        self.assertTrue(YASAK.search("bkz. ANNOTATION_GUIDE.md §3"))
        self.assertFalse(YASAK.search("Kâr payı oranı garanti anlamı taşımaz."))


if __name__ == "__main__":
    unittest.main()
