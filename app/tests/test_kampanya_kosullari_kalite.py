"""`kampanya_kosullari` — koşul dili GENİŞ, koşul olmayan SÜZGEÇLİ.

İlgili: ../src/extraction/rules/extract.py (`_KOSUL_TETIK_RE`, `_kosul_degil`),
        ../src/extraction/rules/ihtar.py (K2 — genel yasal ihtar),
        ../data/gold/ANNOTATION_GUIDE.md §4 `kampanya_kosullari` (K1–K4),
        ../docs/rapor/liste-alanlari-iyilestirme.md (ölçüm defteri)

## Neden bu dosya var — kök neden ve ürün yüzeyindeki etki

Alan gold.v2'de (48 belge) kalem düzeyinde F1 **0,204** ile en zayıf alandı
(tp 27 · fp 101 · fn 110) ve manşet mikro-F1'in yaklaşık üçte birini yiyordu.
Kalem kalem sayım kökü tek bir yere indirdi: gold'un 137 koşulundan **87'si**
metnin bir cümlesinden jeton-Jaccard ≥ 0,70 ile ULAŞILABİLİRdi, ama motor
yalnız 27'sini üretiyordu. Ulaşılabilir ama üretilmeyen 60 kalemin 56'sı için
sebep aynıydı: **TETİKLEYİCİ YOK.**

Eski tetikleyici listesi koşul dilinin yalnız iki ailesini tanıyordu (kiplik
ve dışlayıcılık). Katılım bankası kampanyalarının ayırt edici koşulları ise
diğer iki ailede yazılıdır ve tamamı düşüyordu:

    "Kampanyadan bir kez faydalanılabilir"          (yararlanma hakkı)
    "Sanal kartlar kampanyaya dahildir"             (kapsam)
    "Kampanya 300 adet kod ile sınırlıdır"          (nicelik sınırı)
    "Bu kampanya … kampanyalarla birleştirilemez"   (olumsuz yeterlilik)

Ürün yüzeyindeki etki iki yönlüydü: dashboard'un koşul listesi boş ya da tek
satırlık kalıyordu (kullanıcı kampanyanın gerçek kısıtını GÖRMÜYORDU), ve o
tek satır çoğu zaman hukuki ihtar cümlesiydi — yani iki bankanın koşul listesi
birbirinin aynısı görünüyor, karşılaştırma yapay olarak yumuşuyordu.

Genişleme YALNIZ BAŞINA kesinliği düşürür (ölçüldü: fp 92 → 214). Bu yüzden
aşağıdaki iki kapı BİRLİKTE kilitlenir; biri kaldırılırsa öteki hatayı tek
başına yakalayamaz:

  KAPI 1  Dört koşul dili ailesi tetiklenir (geri çağırma).
  KAPI 2  Koşul OLMAYAN cümle sınıfları elenir ve bu süzgeçler gold.v2'nin
          137 gerçek koşulunun HİÇBİRİNE ateşlenmez (kesinlik + güvenlik).
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import (
    _kosul_degil,
    _yalnizca_tarih_gecerliligi,
    extract_kampanya_kosullari,
)
from src.extraction.rules.ihtar import ihtar_mi

KOK = Path(__file__).resolve().parents[1]
GOLD = KOK / "data" / "gold" / "gold.v2.json"


def _kosullar(metin: str) -> list[str]:
    f = extract_kampanya_kosullari(metin)
    return list(f.canonical_value) if f else []


def _gold_kosul_kalemleri() -> list[str]:
    kayitlar = json.loads(GOLD.read_text(encoding="utf-8"))
    return [c for k in kayitlar
            for c in (k["fields"].get("kampanya_kosullari") or [])]


# --------------------------------------------------------------------------- #
# KAPI 1 — koşul dilinin dört ailesi
# --------------------------------------------------------------------------- #
class TestKosulDiliDortAile(unittest.TestCase):
    """Kılavuz §4'ün "Sayılır" örneklerinin dört sözdizimsel ailesi."""

    def test_kiplik_zorunluluk(self) -> None:
        for metin in (
            "En az 3 ay maaş müşterisi olmak gerekir.",
            "Hisse senedi hesap açılışı için Uygunluk Testi yapılması zorunludur.",
            "Kampanya'dan faydalanmak için Hadi Gold üyesi olmalısın.",
        ):
            with self.subTest(metin=metin):
                self.assertTrue(_kosullar(metin), "kiplik koşulu kaçtı")

    def test_yararlanma_hakki(self) -> None:
        """ESKİ MOTORDA TAMAMEN DÜŞEN AİLE — 'faydalan…/yararlan…'."""
        for metin in (
            "Kampanyadan bir kez faydalanılabilir.",
            "Kampanyadan tüzel ve şahıs firmasına sahip eczaneler faydalanabilir.",
            "Kampanyadan Dünya Katılım Paraf kartlar faydalanabilecektir.",
        ):
            with self.subTest(metin=metin):
                self.assertTrue(_kosullar(metin), "yararlanma koşulu kaçtı")

    def test_kapsam_ve_nicelik_siniri(self) -> None:
        """ESKİ MOTORDA TAMAMEN DÜŞEN AİLE — 'dahil / kapsam dışı / en fazla'."""
        for metin in (
            "Sanal ve ek kartlar kampanyaya dahildir.",
            "Pazar yeri e-ticaret sitelerinden yapılan harcamalar "
            "kampanyaya dahil değildir.",
            "Farklı hava yolları ile ortak icra edilen uçuşlar kampanya "
            "kapsamı dışındadır.",
            "Kampanya 300 adet kod ile sınırlıdır.",
            "Kampanya kapsamında bir takvim ayında en fazla 125 TL nakit "
            "iade kazanılabilir.",
        ):
            with self.subTest(metin=metin):
                self.assertTrue(_kosullar(metin), "kapsam/sınır koşulu kaçtı")

    def test_olumsuz_yeterlilik(self) -> None:
        """Kısıtı olumsuz kuran cümle de koşuldur."""
        for metin in (
            "Bu kampanya diğer davet kodlu kampanyalarla birleştirilemez.",
            "Kampanya size özel hazırlanmıştır, devredilemez.",
            "Kampanya kapsamındaki alışverişlerin iptal/iade olması "
            "durumlarında, iade kazanılmaz.",
        ):
            with self.subTest(metin=metin):
                self.assertTrue(_kosullar(metin), "olumsuz koşul kaçtı")

    def test_cıplak_gecerli_artik_tetikler(self) -> None:
        """Eski yorum "geçerli"yi yasaklamıştı; yasak 9 gerçek koşulu yiyordu.

        Yasağın gerekçesi (tarih cümlesi) korunuyor ama artık ayrı bir
        süzgeçle (`_yalnizca_tarih_gecerliligi`) uygulanıyor.
        """
        self.assertTrue(_kosullar(
            "Taksitli ya da taksitsiz fark etmeksizin tüm işlem "
            "türlerinde geçerlidir."))
        self.assertTrue(_kosullar(
            "Çok Kazananlar Kulübü ek faydaları, yalnızca Hadi Black Kredi "
            "Kartı harcamaları için geçerlidir."))


