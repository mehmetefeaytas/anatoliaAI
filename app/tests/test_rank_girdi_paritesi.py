"""`rank()` çağıran her yer, KAPILARIN ihtiyaç duyduğu alanları taşımak zorunda.

İlgili: ../src/comparison/compare.py (`rank`, `RANK_KAPI_ALANLARI`)
        ../src/api/routers/kiyas.py (`/compare`, `/bank-delta`)
        ../src/chatbot/structured.py

## Bu kapının varlık sebebi — AYNI TUZAK ÜÇ KEZ

`compare.rank()` kıyaslanabilirliği dört kapıyla belirler ve her kapı girdi
sözlüğünden AYRI bir alan okur:

    campaign_status -> süre kapısı        raw_value + bank_name -> koşul kapısı
    confidence      -> güven kapısı       canonical_value       -> birim/aralık

Kapılar eksik alanda **sessizce kapanır** — ve bu bilinçli: "bilinmiyor" ile
"düşük" aynı şey değildir, olmayan bir belirsizlik iddia edilmez. Ama aynı
tasarım, alanı taşımayı unutan çağıranı da sessizce ödüllendirir: kapı hiç
ateşlenmez, test yeşil kalır, ekran yanlış sıralar.

`src/api/main.py` bu tuzağa DÜŞTÜĞÜNÜ kendi yorumlarında iki kez yazıyor
(güven ve süre alanları için). 2026-08-11'de ÜÇÜNCÜSÜ oldu: koşul kapısı
eklendi, birim testleri geçti, `rank()` doğrudan çağrıldığında çalıştı — ama
`/compare` yanıtında "Mobilden yeni müşterilere özel %0" satırları hâlâ
`comparable=True` dönüyordu, çünkü `rank_input` sözlüğü `raw_value`
taşımıyordu.

Yorum yazmak yetmedi. Bu test kapıdır: `rank()`e sözlük listesi veren her
çağrı yeri, `RANK_KAPI_ALANLARI`nın tamamını taşımalıdır. Denetim AST
üzerinden yapılır — dize araması, yorum içindeki bir örneği gerçek kod
sanardı.
"""

from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.compare import RANK_KAPI_ALANLARI

KOK = Path(__file__).resolve().parents[1]

#: `rank()` çağıran modüller. Yeni bir çağıran eklendiğinde buraya da eklenir;
#: liste eksik kalırsa bu testin kendisi kör olur, bu yüzden aşağıda ayrıca
#: "başka çağıran var mı" taraması da yapılır.
TARANAN = ("src/api/routers/kiyas.py", "src/chatbot/structured.py")


def _sozluk_anahtarlari(dugum: ast.AST) -> list[set[str]]:
    """Bir ifadedeki sözlük değişmezlerinin anahtar kümeleri.

    Liste kavraması (`[{...} for r in rows]`) ve düz liste değişmezi
    (`[{...}, {...}]`) biçimlerinin ikisini de çözer.
    """
    out: list[set[str]] = []
    for alt in ast.walk(dugum):
        if isinstance(alt, ast.Dict):
            anahtar = {k.value for k in alt.keys
                       if isinstance(k, ast.Constant) and isinstance(k.value, str)}
            if anahtar:
                out.append(anahtar)
    return out


def _yerel_sozlukler(kapsam: ast.AST) -> dict[str, list[set[str]]]:
    """Kapsam içinde bir ADA bağlanan sözlük değişmezlerinin anahtarları.

    İki biçim çözülür ve İKİSİ DE gerekli:

        rank_input = [{...} for r in rows]       # atama
        rank_input.append({...})                 # ekleme

    ## Neden gerekli — testin KENDİ kör noktası

    İlk sürüm yalnız `rank(...)` çağrısının argümanındaki sözlükleri
    inceliyordu. `/compare` ise sözlüğü önce bir değişkende kuruyor ve
    `rank(rank_input, field)` diye çağırıyor — yani argüman bir `Name`, içinde
    sözlük YOK. Kapı, tam da kırılan çağrı yerini göremiyordu ve `raw_value`
    silinerek denendiğinde YEŞİL kaldı. Yeşil kalan bir kapı, kapı değildir.
    """
    out: dict[str, list[set[str]]] = {}
    for dugum in ast.walk(kapsam):
        if isinstance(dugum, ast.Assign):
            for hedef in dugum.targets:
                if isinstance(hedef, ast.Name):
                    out.setdefault(hedef.id, []).extend(
                        _sozluk_anahtarlari(dugum.value))
        elif (isinstance(dugum, ast.Call)
              and isinstance(dugum.func, ast.Attribute)
              and dugum.func.attr == "append"
              and isinstance(dugum.func.value, ast.Name)):
            out.setdefault(dugum.func.value.id, []).extend(
                _sozluk_anahtarlari(ast.Tuple(elts=list(dugum.args))))
    return out


