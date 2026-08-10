"""Kaldırılan yetenek yoklamalarının yerine geçen sözleşme kapısı.

İlgili: ../src/api/main.py (`_field_rows`), ../scripts/build_summaries.py (`_yaz`)
        ../src/db/base.py (`RepositoryProtocol`, `ThreadSafeRepository`)
        ../src/db/repository.py, ../src/db/postgres.py

## Bu testlerin varlık sebebi

İki yerde "bu backend acaba şunu uyguluyor mu" diye çalışma zamanı yoklaması
vardı:

    src/api/main.py        inspect.signature(repo.query_fields) -> sozlesme_dahil?
    scripts/build_summaries.py  getattr(repo, "set_ozet", None) -> None mu?

Yoklamalar yazıldığında metotlar yalnız sözleşmede tanımlıydı, backend'ler
henüz uygulamamıştı. Sonradan iki backend de uyguladı ve dallar ÖLDÜ — ama
yanlarındaki metinler "bu backend'de henüz uygulanmamış" demeye devam etti.
Zararsız görünen ama YANILTICI bir durumdu: kodu okuyan kişi olmayan bir
eksiklik olduğunu sanıyordu.

Dallar 2026-08-10'da kaldırıldı. Bu dosya kaldırmayı GÜVENLİ tutar:

  1. Metotlar gerçekten dört yüzeyde de var mı (sözleşme, iş parçacığı
     güvenli sarmalayıcı, SQLite backend, Postgres backend). Biri kaybolursa
     yoklamasız çağrı `TypeError`/`AttributeError` ile düşerdi; kapı bunu
     üretimden önce yakalar.
  2. Ölü savunma geri gelmesin — iki dosyada da yoklama deseni aranır.
  3. Bayat metin geri gelmesin: bu iki dosyada, çözülmüş bir eksikliği açık
     gibi anlatan iş kalemi işaretçisi bulunmamalı.
"""

from __future__ import annotations

import ast
import inspect
import io
import sys
import tokenize
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.db.base import RepositoryProtocol, ThreadSafeRepository
from src.db.postgres import PostgresRepository
from src.db.repository import Repository

_KOK = Path(__file__).resolve().parents[1]

#: Yoklaması kaldırılan metotların bulunması gereken tüm yüzeyler.
YUZEYLER = (
    ("RepositoryProtocol", RepositoryProtocol),
    ("ThreadSafeRepository", ThreadSafeRepository),
    ("Repository (SQLite)", Repository),
    ("PostgresRepository", PostgresRepository),
)


class TestSozlesmeButunYuzeylerde(unittest.TestCase):
    """Yoklama kaldırıldı; yerine bu kapı geçti."""

    def test_query_fields_sozlesme_dahil_parametresini_tasir(self) -> None:
        for ad, sinif in YUZEYLER:
            with self.subTest(yuzey=ad):
                params = inspect.signature(sinif.query_fields).parameters
                self.assertIn(
                    "sozlesme_dahil", params,
                    f"{ad}.query_fields() kıyas süzgeci parametresini "
                    "kaybetti — /compare akit belgelerini sessizce tabloya "
                    "karıştırırdı")

    def test_sozlesme_dahil_ontanimi_ELEMEK(self) -> None:
        """Öntanım `False`: kıyas yolu süzgeci istemeden de almalı.

        `True` olsaydı süzgeci UNUTAN her çağrı sessizce akit belgelerini
        tabloya sokardı (adil kıyas garantisi).
        """
        for ad, sinif in YUZEYLER:
            with self.subTest(yuzey=ad):
                p = inspect.signature(sinif.query_fields).parameters
                self.assertIs(p["sozlesme_dahil"].default, False, ad)

    def test_set_ozet_her_yuzeyde_var(self) -> None:
        for ad, sinif in YUZEYLER:
            with self.subTest(yuzey=ad):
                self.assertTrue(
                    callable(getattr(sinif, "set_ozet", None)),
                    f"{ad}.set_ozet() yok — scripts/build_summaries.py "
                    "yazma adımında düşerdi")