# --------------------------------------------------------------------------- #
# KAPI 2 — koşul OLMAYAN sınıflar
# --------------------------------------------------------------------------- #
class TestKosulOlmayanElenir(unittest.TestCase):
    """Her karşı-örnek gerçek korpustan alınmış bir yanlış pozitiftir."""

    def test_genel_yasal_ihtarin_UC_CEKIMI(self) -> None:
        """K2. Dar desen bu üç çekimi görmüyordu (9 yanlış pozitif)."""
        for metin in (
            "Türkiye Emlak Katılım Bankası A.Ş. kampanyayı dilediği zaman "
            "durdurma ve/veya kampanya koşullarını değiştirme hakkına sahiptir.",
            "Hayat Finans kampanyayı dilediği zaman durdurma ve/veya kampanya "
            "koşullarını değiştirme yetkisine sahiptir.",
            "Kuveyt Türk, önceden haber vermeden kampanya koşullarında "
            "değişiklik yapabilir ya da kampanyayı sonlandırabilir.",
        ):
            with self.subTest(metin=metin):
                self.assertTrue(ihtar_mi(metin), "ihtar tanınmadı")
                self.assertEqual(_kosullar(metin), [], "ihtar koşul sayıldı")

    def test_tarih_gecerlilik_cumlesi_KOSUL_DEGIL(self) -> None:
        """K3 — bu bilgi `kampanya_suresi` alanına aittir."""
        for metin in (
            "Kampanya Koşulları Kampanya 1-31 Temmuz 2026 tarihleri "
            "arasında geçerlidir.",
            "Kampanya Şartları; Kampanya, 01.01.2026 - 29.01.2026 tarihleri "
            "arasında geçerlidir.",
            "Kampanya 01.07.2026 (saat 12.00'dan itibaren) – 31.10.2026 "
            "(saat 23.59'a kadar) tarihleri arasında geçerlidir.",
        ):
            with self.subTest(metin=metin):
                self.assertEqual(_kosullar(metin), [])

    def test_tarih_cumlesi_GERCEK_kosul_tasiyorsa_KALIR(self) -> None:
        """Süzgeç kalıp değil ÇIKARMA testi; koşul taşıyan tarih cümlesi kalır."""
        self.assertFalse(_yalnizca_tarih_gecerliligi(
            "Kampanya 1 Eylül – 30 Kasım 2025 tarihleri arasında üç (3) ay "
            "süresince sadece hafta sonları geçerlidir."))
        self.assertTrue(_kosullar(
            "Kampanya 1 Eylül – 30 Kasım 2025 tarihleri arasında üç (3) ay "
            "süresince sadece hafta sonları geçerlidir."))

    def test_soru_ve_sss_cevabi_KOSUL_DEGIL(self) -> None:
        for metin in (
            "Bu avantajlar sadece ilk başta mı geçerli?",
            "HFY fonunda minimum yatırım tutarı var mı?",
            "Hayır, avantajlar sadece ilk başta geçerli değildir.",
        ):
            with self.subTest(metin=metin):
                self.assertEqual(_kosullar(metin), [])

    def test_pazarlama_daveti_KOSUL_DEGIL(self) -> None:
        """Kılavuz §4: "Sayılmaz: … pazarlama sloganları"."""
        for metin in (
            "Birikimlerinizi yönetmek için profesyonel hizmetten "
            "yararlanabilirsiniz.",
            "Leasing başvuru sürecini hızlıca tamamlama fırsatından "
            "Kuveyt Türk farkıyla yararlanın!",
            "Mobil uygulamamızdan sözleşmelerinizi onaylayarak "
            "avantajlardan yararlanmaya başlayabilirsiniz.",
        ):
            with self.subTest(metin=metin):
                self.assertEqual(_kosullar(metin), [])

    def test_dislayici_ile_baslayan_yeterlilik_KOSULDUR(self) -> None:
        """Davet süzgecinin MUAFİYETİ — ölçümle eklendi, aksi 1 gold kalemi ölür."""
        self.assertTrue(_kosullar(
            "Sadece Türk Lirası (TL) cinsinden hesap açılışı yapabilirsiniz."))

    def test_yonlendirme_ve_sorumluluk_reddi_KOSUL_DEGIL(self) -> None:
        for metin in (
            "Kampanya koşulları hakkında detaylı bilgi için tıklayın.",
            "Ayrıntılı bilgi için kampanya şartlarına göz atabilirsiniz.",
            "Başvurunuza yönelik işlemlerin ayrı bir maliyeti gerektirmesi "
            "hâlinde, Kurul tarafından belirlenen tarifedeki ücret tarafınıza "
            "yansıtabilmektedir.",
            "Faturaların sistemde bilgilerinin hatalı olması veya kampanya "
            "kapsamı dışında kalması durumunda sorumluluk Türkiye Finans "
            "Katılım Bankası A.Ş.'ye ait değildir.",
        ):
            with self.subTest(metin=metin):
                self.assertEqual(_kosullar(metin), [])

    def test_odul_kademesi_KOSUL_DEGIL_ama_tek_tutar_KOSULDUR(self) -> None:
        """K3 — ödül tarifesi `odul_miktari`nın işi.

        Süzgeç İKİ koşulu birlikte arar (ödül fiili + en az iki tutar);
        yalnız fiile bakan sürüm gold'un üç gerçek koşulunu öldürüyordu.
        """
        self.assertEqual(_kosullar(
            "Kampanya kapsamında yurt içi giyim sektöründe tek seferde "
            "yapılacak 10.000 TL ile 24.999 TL arasındaki ilk harcamaya "
            "500 TL, 25.000 TL ve üzerindeki ilk harcamaya 1.000 TL "
            "ParafPara verilecektir."), [])
        self.assertTrue(_kosullar(
            "1000 TL ve üzeri akaryakıt harcamalarına 100 TL indirim verilir."))

    def test_fikih_ve_mevzuat_metni_KOSUL_DEGIL(self) -> None:
        """Kılavuz §4.13/1 — belgenin tek öznesi yok (zekât aracı, sukuk)."""
        for metin in (
            "Hanefi mezhebinden olanlar ziynet eşyalarını da zekat "
            "hesaplamasına dahil ederler.",
            "Kira sertifikasının vade bitimi tarihi itibarıyla satış "
            "bedelinin tamamının VKŞ tarafından tahsil edilmesi zorunludur.",
        ):
            with self.subTest(metin=metin):
                self.assertEqual(_kosullar(metin), [])