def _rank_cagrilari(kaynak: str) -> list[ast.Call]:
    agac = ast.parse(kaynak)
    return [d for d in ast.walk(agac)
            if isinstance(d, ast.Call) and isinstance(d.func, ast.Name)
            and d.func.id == "rank" and d.args]


def _girdi_anahtarlari(kaynak: str) -> list[tuple[int, set[str]]]:
    """(satır, sözlük anahtarları) — hem satır içi hem değişkenli çağrılar."""
    agac = ast.parse(kaynak)
    yerel = _yerel_sozlukler(agac)
    out: list[tuple[int, set[str]]] = []
    for cagri in _rank_cagrilari(kaynak):
        arg = cagri.args[0]
        if isinstance(arg, ast.Name):
            kumeler = yerel.get(arg.id, [])
        else:
            kumeler = _sozluk_anahtarlari(arg)
        for k in kumeler:
            out.append((cagri.lineno, k))
    return out


class TestRankGirdiParitesi(unittest.TestCase):
    def test_sozluk_kuran_cagrilar_TUM_kapi_alanlarini_tasiyor(self) -> None:
        bulunan = 0
        for yol in TARANAN:
            kaynak = (KOK / yol).read_text(encoding="utf-8")
            for satir, anahtar in _girdi_anahtarlari(kaynak):
                bulunan += 1
                eksik = RANK_KAPI_ALANLARI - anahtar
                self.assertEqual(
                    eksik, set(),
                    f"{yol}:{satir} — `rank()`e verilen sözlük şu kapı "
                    f"alanlarını taşımıyor: {sorted(eksik)}. Eksik alanda "
                    "kapı SESSİZCE kapanır ve sıralama yanlış olur "
                    "(modül başlığındaki üç örnek).")
        self.assertGreater(bulunan, 0,
                           "hiç sözlük kuran `rank()` çağrısı bulunamadı — "
                           "test kör kalmış olabilir")

    def test_compare_ucu_DENETLENIYOR(self) -> None:
        """Kapının kendi kör noktasına karşı kapı.

        `/compare` sözlüğü bir değişkende kuruyor; ilk sürüm bunu göremiyordu
        ve `raw_value` silindiğinde yeşil kalmıştı. Bu test, o çağrı yerinin
        GERÇEKTEN denetlendiğini doğrular — denetim kapsamı sessizce
        daralırsa burası düşer.
        """
        kaynak = (KOK / "src" / "api" / "routers" / "kiyas.py").read_text(
            encoding="utf-8")
        anahtarlar = _girdi_anahtarlari(kaynak)
        self.assertGreaterEqual(
            len(anahtarlar), 2,
            "kiyas.py'de iki `rank()` çağrı yeri var (/compare ve "
            "/bank-delta); "
            "ikisi de denetlenmeli")

    def test_baska_cagiran_kalmadi(self) -> None:
        """`TARANAN` listesi eksikse bu test kör olur; taramayı doğrula."""
        cagiran = set()
        for p in (KOK / "src").rglob("*.py"):
            if _rank_cagrilari(p.read_text(encoding="utf-8")):
                cagiran.add(str(p.relative_to(KOK)))
        # `compare.py` kendi içinde `rank`i tanımlar, çağırmaz sayılmaz.
        cagiran.discard("src/comparison/compare.py")
        self.assertEqual(
            cagiran, set(TARANAN),
            "`rank()` çağıran modül kümesi değişmiş; TARANAN listesini "
            "güncelleyin, yoksa yeni çağıran denetlenmez")


class TestKapiAlanlariGercek(unittest.TestCase):
    """`RANK_KAPI_ALANLARI` gerçekten kapıların okuduğu alanlar mı."""

    def test_liste_bos_degil_ve_bilinen_alanlari_icerir(self) -> None:
        for alan in ("confidence", "campaign_status", "raw_value",
                     "canonical_value", "bank_name"):
            self.assertIn(alan, RANK_KAPI_ALANLARI)

    def test_rank_govdesi_her_alani_GERCEKTEN_okuyor(self) -> None:
        """Listeye ölü bir alan eklenirse çağıranlara boşuna yük binerdi."""
        kaynak = (KOK / "src" / "comparison" / "compare.py").read_text(
            encoding="utf-8")
        for alan in RANK_KAPI_ALANLARI:
            self.assertIn(f'"{alan}"', kaynak,
                          f"{alan} kapı listesinde ama `compare.py` onu "
                          "hiç okumuyor")


if __name__ == "__main__":
    unittest.main()
