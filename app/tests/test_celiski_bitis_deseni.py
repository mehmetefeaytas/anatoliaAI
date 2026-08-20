"""`_END_PATTERNS` genişlemesi — "gün-gün ortak yıl" ve "Kampanya Dönemi:" biçimleri.

İlgili: ../src/comparison/contradiction.py (`_END_PATTERNS`, `end_date_claims`,
        `_multiple_campaign_blocks`, `_rule_conflicting_end_dates`)
        docs/rapor/celiski-kod-yolu-tutarsizligi.md (ölçüm + karar gerekçesi)
        ../src/extraction/rules/extract.py (`kampanya_tarih_araligi` — genel
        alan çıkarıcı, bu dosyanın "kod yolu tutarsızlığı" kapattığı taraf)

## Bağlam

Ölçüldü (2026-08-20, iki gerçek hasat turu: c3f3b90 2026-07-30 / 849 belge →
e05bc83 2026-08-03 / 1635 belge): 40 gerçek `kampanya_suresi` değişikliği
adayından yalnız 6'sı `detect_across()`'ta ateşliyordu, çünkü `_END_PATTERNS`
korpusta EN SIK geçen "Kampanya 1 – 31 Temmuz 2026 tarihlerinde geçerlidir"
(gün-gün, ortak yıl) biçimini yakalamıyordu — genel alan çıkarıcı
`extract_kampanya_suresi` yakalıyordu. Bu dosya o genişlemenin hem POZİTİF
(doğru ateşleme) hem NEGATİF (hâlâ dar kalması GEREKEN) taraflarını sabitler.

Bu dosyanın omurgası da (ana `test_contradiction_across.py` gibi) YANLIŞ
POZİTİF testleridir: her yeni desen bir karşı-örnekle eşleşir.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.comparison.contradiction import (
    detect,
    detect_across,
    end_date_claims,
)
from src.schemas import Campaign


def _campaign(text: str, *, bank: str = "test", url: str | None = None) -> Campaign:
    return Campaign(bank_slug=bank, raw_text=text, source_url=url, fields=[])


# --------------------------------------------------------------------------- #
# 1) "Gün-gün ortak yıl" + tarihinde/tarihlerinde/arasında geçerli
# --------------------------------------------------------------------------- #

class TestGunGunOrtakYilDeseni(unittest.TestCase):
    """GERÇEK KORPUS ÖRNEĞİ (albaraka, iki hasat turu arasında değişti):
    "Kampanya Başlangıç ve Bitiş Tarihi: Kampanya 1 – 31 Temmuz 2026
    tarihlerinde geçerlidir." — yalnız GÜN solda, yıl sağdaki tam tarihle
    paylaşılıyor. Eski `_END_PATTERNS` bunu YAKALAMIYORDU (iki tam tarih ya da
    "tarihine kadar" tek tarih bekliyordu).
    """

    def test_gun_gun_tarihlerinde_gecerli_yakalanir(self):
        text = ("World Kampanyaları Kampanya Başlangıç ve Bitiş Tarihi: "
                "Kampanya 1 – 31 Temmuz 2026 tarihlerinde geçerlidir. "
                "Kampanyadan Kimler Faydalanabilir: Tüm World kart sahipleri.")
        isos = [c.iso for c in end_date_claims(text)]
        self.assertEqual(isos, ["2026-07-31"])

    def test_gun_ay_ortak_yil_tarihleri_arasinda_gecerli_yakalanir(self):
        # GERÇEK KORPUS ÖRNEĞİ (turkiye-finans): sol taraf GÜN+AY (yıl yok).
        text = ("Kampanya Hangi Tarihler Arasında Geçerlidir? Kampanya "
                "1 Temmuz - 31 Temmuz 2026 tarihleri arasında geçerlidir. "
                "4.000 TL Bonus Kazandıran Kampanyadan Kimler Yararlanabilir?")
        isos = [c.iso for c in end_date_claims(text)]
        self.assertEqual(isos, ["2026-07-31"])

    def test_caprazda_dogru_ateslenir(self):
        # GERÇEK KORPUS ÖRNEĞİ — albaraka "1000 TL'ye varan Worldpuan"
        # kampanyası, iki hasat turunda 2026-07-31 → 2026-08-31 değişti.
        # `detect_across()`'un ÜRETİM fonksiyonu tam bu biçimle çalışmalı.
        before = _campaign(
            "Kampanya Başlangıç ve Bitiş Tarihi: Kampanya 1 – 31 Temmuz 2026 "
            "tarihlerinde geçerlidir.",
            bank="albaraka",
            url="https://www.albaraka.com.tr/tr/world-dunyasi/detay/"
                "giyim-ve-kozmetik-harcamalarinizda-1000-tlye-varan-worldpuan")
        after = _campaign(
            "Kampanya Başlangıç ve Bitiş Tarihi: Kampanya 1 – 31 Ağustos 2026 "
            "tarihlerinde geçerlidir.",
            bank="albaraka",
            url="https://www.albaraka.com.tr/tr/world-dunyasi/detay/"
                "giyim-ve-kozmetik-harcamalarinizda-1000-tlye-varan-worldpuan_1")
        cons = detect_across([before, after])
        self.assertEqual([k.kind for k in cons], ["capraz_kampanya_bitisi"])
        self.assertEqual({e.value for e in cons[0].evidence},
                         {"2026-07-31", "2026-08-31"})

    # -- KARŞI-ÖRNEKLER: hâlâ dar kalması gereken durumlar ----------------- #

    def test_gecerli_sozcugu_yoksa_yakalanmaz(self):
        # GERÇEK KORPUS ÖRNEĞİ (turkiye-emlak-katilim): "geçerli" hiç geçmiyor,
        # tarih doğrudan mekanik açıklamaya bağlanıyor. Ölçülen karar: bu
        # biçim BİLEREK dar bırakıldı (bkz. rapor §"Kampanya Koşulları" —
        # başlık tek başına yeterince güvenilir çapa değil).
        text = ("Kampanya Koşulları 01-31 Temmuz 2026 tarihleri arasında "
                "ADV mağazalarında Paraf POS'undan tek seferde yapılacak "
                "10.000 TL ve üzeri ilk alışverişe 1.000 TL ParafPara "
                "verilecektir.")
        self.assertEqual(end_date_claims(text), [])

    def test_kampanya_sozcugu_uzaktaysa_yakalanmaz(self):
        # "kampanya" sözcüğü 80 karakterden uzaktaysa (başka bir konu hakkında
        # konuşuluyorsa) sıkı kalıp hâlâ konuşmamalı.
        text = ("Bu sayfa genel kullanım koşullarını açıklar. " + "x" * 60 +
                " 1 – 31 Temmuz 2026 tarihlerinde geçerlidir.")
        self.assertEqual(end_date_claims(text), [])

    def test_dort_haneli_yilin_sonu_gun_sanilmaz(self):
        # Regresyon: "...2026-31 Temmuz 2026..." gibi bitişik yazımda "26"
        # (yılın son iki hanesi) GÜN sanılıp yanlış bir sol-sınır üretmemeli.
        # `(?<!\d)` koruması olmadan `\d{1,2}` "2026"nın içinden "26"yı
        # yakalardı; koruma varken hâlâ SAĞ taraftaki tam tarih ("31 Temmuz
        # 2026") doğru çıkmalı — solun neye bağlandığı kanonik değeri
        # etkilemez ama testin amacı regex'in çökmediğini garanti etmek.
        text = "Kampanya 01 Mayıs 2026-31 Temmuz 2026 tarihleri arasında geçerlidir."
        isos = [c.iso for c in end_date_claims(text)]
        self.assertEqual(isos, ["2026-07-31"])


# --------------------------------------------------------------------------- #
# 2) "Kampanya Dönemi:" başlığı — pattern3 ("Başlangıç ve Bitiş Tarihi:") ile
#    AYNI güven seviyesinde, "geçerli" gerektirmeyen bir başlık çapası.
# --------------------------------------------------------------------------- #

class TestKampanyaDonemiBasligi(unittest.TestCase):
    """GERÇEK KORPUS ÖRNEĞİ (hayat-finans): "Kampanya Dönemi: 16 Haziran -
    31 Temmuz 2026 Kampanya Koşulları ..." — ne "tarihine kadar" ne "tarihleri
    arasında ... geçerli" var; başlığın kendisi çapa. Ölçüm: tam korpusta
    (2465 belge) bu desen 14 kez ateşledi, 14'ü de genel çıkarıcıyla tutarlıydı
    (0 tutarsız) — bkz. docs/rapor/celiski-kod-yolu-tutarsizligi.md.
    """

    def test_kampanya_donemi_basligi_gecerli_gerektirmez(self):
        text = ("Biz Kart Dijital Üyelikler Kampanyası %75 Nakit İade "
                "Fırsatı! Kampanya Dönemi: 16 Haziran - 31 Temmuz 2026 "
                "Kampanya Koşulları Kampanya Hayat Finans bireysel "
                "müşterileri için geçerlidir.")
        isos = [c.iso for c in end_date_claims(text)]
        self.assertEqual(isos, ["2026-07-31"])

    def test_caprazda_dogru_ateslenir(self):
        before = _campaign(
            "Kampanya Dönemi: 16 Haziran - 31 Temmuz 2026 Kampanya Koşulları",
            bank="hayat-finans",
            url="https://hayatfinans.com.tr/kampanyalar/"
                "biz-kart-dijital-uyelikler-kampanyasi")
        after = _campaign(
            "Kampanya Dönemi: 16 Haziran - 31 Ağustos 2026 Kampanya Koşulları",
            bank="hayat-finans",
            url="https://hayatfinans.com.tr/kampanyalar/"
                "biz-kart-dijital-uyelikler-kampanyasi_1")
        cons = detect_across([before, after])
        self.assertEqual([k.kind for k in cons], ["capraz_kampanya_bitisi"])

    # -- KARŞI-ÖRNEK --------------------------------------------------------#

    def test_baslik_yoksa_yakalanmaz(self):
        # Aynı tarih aralığı ama "Kampanya Dönemi:" başlığı YOK, "geçerli" de
        # yok, "tarihleri arasında" da yok — hiçbir desen eşleşmemeli.
        text = "16 Haziran - 31 Temmuz 2026 arasında bu ürün satışa kapalıdır."
        self.assertEqual(end_date_claims(text), [])

    def test_baska_baslikte_donemi_sozcugu_yakalanmaz(self):
        # "Kampanya" ve "Dönemi" sözcükleri metinde var ama BİRLİKTE başlık
        # OLUŞTURMUYORLAR (araya başka içerik girmiş) — pattern eşleşmemeli.
        text = ("Kampanya hakkında genel bilgi. Ödeme Dönemi: 16 Haziran - "
                "31 Temmuz 2026 arasındadır.")
        self.assertEqual(end_date_claims(text), [])


# --------------------------------------------------------------------------- #
# 3) `_multiple_campaign_blocks` — önceden var olan liste-sayfası hatasının
#    kapatılması (bkz. contradiction.py docstring'i, aynı fonksiyon).
# --------------------------------------------------------------------------- #

class TestCokluKampanyaBlogu(unittest.TestCase):
    """ÖNCEDEN VAR OLAN hata: `tests/test_contradiction_across.py`'deki
    `test_liste_sayfasi_tumu_icin_hukum_vermez` testinin SENTETİK T.O.M. Bank
    metni, bu koruma eklenmeden önceki (PATCH ÖNCESİ) kodla bile sessizce bir
    `celisen_kampanya_bitisi` HAYALETİ üretiyordu — o test yalnızca
    `suresi_dolmus_kampanya` türünü kontrol ettiği için bu görünmüyordu.
    `_END_PATTERNS`'in gün-gün genişlemesi bu senaryoyu gerçek korpusta da
    (T.O.M. Bank'ın kendi `kampanyalar.html` sayfası) tetikler hale getirdiği
    için koruma bu PR'da eklendi.
    """

    LISTE_METNI = (
        "Kampanyalar "
        "Hemen kampanyaya katıl, kazanmaya başla! "
        "Kampanya Koşulları Kampanya 6 Mart-31 Ağustos 2026 tarihleri "
        "arasında yapılacak harcamalarda geçerlidir. "
        "Hemen kampanyanı seç, tüm marketlerde sen de kazanmaya başla! "
        "Kampanya Koşulları Kampanya 19.01.2026 - 30.09.2026 tarihleri "
        "arasında yapılacak ödemelerde geçerlidir."
    )

    def test_liste_sayfasinda_belge_ici_celiski_uretilmez(self):
        # Regresyon testi: patch öncesi bu `celisen_kampanya_bitisi` üretiyordu.
        c = _campaign(self.LISTE_METNI, url="https://www.tombank.com.tr/kampanyalar.html")
        cons = [k for k in detect(c) if k.kind == "celisen_kampanya_bitisi"]
        self.assertEqual(cons, [])

    def test_tek_kampanyanin_kendi_celiskisi_hala_yakalanir(self):
        # KARŞI-ÖRNEK — koruma aşırı geniş OLMAMALI: "Kampanya Koşulları"
        # başlığı sayfada yalnız BİR kez geçiyorsa (gerçek Albaraka "Temmuz
        # Ayına Özel Fatura Kampanyası" vakasında olduğu gibi, orada "Kampanya
        # Şartları:" farklı sözcük kullanılıyor) belge-içi çelişki hâlâ
        # ateşlenmeli.
        text = ("Temmuz Ayına Özel Fatura Kampanyası "
                "Kampanya Başlangıç ve Bitiş 01.07.2026 - 31.07.2026 "
                "Kampanya Şartları: Kampanya müşteri bazındadır. "
                "Kampanya 31 Temmuz 2027 tarihine kadar geçerlidir.")
        c = _campaign(text, bank="albaraka",
                      url="https://www.albaraka.com.tr/tr/kampanyalar/detay/"
                          "temmuz-ayina-ozel-fatura-kampanyasi")
        cons = [k for k in detect(c) if k.kind == "celisen_kampanya_bitisi"]
        self.assertEqual(len(cons), 1)
        self.assertEqual({e.value for e in cons[0].evidence},
                         {"2026-07-31", "2027-07-31"})

    def test_iki_kampanyali_liste_tek_basligi_koruma_tetiklemez(self):
        # Sınır durumu: başlık yalnız 1 kez ama sayfa yine de 2 FARKLI bitiş
        # taşıyorsa (ör. eski davranış) koruma devreye GİRMEMELİ — bu hâlâ
        # `_rule_conflicting_end_dates`'in ele alması gereken vaka. Yani
        # koruma yalnız "başlık ≥2 kez" kesişimiyle sınırlı, tek başlıklı
        # sayfalarda `_looks_like_listing` gibi aşırı geniş davranmaz.
        text = ("Kampanya Koşulları Kampanya 1-31 Temmuz 2026 tarihleri "
                "arasında geçerlidir. Ayrıca sayfanın başka bir yerinde "
                "Kampanya 31 Aralık 2026 tarihine kadar geçerlidir deniyor.")
        c = _campaign(text)
        cons = [k for k in detect(c) if k.kind == "celisen_kampanya_bitisi"]
        self.assertEqual(len(cons), 1)


if __name__ == "__main__":
    unittest.main()