# --------------------------------------------------------------------------- #
# GÜVENLİK KAPISI — süzgeçler gold'un GERÇEK koşullarına dokunamaz
# --------------------------------------------------------------------------- #
class TestSuzgecGoldKosulunuOldurmez(unittest.TestCase):
    """Bu sınıf olmadan kesinlik süzgeci eklemek KÖR bir işlemdir.

    Her yeni `_kosul_degil` dalı buradan geçmek zorunda: gold.v2'nin 137
    gerçek koşul kaleminin hiçbiri "koşul değil" sayılamaz. Ölçüt kalem
    düzeyinde 1-1 eşleşiyor, yani süzgecin öldürdüğü her gerçek koşul
    doğrudan bir kaçırmaya dönüşür.
    """

    def test_hicbir_gold_kalemi_kosul_degil_sayilmaz(self) -> None:
        ihlal = [c for c in _gold_kosul_kalemleri() if _kosul_degil(c)]
        self.assertEqual(ihlal, [], f"süzgeç {len(ihlal)} gerçek koşulu eliyor")

    def test_hicbir_gold_kalemi_ihtar_sayilmaz(self) -> None:
        ihlal = [c for c in _gold_kosul_kalemleri() if ihtar_mi(c)]
        self.assertEqual(ihlal, [], f"ihtar deseni {len(ihlal)} koşulu eliyor")