class TestOluSavunmaGeriGELMEZ(unittest.TestCase):
    """Kaldırılan yoklama desenleri iki dosyaya geri sızmamalı."""

    HEDEFLER = ("src/api/main.py", "scripts/build_summaries.py")

    def _kaynak(self, ad: str) -> str:
        return (_KOK / ad).read_text(encoding="utf-8")

    def _kod_govdesi(self, ad: str) -> str:
        """Dosyanın docstring'leri BOŞALTILMIŞ hâli.

        Kaldırılan desenler docstring'lerde AYNEN alıntılanıyor ("burada şu
        yoklama vardı, şu yüzden kaldırıldı"). O kayıt kalmalı; aranan şey
        çalışan koddur. Docstring satırları boşaltılır, satır numaraları
        korunur.
        """
        govde = self._kaynak(ad)
        satirlar = govde.splitlines()
        for d in ast.walk(ast.parse(govde)):
            if not isinstance(d, (ast.Module, ast.FunctionDef,
                                  ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            ilk = d.body[0] if d.body else None
            if (isinstance(ilk, ast.Expr) and isinstance(ilk.value, ast.Constant)
                    and isinstance(ilk.value.value, str)):
                for i in range(ilk.lineno - 1, (ilk.end_lineno or ilk.lineno)):
                    satirlar[i] = ""
        return "\n".join(satirlar)

    def test_imza_yoklamasi_yok(self) -> None:
        """`inspect.signature(...).parameters` ile yetenek yoklanmamalı."""
        for ad in self.HEDEFLER:
            with self.subTest(dosya=ad):
                self.assertNotIn(
                    ").parameters", self._kod_govdesi(ad),
                    f"{ad}: depo yeteneği yeniden imzadan yoklanıyor — "
                    "sözleşme zaten bağlar")

    def test_set_ozet_getattr_yoklamasi_yok(self) -> None:
        for ad in self.HEDEFLER:
            with self.subTest(dosya=ad):
                self.assertNotIn('getattr(repo, "set_ozet"',
                                 self._kod_govdesi(ad), ad)

    def test_cozulmus_eksiklik_acik_gibi_anlatilmiyor(self) -> None:
        """Bu iki dosyada AÇIK iş kalemi işaretçisi kalmamalı.

        Bir kod satırının yanındaki işaretçi "burada eksik var" demektir.
        Eksiklik çözüldükten sonra duran işaretçi okuyanı olmayan bir boşluğa
        yönlendirir — ölçüldü: `campaign_text()` özet sütununu seçmiyor
        sanılıp arıza yanlış yerde arandı.

        Taranan yer YORUM SATIRLARI ve normal dizge sabitleridir. Docstring'ler
        MUAF: içlerindeki işaretçi bir iş kalemi değil, çözülmüş bir kusurun
        kaydıdır ("… buradaki işaretçi şunu diyordu, artık geçerli değil") ve
        o kayıt silinmemeli.
        """
        isaretci = "TODO" + "("
        for ad in self.HEDEFLER:
            with self.subTest(dosya=ad):
                govde = self._kaynak(ad)
                agac = ast.parse(govde)

                docstringler = set()
                for d in ast.walk(agac):
                    if isinstance(d, (ast.Module, ast.FunctionDef,
                                      ast.AsyncFunctionDef, ast.ClassDef)):
                        ds = ast.get_docstring(d, clean=False)
                        if ds:
                            docstringler.add(ds)

                bulgular = []
                for d in ast.walk(agac):
                    if (isinstance(d, ast.Constant)
                            and isinstance(d.value, str)
                            and d.value not in docstringler
                            and isaretci in d.value):
                        bulgular.append(f"{ad}:{d.lineno} (dizge)")

                okuyucu = io.StringIO(govde).readline
                for tok in tokenize.generate_tokens(okuyucu):
                    if tok.type == tokenize.COMMENT and isaretci in tok.string:
                        bulgular.append(f"{ad}:{tok.start[0]} (yorum)")

                self.assertEqual(
                    bulgular, [],
                    "çözülmüş eksiklik açık iş kalemi gibi duruyor: "
                    + "; ".join(bulgular))


if __name__ == "__main__":
    unittest.main()
