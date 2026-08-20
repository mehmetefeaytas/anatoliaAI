"""Ortografik değişmezlik — BÜYÜK HARFLE yazılmış belge aynı değeri vermeli.

İlgili: ../src/extraction/rules/extract.py (`_IC_AYIRAC_RE`, `_kosul_parcalari`),
        ../src/preprocessing/clean.py (`tr_upper`, `split_sentences`),
        ../eval/properties.py (P2 — `P2_buyuk_harf_deger_degisti`),
        ../docs/rapor/liste-alanlari-iyilestirme.md (ölçüm defteri)

## Neden bu dosya var — kök neden ve ürün yüzeyindeki etki

`eval.properties` P2 değişmezi şunu söyler: belge büyük harfe çevrildiğinde
çıkarılan değer DEĞİŞMEMELİ. Bu kozmetik bir test değil — TEKNOFEST rubriğinin
model başarısı kaleminde *"farklı ifade biçimlerini doğru yorumlayabilmesi"*
maddesi var ve banka belgelerinin büyük bölümü (taahhütname, bilgilendirme
formu, ücret tarifesi) BÜYÜK HARFLE yazılıdır.

`kampanya_kosullari` iyileştirmesi (kalem F1 0,204 -> 0,520) bu değişmezi
kırdı. Birleşik blok bölücüsünün tire ayıracı `\\s+-(?=[A-ZÇĞİÖŞÜ])` yazılıydı,
yani "boşluk + tire + BÜYÜK harf". Bu desen madde iminin GÖRÜNTÜSÜNÜ tarif
ediyordu ama sonucu ORTOGRAFİYE bağlıyordu ve 1.782 belgelik korpusta üç
belgede ihlal üretti:

    normal : "… irade beyanının (icap -kabul) bulunması gerekir."
             -> 'kabul' küçük, ayıraç ateşlemez, koşul TEK PARÇA
    BÜYÜK  : "… İRADE BEYANININ (İCAP -KABUL) BULUNMASI GEREKİR."
             -> 'KABUL' büyük, ayıraç ateşler, koşul ORTADAN KESİLİR;
                listeye 'KABUL) BULUNMASI GEREKİR.' düşer

Ürün yüzeyindeki zarar somut: panelde ve chatbot cevabında koşul olarak
yarım bir cümle görünür ve kaynak vurgulaması cümlenin ortasını gösterir.

## Düzeltmenin biçimi

Ayıraç harf büyüklüğü yerine ÖNCEKİ NOKTALAMAYA bağlandı
(`(?<=[.!?:])\\s+-\\s*`): madde imi bir cümle/başlık bitiminden sonra gelir,
birleşik sözcük tiresi ise harften sonra gelir. Gerekçe ve çürütülen
alternatiflerin ölçümü `_IC_AYIRAC_RE`nin başındaki blokta yazılı.

## Bu dosya neyi kapıda tutuyor

1. Üç gerçek ihlal belgesi — ham dosyalarla, ARŞİVDEN okunarak.
2. Sınıfın kendisi — sentetik olarak, ham dosyalar taşınsa bile test kalır.
3. Belgelenmiş madde imi işlevi — değişmez, ayıracı ATMAKLA da geçirilebilirdi;
   o "düzeltme" bölme işlevini kaybettirirdi.

Ham korpus koşumun bir parçası değildir (CI'da `data/raw` var, temiz klonda
yok); dosya yoksa ilgili test ATLANIR, sessizce geçmez.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from eval.properties import check_orthographic_invariance
from src.extraction.rules.extract import extract_kampanya_kosullari
from src.preprocessing.clean import normalize_text, tr_upper

HAM = Path(__file__).resolve().parents[1] / "data" / "raw"

#: P2'yi kıran üç belge (1.782 belgelik korpus, 2026-08-20 koşumu).
IHLAL_BELGELERI = (
    "albaraka/docs/bilgilendirme-formu-icare-is-gucu-hizmet-kiralamasi.txt",
    "albaraka/docs/bilgilendirme-formu-murabaha.txt",
    "turkiye-emlak-katilim/docs/"
    "qr-kur-referanslarina-iliskin-musteri-taahhutnamesi-pdf.txt",
)


def _kosullar(metin: str) -> list[str]:
    alan = extract_kampanya_kosullari(normalize_text(metin))
    return list(alan.canonical_value) if alan else []


class TestUcGercekIhlalBelgesi(unittest.TestCase):
    """Değişmezi kıran üç belge, BÜYÜK harfte aynı koşul listesini vermeli."""

    def test_ham_belgelerde_kosul_listesi_degismiyor(self) -> None:
        for yol in IHLAL_BELGELERI:
            dosya = HAM / yol
            if not dosya.exists():
                self.skipTest(f"ham korpus yok: {yol}")
            metin = dosya.read_text(encoding="utf-8", errors="replace")
            with self.subTest(belge=yol):
                normal = _kosullar(metin)
                buyuk = _kosullar(tr_upper(metin))
                self.assertEqual(
                    len(normal), len(buyuk),
                    "kalem sayısı harf büyüklüğüne göre değişti")
                for a, b in zip(normal, buyuk, strict=True):
                    self.assertEqual(
                        tr_upper(a), b,
                        "koşul kalemi BÜYÜK harfte farklı sınırdan kesildi")

    def test_P2_denetimi_ihlal_vermiyor(self) -> None:
        """Kapı ÖLÇÜTÜN KENDİSİYLE kurulur, kopyasıyla değil.

        `eval.properties.check_orthographic_invariance` CI'da koşan denetimin
        ta kendisidir. Test onu doğrudan çağırır: burada geçip orada düşmesi
        mümkün olmasın (ölçüt kopyalanırsa iki taraf zamanla ayrışır).
        """
        for yol in IHLAL_BELGELERI:
            dosya = HAM / yol
            if not dosya.exists():
                self.skipTest(f"ham korpus yok: {yol}")
            metin = normalize_text(
                dosya.read_text(encoding="utf-8", errors="replace"))
            with self.subTest(belge=yol):
                ihlaller = check_orthographic_invariance(metin, doc_id=yol)
                self.assertEqual(
                    [], [v.prop for v in ihlaller],
                    f"P2 ihlali: {[(v.prop, v.before, v.after) for v in ihlaller]}")


class TestSinifSentetik(unittest.TestCase):
    """Ham dosyalara bağlı OLMAYAN sınıf testi — kusur biçimini kilitler.

    `data/raw` temiz klonda yok; yukarıdaki testler orada atlanır. Sınıfın
    kendisi burada sentetik metinle tutulur, böylece kapı her ortamda çalışır.
    """

    #: Ölçülmüş kusur: PDF metin çıkarımı birleşik sözcüğün tiresinden ÖNCE
    #: boşluk bırakıyor. Küçük harfte masum, büyük harfte madde imi gibi
    #: görünüyor. Bloğun 170 karakterlik birleşik eşiğini aşması şart —
    #: bölücü yalnız o eşiğin üstünde devreye girer.
    BLOK = (
        "Murabaha akdinde alıcının, satıcının, akde konu malın mevcut ve "
        "belirli olması, faizsiz bankacılık ilke ve standartlarına ve vadeli "
        "satışa uygun olması ve tarafların irade beyanının (icap -kabul) "
        "bulunması gerekir."
    )

    def test_bosluklu_birlesik_tire_madde_imi_SAYILMAZ(self) -> None:
        normal = _kosullar(self.BLOK)
        buyuk = _kosullar(tr_upper(self.BLOK))
        self.assertEqual([tr_upper(k) for k in normal], buyuk)
        self.assertTrue(
            all("bulunması gerekir" in k for k in normal if "icap" in k)
            or any("icap -kabul) bulunması gerekir" in k for k in normal),
            f"koşul (icap -kabul) parantezinden kesilmiş: {normal}",
        )

    def test_alis_satim_gibi_ikili_bilesik_bolunmez(self) -> None:
        blok = (
            "Tarafımca iletilecek işlem talimatlarım üzerine Bankanızca, yurt "
            "içi veya yurt dışı piyasalarda bu işlemlerin gerçekleştirilebilmesi "
            "için gerekli döviz ya da kıymetli maden alım -satım işlemlerinin "
            "yapılacağı ve bu işlemler nedeniyle Bankanızın yükümlülük altına "
            "gireceği bilgimiz dâhilindedir."
        )
        self.assertEqual(
            [tr_upper(k) for k in _kosullar(blok)], _kosullar(tr_upper(blok)))

    def test_madde_imi_ISLEVI_KORUNUYOR(self) -> None:
        """Ayıracı atmak da değişmezi geçirirdi; işlev kaybı kabul edilmez."""
        metin = (
            "Kampanya müşteri bazlı olup bir müşteri kampanyadan bir defa "
            "yararlanabilir ve ilk alışveriş tutarına göre yalnız birini "
            "kazanabilir. -Bir kart ile kampanyaya katılım yapıldığında "
            "müşterinin tüm kartları kampanyaya dahil olur."
        )
        kalemler = _kosullar(metin)
        self.assertTrue(any(k.startswith("Bir kart ile") for k in kalemler),
                        f"madde imi bölünmesi kayboldu: {kalemler}")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