# --------------------------------------------------------------------------- #
# BİÇİM — kalem atomik ve izlenebilir olmalı
# --------------------------------------------------------------------------- #
class TestKalemBicimi(unittest.TestCase):

    def test_blok_basligi_kaleme_yapismaz(self) -> None:
        """HTML başlığı cümlenin parçası değildir; kırpılır."""
        (kalem,) = _kosullar(
            "Kampanya Koşulları Kampanyadan bir kez faydalanılabilir.")
        self.assertEqual(kalem, "Kampanyadan bir kez faydalanılabilir.")

    def test_birlesik_blok_madde_isaretinden_bolunur(self) -> None:
        metin = ("Kampanya müşteri bazlı olup bir müşteri kampanyadan bir defa "
                 "yararlanabilir ve ilk alışveriş tutarına göre yalnız birini "
                 "kazanabilir. -Bir kart ile kampanyaya katılım yapıldığında "
                 "müşterinin tüm kartları kampanyaya dahil olur.")
        kalemler = _kosullar(metin)
        self.assertGreaterEqual(len(kalemler), 2, "birleşik blok bölünmedi")
        self.assertTrue(any(k.startswith("Bir kart ile") for k in kalemler))

    def test_ayni_kosul_iki_kez_listelenmez(self) -> None:
        """Ölçüt 1-1 eşleşiyor; yakın-tekil ikinci kalem zorunlu yanlış pozitif."""
        metin = ("Kampanyadan bir kez faydalanılabilir. "
                 "Kampanyadan bir kez faydalanılabilir.")
        self.assertEqual(len(_kosullar(metin)), 1)

    def test_kalem_metinde_BIREBIR_bulunur(self) -> None:
        """K1/izlenebilirlik: kırpma yalnız kenarlardan, span kurulabilir kalır."""
        kayitlar = json.loads(GOLD.read_text(encoding="utf-8"))
        for kayit in kayitlar:
            f = extract_kampanya_kosullari(kayit["text"])
            if f is None:
                continue
            with self.subTest(belge=kayit["id"]):
                self.assertIsNotNone(f.span_start, "span kurulamadı")
                self.assertEqual(
                    kayit["text"][f.span_start:f.span_end],
                    f.canonical_value[0],
                    "span ilk kalemi göstermiyor — kaynak vurgulama bozulur")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
