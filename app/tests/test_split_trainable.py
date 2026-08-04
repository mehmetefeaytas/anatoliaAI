"""Eğitilebilirlik ayrımı testleri.

İlgili: ../scripts/split_trainable.py · ../src/scraping/collector.py

## Neden bu testler

Bu araç, bir sınıflandırıcının GÖRECEĞİ veriyi belirliyor. İki yönde de hata
kalıcıdır ve sonradan kaynağı bulunamaz:

- **Yanlış pozitif** (geçerli belgeyi elemek): eğitim kümesi sessizce küçülür.
  Ölçülmüş en tehlikeli örnek, "Kampanya bulunamadı." cümlesini İÇEREN ama
  altında "Geçmiş Kampanyalarımız" başlığıyla GERÇEK arşiv kampanyası taşıyan
  31 İş Bankası belgesidir. Naif bir "bulunamadı" kuralı 31'ini de atardı.
- **Yanlış negatif** (çöpü içeride bırakmak): sınıflandırıcı menü metninden
  etiket öğrenir. Ölçülmüş örnek, 27 KB metinle korpusa giren "Test Figma"
  başlıklı Yapı Kredi test sayfalarıdır.

Bu yüzden her gerekçe kodunun EN AZ bir testi var ve ayrıca yanlış pozitif
tuzakları ayrı ayrı test ediliyor.

## Örnek metinlerin kaynağı

Aşağıdaki sabitler `data/raw-classic/` (ve bir tanesi `data/raw/`) altındaki
GERÇEK belgelerden BİREBİR alınmıştır; hangi dosyadan geldiği her sabitin
üstünde yazılıdır. Tek istisna `BOS_KABUK_METNI`: gerçek bir arşiv
sayfasının metninden arşiv bloğu çıkarılarak üretildi, çünkü 2026-08-04
toplama turunda İş Bankası'nın 30 boş kabuğu (202-262 karakter) tam olarak
bu biçimdeydi ama toplayıcı düzeltildikten sonra korpusta kalmadı; hangi
dosyadan türetildiği ilgili testte yazılı.

## Ölçüm notu

`split_report.md`'de raporlanan sayılar 2026-08-04 tarihli 548 belgelik
korpusa aittir: 502 kullanılabilir, 46 elenen (37 çerçeve/dizin, 5 ürün
değil, 2 blog, 2 boş kabuk). Testler bu sayılara BAĞLI DEĞİL — korpus
büyüdükçe kırılmasınlar diye davranışı sentetik kurgularla doğruluyorlar.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.split_trainable import (
    MIN_CORE_TOKENS,
    MIN_DOC_CHARS,
    R_BLOG,
    R_BOS_KABUK,
    R_CERCEVE_AGIRLIKLI,
    R_KISA,
    R_MUKERRER,
    R_URUN_DEGIL,
    R_UYGUN,
    Doc,
    boilerplate_shingles,
    build_report,
    classify,
    core_text,
    is_listing_url,
    iter_docs,
    main,
    split_corpus,
    text_key,
)

# --------------------------------------------------------------------------
# GERÇEK KORPUS METİNLERİ (birebir kopya)
# --------------------------------------------------------------------------

# data/raw-classic/vakifbank/live/krediler-proje-ve-yatirim-kredileri.txt
# TAM metin, 294 karakter. Korpustaki en kısa GEÇERLİ ürün listelerinden biri;
# `collector.py` de bu belgeyi uzunluk eşiği tartışmasında referans alıyor.
VAKIFBANK_294 = (
    "Proje ve Yatırım Kredileri Proje Finansmanı Kredileri Proje ve "
    "yatırımların finansmanına yönelik olarak uygun alternatifler "
    "VakıfBank'ta. Detaylı Bilgi IPARD Hibe Destekli Yatırım Kredisi IPARD "
    "kapsamındaki yatırımlarınıza ilişkin IPARD Hibe Destekli Yatırım "
    "Kredisi VakıfBank'ta. Detaylı Bilgi"
)

# data/raw-classic/is-bankasi/live/kampanyalar-akzonobel-ilave-taksit-kampanyasi.txt
# TAM metin, 743 karakter. KRİTİK ÖRNEK: "Kampanya bulunamadı." diyor AMA
# altında "Geçmiş Kampanyalarımız" başlığıyla gerçek kampanya koşulları var.
ISBANK_ARSIV_743 = (
    "Ana Sayfa > Kampanyalar > Ticari Kredi Kartı Kampanyaları > Akzonobel "
    "İlave Taksit Kampanyası Akzonobel İlave Taksit Kampanyası Kampanya "
    "bulunamadı. Güncel kampanyalara buradan ulaşabilirsiniz. Geçmiş "
    "Kampanyalarımız 01 Mart 2021 Akzonobel İlave Taksit Kampanyası Kampanya "
    "Geçerlilik Tarihi 01.03.2021 - 31.05.2021 Kampanyaya Dahil Olan Kartlar "
    "Maximum özellikli Bankamız Ticari Kredi Kartları, Maximum özellikli "
    "Bankamız Bireysel Kredi Kartları Kampanyaya dâhil olmayan kartlar ve "
    "işlemler Aidatsız Kartlar, Bankamatik Kart, İş Bankası Vergi Kart ve "
    "Maximum Business Aidatsız Kart ile yapılan işlemler, Maximum Fırsat ve "
    "MaxiPuan kullanılarak yapılan alışverişler, Maximum POS cihazından "
    "yapılmayan işlemler kampanyaya dâhil değildir. X Kapat"
)

# ISBANK_ARSIV_743'ten arşiv bloğu çıkarılmış hâli (bkz. modül açıklaması).
# 2026-08-04 turunda İş Bankası'nın boş kabukları tam bu biçimdeydi.
BOS_KABUK_METNI = (
    "Ana Sayfa > Kampanyalar > Ticari Kredi Kartı Kampanyaları > Akzonobel "
    "İlave Taksit Kampanyası Akzonobel İlave Taksit Kampanyası Kampanya "
    "bulunamadı. Güncel kampanyalara buradan ulaşabilirsiniz. X Kapat"
)

# data/raw-classic/teb/live/filenotfound.txt — 404 cümlesinin çevresinden 800
# karakterlik birebir kesit. Tam belge 3628 karakter (kısalık kuralının 6
# katı) ve tamamı gezinme menüsü artı buradaki "bulunamadı" cümlesi. Kesit
# kasten 600 karakterin ÜSTÜNDE tutuldu; kısalık kuralının bu sayfayı
# göremediğini, ayrı 404 kuralının gördüğünü kanıtlamak için.
TEB_404 = (
    "ş Dünyası Emekli Bankacılığı ÜniversiTEB Ayrıcalıklı Bankacılık Size "
    "özel çözümler için sizi tanıyan bankacılık. Kampanyalar CEPTETEB "
    "CEPTETEB'de Merak Ettikleriniz CEPTETEB'lilere Özel Avantajlar Nasıl "
    "CEPTETEB'li Olurum? CEPTETEB Mobil Uygulaması İnternet Şubesi TELEPATİ "
    "Kişisel Bankacılık Asistanı ATM'ler Hemen Yükle Güvenlik CEPTETEB "
    "CEPTETEB tüm bankacılık işlemlerini, istediğin zaman, istediğin yerden, "
    "şubeye gitmeden kolayca yapmanı sağlar. Firmanız İçin Uygun Olanı Seçin "
    "Esnafım Çiftçiyim Girişimciyim Kadın Patronum KOBİ'yim Kurumsal "
    "Çalışıyorum Görüntülemek istediğiniz sayfa bulunamadı. Lütfen adresi "
    "kontrol ederek tekrar deneyin veya seçeneklerden birini kullanin. Ana "
    "Sayfa Site Haritası Avrupa ve Türkiye'nin en iyi işverenlerinden "
    "biriyiz. TEB Kariyer TEB Önce Müşteri Memnuniyet"
)

# data/raw-classic/qnb/live/kart-sozlugu.txt — ilk 700 karakter.
QNB_SOZLUK = (
    "Hemen Başvur QNB Mobil EN Ara Kartlar QNB Kredi Kartı QNB Xtra QNB "
    "Nakit Banka Kartı QNB Kredi Kartı Sanal Kart QNB Kredi Kartı 25.000 "
    "TL'ye varan Faizsiz Taksitli Nakit Avans! Diğer Kartlar QNB Emekli QNB "
    "Hemşire QNB Fix Kampanyalar Özellikler Kolay Ödeme Rehberi TaksitKolay "
    "Ekstre Taksit Nakit İhtiyaçlarınız İçin Nakit Avans Taksitli Nakit "
    "Avans Ekstra Özellikler Sigorta Ürünleri ve Ödeme Güvencesi Asistans "
    "Hizmetleri Ödemeler Otomatik Fatura Ödeme SGK & Vergi Ödemeleri Nasıl "
    "Başvurabilirsiniz? Kart Sözlüğü Ana Sayfa Kart Sözlüğü Temassız Kredi "
    "Kartı Limiti Faiz Oranları ve Kart Ücretleri Güvenlik Ek Kart Ekstre "
    "Para Transferi Hızlı Kart Başvurusu"
)

# data/raw-classic/qnb/live/akademi-yemek-kartlarinda-qr-kod-kullanmanin-avantajlari-10587.txt
QNB_AKADEMI = (
    "Ana Sayfa Akademi Yemek Kartlarında QR Kod Kullanmanın Avantajları "
    "Yemek Kartlarında QR Kod Kullanmanın Avantajları Okuma Süresi 3 dk "
    "16.02.2024 Akademi Blog Yemek Kartlarında QR Kod Kullanmanın "
    "Avantajları İşletmelerin personeller için sunmuş olduğu yemek kartı "
    "opsiyonu, hem işveren hem de çalışan açısından çeşitli avantajlar taşır."
)

# data/raw-classic/halkbank/live/bagislar-yardim-kampanyalari-bagis-ve-kurban-tahsilatlari.txt
HALKBANK_BAGIS = (
    "Yardım Kampanyaları, Bağış ve Kurban Tahsilatları Bağış ve Kurban "
    "Tahsilatları AFAD Yardım Kampanyaları Desteklediğiniz kurum ve sivil "
    "toplum kuruluşları için bağış ödemelerinizi Halkbank Şubelerimizden, "
    "İnternet Şubesi, Halkbank Mobil veya Halkbank Dialog ve "
    "ATM'lerimizden kolayca yapabilirsiniz Bağış Yapabileceğiniz Kurumlar"
)

# data/raw-classic/halkbank/live/eylul-halkbanktan-sahan-gokbakarli-yeni-reklam-kampanyasi.txt
HALKBANK_REKLAM = (
    "Halkbank'tan Şahan Gökbakar'lı yeni reklam kampanyası 30.09.2016 "
    "Halkbank'tan Şahan Gökbakar'lı yeni reklam kampanyası Halkbank yeni "
    "dönemini \"Halk ister Halkbank Yapar\" sloganıyla karşılıyor Halkbank, "
    "oyuncu Şahan Gökbakar'ın rol aldığı, \"Halk ister Halkbank yapar\" "
    "sloganlı reklam kampanyasıyla yeni döneme iddialı bir giriş yapıyor."
)

# data/raw-classic/qnb/live/*.txt — QNB'nin her sayfasında AYNEN tekrar eden
# gezinme menüsü. 80 QNB belgesinin hepsinde bu blok var.
QNB_MENU = (
    "Hemen Başvur QNB Mobil EN Ara Kartlar QNB Kredi Kartı QNB Xtra QNB "
    "Nakit Banka Kartı QNB Kredi Kartı Sanal Kart QNB Kredi Kartı 25.000 "
    "TL'ye varan Faizsiz Taksitli Nakit Avans! Diğer Kartlar QNB Emekli QNB "
    "Hemşire QNB Fix Kampanyalar Özellikler Kolay Ödeme Rehberi TaksitKolay "
    "Ekstre Taksit Nakit İhtiyaçlarınız İçin Nakit Avans Taksitli Nakit "
    "Avans Ekstra Özellikler Sigorta Ürünleri ve Ödeme Güvencesi Asistans "
    "Hizmetleri Ödemeler Otomatik Fatura Ödeme SGK & Vergi Ödemeleri Nasıl "
    "Başvurabilirsiniz?"
)

# data/raw-classic/denizbank/live/kampanya-kart-kampanyalari.txt — altbilgi.
# 9 DenizBank listeleme sayfasının VE 26 gerçek kampanya sayfasının hepsinde
# bulunuyor; bu yüzden "KVKK/çerez geçiyorsa ürün değildir" kuralı tam
# metinde çalıştırılamaz.
DENIZBANK_KVKK_ALTBILGI = (
    "Yukarı Çık Kapat Kapat 1 Kapat 2 Kapat Kapat Kapat Kapat 1. Amaç ve "
    "Kapsam Bu Kişisel Verilerinizin İşlenmesi Hakkında Aydınlatma Metni "
    "(\"Aydınlatma Metni\") 6698 sayılı Kişisel Verilerin Korunması Kanunu "
    "(KVKK) kapsamında DenizBank A.Ş. tarafından işlenen kişisel verileriniz"
)

# data/raw-classic/denizbank/live/ciftcilerimize-ozel-kampanyalar-*yem*.txt
# ÜÇ GERÇEK kampanya metni (birebir). Aralarında kalıp cümleler AYNEN tekrar
# ediyor ("Kampanyadan yalnızca Üretici Kart sahibi müşterilerimiz
# yararlanabilir.") — çerçeve tespiti bunları ayıklayacak, ama marka adı,
# vade ve POS koşulu gibi AYIRT EDİCİ bilgi çekirdekte kalmalı.
DENIZBANK_KAMPANYALARI: tuple[str, ...] = (
    "Menüye Git İçeriğe Git Balyem Yem Alımlarında 3 Ay Vade Üretici Kart "
    "ile Balyem Yem bayilerinden yapacağınız alışverişlerde 3 ay vade "
    "avantajı sizi bekliyor. Kampanya Geçerlilik Tarihi 01.04.2026 - "
    "31.08.2026 Kampanyaya Nereden Katılırım? Paylaş Kampanya Detayları "
    "Kampanya 01.04.2026 – 31.08.2026 tarihleri arasında geçerlidir. "
    "Kampanya Balyem Yem bayilerindeki sanal POS işlemlerinde geçerlidir. "
    "Kampanyadan yalnızca Üretici Kart sahibi müşterilerimiz yararlanabilir.",
    "Menüye Git İçeriğe Git Emek Yem Alımlarında 6 Aya Varan Vade Üretici "
    "Kart ile Emek Yem bayilerinde yapacağınız yem alımlarında 6 aya varan "
    "vade avantajından yararlanabilirsiniz. Kampanya Geçerlilik Tarihi "
    "01.04.2026 - 31.08.2026 Kampanyaya Nereden Katılırım? Paylaş Kampanya "
    "Detayları Kampanya 01.04.2026 – 31.08.2026 tarihleri arasında "
    "geçerlidir. Kampanya Emek Yem bayilerinde bulunan sanal POS "
    "cihazlarında geçerlidir. Kampanyadan yalnızca Üretici Kart sahibi "
    "müşterilerimiz yararlanabilir.",
    "Menüye Git İçeriğe Git Abalıoğlu Yem Alımlarında 4 Aya Varan Vade "
    "Üretici Kart sahibi müşterilerimize özel, Abalıoğlu Yem bayilerinde 4 "
    "aya varan vade fırsatı. Kampanya Geçerlilik Tarihi 01.04.2026 - "
    "31.08.2026 Kampanyaya Nereden Katılırım? Paylaş Kampanya Detayları "
    "Kampanya 01.04.2026 – 31.08.2026 tarihleri arasında geçerlidir. "
    "Kampanya Abalıoğlu Yem bayilerinde bulunan sanal POS cihazlarında "
    "geçerlidir. Kampanyadan yalnızca Üretici Kart sahibi müşterilerimiz "
    "yararlanabilir.",
)

# data/raw/dunya-katilim/live/finansmanlar-ihtiyac-finansmani.txt (SSS bölümü)
# GERÇEK bir ürün sayfasının içinde "nelere dikkat" ifadesi geçiyor; blog
# kuralı gövdede arasa bu ürün sayfası elenirdi.
DUNYA_KATILIM_SSS = (
    "Tüketici finansmanı kullanmadan önce nelere dikkat etmeliyim? Tüketici "
    "finansmanı kullanmadan önce, başvurduğunuz kanala göre (şube, internet "
    "şubesi veya mobil uygulama) gerekli belgeleri hazırlamanız gerekir."
)


def _doc(text: str, *, doc_id: str = "banka--belge", bank: str = "banka",
         title: str | None = None, url: str | None = None) -> Doc:
    """Tek belgeli hızlı kurgu — `split_corpus` yerine `classify` testleri için.

    Tek belge olduğu için çerçeve tespiti devre dışı kalır (`core == text`);
    çerçeveden bağımsız kuralları izole eder.
    """
    doc = Doc(doc_id=doc_id, bank=bank, rel_path=f"{bank}/live/x.txt",
              text=text, title=title, source_url=url)
    # Sözcük sayımı araçla AYNI tokenleştiriciden geçmeli; `str.split()`
    # noktalamayı sözcüğe yapıştırır ve sayı kayar.
    doc.core_text = core_text(text, set())
    doc.total_tokens = len(doc.core_text.split())
    doc.core_tokens = doc.total_tokens
    return doc


class TestUygun(unittest.TestCase):
    """R_UYGUN — geçerli belge elenmemeli."""

    def test_294_karakterlik_urun_listesi_elenmez(self) -> None:
        """294 karakterlik VakıfBank ürün listesi KULLANILABİLİR olmalı.

        Bu, uzunluk eşiğini tek başına kullanmanın neden yasak olduğunun
        kanıtı: aynı toplama turunda 202-262 karakterlik boş kabuklar vardı,
        yani eşiği 300'e çekmek bu geçerli belgeyi de atardı.
        """
        doc = _doc(VAKIFBANK_294,
                   url="https://www.vakifbank.com.tr/tr/bireysel/krediler/"
                       "proje-ve-yatirim-kredileri",
                   title="Proje ve Yatırım Kredileri | VakıfBank")
        self.assertEqual(len(VAKIFBANK_294), 294)
        self.assertEqual(classify(doc)[0], R_UYGUN)

    def test_arsiv_icerigi_tasiyan_bulunamadi_sayfasi_kullanilabilir(self) -> None:
        """"Kampanya bulunamadı" + GERÇEK arşiv içeriği => KULLANILABİLİR.

        Korpusta 31 belge bu biçimde (İş Bankası). Hepsinde kampanya tarihi,
        dahil kartlar ve koşullar var. Elenirlerse gümüş kümenin en zengin
        arşiv kaynağı yok olur.
        """
        doc = _doc(ISBANK_ARSIV_743,
                   bank="is-bankasi",
                   url="https://www.isbank.com.tr/kampanyalar/"
                       "akzonobel-ilave-taksit-kampanyasi",
                   title="Akzonobel İlave Taksit Kampanyası | Türkiye İş Bankası")
        self.assertIn("bulunamadı", ISBANK_ARSIV_743)
        self.assertGreater(len(ISBANK_ARSIV_743), 600)
        self.assertEqual(classify(doc)[0], R_UYGUN)


class TestBosKabuk(unittest.TestCase):
    """R_BOS_KABUK — "içerik yok" diyen sayfalar."""

    def test_kisa_bulunamadi_kabugu_elenir(self) -> None:
        """İşaretçi + kısalık BİRLİKTE: 201 karakterlik kabuk elenir.

        201 karakter, 2026-08-04 ölçümündeki 202-262 karakterlik İş Bankası
        kabuklarının tam bandında.
        """
        self.assertLess(len(BOS_KABUK_METNI), 600)
        doc = _doc(BOS_KABUK_METNI, bank="is-bankasi")
        code, detail = classify(doc)
        self.assertEqual(code, R_BOS_KABUK)
        self.assertIn("bulunamadi", detail)

    def test_404_sayfasi_uzun_olsa_da_elenir(self) -> None:
        """TEB 404 sayfası 3628 karakter — kısalık kuralı görmez, 404 kuralı görür."""
        doc = _doc(TEB_404, bank="teb",
                   url="https://www.teb.com.tr/FileNotFound.aspx",
                   title="Türk Ekonomi Bankasi")
        code, detail = classify(doc)
        self.assertEqual(code, R_BOS_KABUK)
        self.assertIn("404", detail)

    def test_uzun_sayfada_gecen_bulunamadi_belgeyi_dusurmez(self) -> None:
        """600 karakteri aşan belgede tek başına "bulunamadı" eleme sebebi değil."""
        doc = _doc(ISBANK_ARSIV_743, bank="is-bankasi")
        self.assertNotEqual(classify(doc)[0], R_BOS_KABUK)


class TestKisa(unittest.TestCase):
    """R_KISA — belgenin kendisi çok kısa.

    Bu kural bugün korpusta ATEŞLENMİYOR: `collector.MIN_DOC_CHARS` aynı
    eşiği uyguladığı için toplanan en kısa belge 214 karakter. Kural,
    toplayıcıdan hiç geçmeyen `manual/` belgeleri (şartname §5.1 elle
    toplamaya izin veriyor) için savunma katmanı olarak duruyor — elle
    kaydedilen bir sayfa yarım kaydedilebilir.
    """

    def test_esik_altindaki_belge_elenir(self) -> None:
        kisa = VAKIFBANK_294[:150]
        self.assertLess(len(kisa), MIN_DOC_CHARS)
        code, detail = classify(_doc(kisa))
        self.assertEqual(code, R_KISA)
        self.assertIn("150", detail)

    def test_esik_ustundeki_belge_elenmez(self) -> None:
        self.assertGreaterEqual(len(VAKIFBANK_294), MIN_DOC_CHARS)
        self.assertNotEqual(classify(_doc(VAKIFBANK_294))[0], R_KISA)


class TestBlog(unittest.TestCase):
    """R_BLOG — blog / sözlük / rehber."""

    def test_kart_sozlugu_elenir(self) -> None:
        """QNB "Kart Sözlüğü": terim başlıkları listesi, ürün bilgisi yok."""
        doc = _doc(QNB_SOZLUK, bank="qnb",
                   url="https://www.qnbcard.com.tr/kart-sozlugu",
                   title="Kartlar Hakkında Bilgiler | QNB Kredi Kartı")
        code, detail = classify(doc)
        self.assertEqual(code, R_BLOG)
        self.assertIn("sozlugu", detail)

    def test_akademi_blog_yazisi_elenir(self) -> None:
        """QNB Akademi yazısı: "Okuma Süresi 3 dk" + "Akademi Blog" rozetleri."""
        doc = _doc(QNB_AKADEMI, bank="qnb",
                   url="https://www.qnb.com.tr/dijitalkopru/akademi/"
                       "yemek-kartlarinda-qr-kod-kullanmanin-avantajlari-10587",
                   title="Yemek Kartlarında QR Kod Kullanımı | QNB Dijital Köprü")
        self.assertEqual(classify(doc)[0], R_BLOG)

    def test_urun_sayfasinin_sss_bolumu_blog_sayilmaz(self) -> None:
        """GÖVDEDE geçen "nelere dikkat" ürün sayfasını blog yapmaz.

        Ölçüm: `data/raw/` altında 3 gerçek ürün sayfasının SSS bölümünde bu
        ifade geçiyor. İşaretçiler bu yüzden yalnız BAŞLIK BÖLGESİNDE aranır.
        """
        text = VAKIFBANK_294 + " " + DUNYA_KATILIM_SSS
        doc = _doc(text, url="https://www.dunyakatilim.com.tr/finansmanlar/"
                             "ihtiyac-finansmani",
                   title="İhtiyaç Finansmanı")
        self.assertIn("nelere dikkat", text)
        self.assertNotEqual(classify(doc)[0], R_BLOG)


class TestUrunDegil(unittest.TestCase):
    """R_URUN_DEGIL — bağış, haber, KVKK, iletişim, yatırımcı ilişkileri."""

    def test_bagis_ve_kurban_tahsilati_elenir(self) -> None:
        doc = _doc(HALKBANK_BAGIS, bank="halkbank",
                   url="https://www.halkbank.com.tr/tr/bireysel/odemeler/"
                       "bagislar/yardim-kampanyalari-bagis-ve-kurban-tahsilatlari",
                   title="Yardım Kampanyaları, Bağış ve Kurban Tahsilatları")
        self.assertEqual(classify(doc)[0], R_URUN_DEGIL)

    def test_reklam_haberi_elenir(self) -> None:
        """2016 tarihli reklam filmi haberi — bankacılık kampanyası değil."""
        doc = _doc(HALKBANK_REKLAM, bank="halkbank",
                   url="https://www.halkbank.com.tr/tr/bankamiz/bizi-taniyin/"
                       "haberler-ve-duyurular/haberler/2016/eylul/"
                       "halkbanktan-sahan-gokbakarli-yeni-reklam-kampanyasi",
                   title="Halkbank'tan Şahan Gökbakar'lı yeni reklam kampanyası")
        self.assertEqual(classify(doc)[0], R_URUN_DEGIL)

    def test_url_parcasi_tam_parca_olarak_eslesir(self) -> None:
        """"kariyer" YOL PARÇASI olmalı; slug içinde geçmesi eleme sebebi değil.

        Ölçülmüş yanlış pozitif: Yapı Kredi Play'in
        `.../play-karta-ozel-200-tl-ve-uzeri-egitim-ve-kariyer-platformlarinda-...`
        kampanyası alt dize eşleşmesiyle "kariyer sayfası" sanılıyordu.
        """
        doc = _doc(VAKIFBANK_294, bank="yapi-kredi",
                   url="https://www.yapikrediplay.com.tr/kampanyalar/"
                       "play-karta-ozel-200-tl-ve-uzeri-egitim-ve-kariyer-"
                       "platformlarinda-odeme",
                   title="Play karta özel eğitim ve kariyer platformları")
        self.assertNotEqual(classify(doc)[0], R_URUN_DEGIL)

    def test_altbilgideki_kvkk_metni_belgeyi_dusurmez(self) -> None:
        """KVKK/çerez altbilgisi gerçek kampanya sayfalarında da var.

        Ölçüm (2026-08-04): "Kişisel Verilerin Korunması" ifadesi 9 DenizBank
        listeleme sayfasında VE 26 gerçek DenizBank kampanya sayfasında
        geçiyor. Kural tam metinde çalışsa 26 gerçek kampanya elenirdi.
        Burada çerçeve, ÜÇ belgede tekrar ettiği için ayıklanıyor ve
        başlık bölgesine hiç girmiyor.
        """
        docs = [
            _row(f"denizbank--k{i}", f"{text} {DENIZBANK_KVKK_ALTBILGI}",
                 f"https://www.denizbank.com/kampanya/ciftci/k{i}")
            for i, text in enumerate(DENIZBANK_KAMPANYALARI)
        ]
        for doc in docs:
            self.assertIn("Kişisel Verilerin Korunması", doc.text)
        split_corpus(docs)
        for doc in docs:
            self.assertEqual(doc.decision, R_UYGUN, doc.detail)
            self.assertNotIn("Kişisel", doc.core_text)
        # Marka adı ve vade çekirdekte KALMALI — yoksa çerçeve ayıklaması
        # gerçek içeriği yiyor demektir.
        self.assertIn("Balyem", docs[0].core_text)
        self.assertIn("Emek", docs[1].core_text)
        self.assertIn("Abalıoğlu", docs[2].core_text)


class TestCerceveAgirlikli(unittest.TestCase):
    """R_CERCEVE_AGIRLIKLI — metni neredeyse tamamen çerçeve / dizin."""

    def test_menu_agirlikli_sayfa_elenir(self) -> None:
        """Aynı menüyü paylaşan 3 belgeden içeriği olmayan eleniyor.

        Kurgu gerçek QNB menüsünü kullanıyor: üç belgede aynen tekrar
        ettiği için çerçeve sayılıyor. Üçüncü belgenin menüden başka hiçbir
        şeyi yok — korpusta `qnb--kartlar` (1390 karakter, çekirdek 3
        sözcük) ve `ziraat-bankasi--kartlar-yurt-ici-banka-karti-atm-paylasimi`
        (1503 karakter, çekirdek 2 sözcük) tam olarak böyle.
        """
        gercek_1 = ("ZARA'da Peşin Fiyatına 6 Taksit! QNB Kredi Kartı'nızla "
                    "Zara mağazalarından 31 Ocak 2027'ye kadar yapacağınız "
                    "alışverişlerinizde peşin fiyatına 6 taksit fırsatı!")
        gercek_2 = ("Koton'da Peşin Fiyatına 6 Taksit! QNB Kredi Kartı'nızla "
                    "Koton mağazalarından 31 Aralık 2026'ya kadar yapacağınız "
                    "alışverişlerinizde peşin fiyatına 6 taksit fırsatı!")
        docs = [
            _row("qnb--zara", f"{QNB_MENU} {gercek_1}",
                 "https://www.qnbcard.com.tr/kampanyalar/zarada-6-taksit"),
            _row("qnb--koton", f"{QNB_MENU} {gercek_2}",
                 "https://www.qnbcard.com.tr/kampanyalar/kotonda-6-taksit"),
            _row("qnb--kartlar", f"{QNB_MENU} Kartlar",
                 "https://www.qnbcard.com.tr/kartlar-listesi"),
        ]
        split_corpus(docs)
        kararlar = {d.doc_id: d.decision for d in docs}
        self.assertEqual(kararlar["qnb--zara"], R_UYGUN)
        self.assertEqual(kararlar["qnb--koton"], R_UYGUN)
        self.assertEqual(kararlar["qnb--kartlar"], R_CERCEVE_AGIRLIKLI)

    def test_iki_belgeden_cerceve_cikarilmaz(self) -> None:
        """`BOILERPLATE_MIN_DOCS` altındaki bankada çerçeve tespiti kapalı.

        İki belgenin ortak metni çerçeve OLMAYABİLİR (aynı kampanyanın
        bireysel/KOBİ görünümü). İki belgeden çerçeve çıkarmak gerçek içeriği
        siler; o yüzden küme boş dönmeli.
        """
        self.assertEqual(boilerplate_shingles([QNB_MENU, QNB_MENU]), set())

    def test_kampanya_dizini_url_ile_elenir(self) -> None:
        """`/kampanyalar` ile biten URL kampanya DETAYI değil, dizindir.

        Ölçüm: bu kural 548 belgelik korpusta 19 belge eledi ve 19'unun 19'u
        elle okunup dizin olduğu doğrulandı (Akbank, Axess, Garanti, Bonus,
        Halkbank, Paraf, ING, İş Bankası, Maximiles, TEB, QNB, Yapı Kredi'nin
        4 kart alt sitesi, Bankkart ana sayfası, DenizBank).
        """
        uzun_dizin = " ".join(["Tüm Kampanyalar Bireysel Kurumsal Kredi Kartı "
                               "Sigorta Kredi Emeklilik Mevduat"] * 20)
        doc = _doc(uzun_dizin, bank="akbank",
                   url="https://www.akbank.com/kampanyalar",
                   title="Tüm Kampanyalar | Akbank")
        code, detail = classify(doc)
        self.assertEqual(code, R_CERCEVE_AGIRLIKLI)
        self.assertIn("listeleme", detail)

    def test_kategori_yolu_elenir(self) -> None:
        doc = _doc(VAKIFBANK_294 * 3, bank="yapi-kredi",
                   url="https://www.yapikredi.com.tr/kampanyalar/kategori/kobi/")
        self.assertEqual(classify(doc)[0], R_CERCEVE_AGIRLIKLI)

    def test_arsiv_dizini_elenir_arsiv_detayi_kalir(self) -> None:
        """Arşiv DİZİNİ elenir, arşiv KAMPANYA DETAYI elenmez.

        Eşleşme yol parçasının TAMAMIYLA yapılır. QNB'nin
        `/kampanyalar/arsivdeki-kampanyalar` dizini eleniyor; DenizBank'ın
        `/kampanya/arsivdeki-kampanyalar/<slug>-18027` detay sayfası kalıyor.
        """
        self.assertIsNotNone(is_listing_url(
            "https://www.qnb.com.tr/kampanyalar/arsivdeki-kampanyalar"))
        self.assertIsNone(is_listing_url(
            "https://www.denizbank.com/kampanya/arsivdeki-kampanyalar/"
            "emekliler-denizde-mutlu-112769"))

    def test_url_yoksa_listeleme_kurali_ateslenmez(self) -> None:
        """`source_url` eksikse kural sessiz kalmalı.

        Aksi hâlde "yol boş" koşulu meta'sı olmayan HER belge için doğru
        görünür ve kural tüm korpusu elerdi.
        """
        self.assertIsNone(is_listing_url(None))
        self.assertIsNone(is_listing_url(""))
        self.assertIsNone(is_listing_url("   "))
        self.assertIsNotNone(is_listing_url("https://www.bankkart.com.tr/"))

    def test_esik_gercek_kampanyalari_korur(self) -> None:
        """`MIN_CORE_TOKENS` GERÇEK kısa kampanyaların altında kalmalı.

        Ölçüm (548 belge): QNB'nin marka ailesi kampanyaları (Zara, Bershka,
        Oysho, Stradivarius "peşin fiyatına 6 taksit") çekirdekte tam 12
        sözcükte kalıyor, çünkü aralarındaki tek fark marka adı. Eşik 13
        olsaydı 4 gerçek kampanya elenirdi.
        """
        self.assertLessEqual(MIN_CORE_TOKENS, 12)


class TestMukerrer(unittest.TestCase):
    """R_MUKERRER — aynı metin farklı dosya adıyla."""

    def test_beyaz_bosluk_farki_mukerrer_sayilir(self) -> None:
        """Tekilleştirme anahtarı beyaz boşluğa duyarsız (`collector` ile aynı)."""
        a = ISBANK_ARSIV_743
        b = "  " + ISBANK_ARSIV_743.replace(" ", "\n  ") + "\n"
        self.assertEqual(text_key(a), text_key(b))

    def test_ilk_goren_kazanir_ikincisi_elenir(self) -> None:
        docs = [
            _row("is-bankasi--a", ISBANK_ARSIV_743,
                 "https://www.isbank.com.tr/kampanyalar/a"),
            _row("is-bankasi--b", ISBANK_ARSIV_743.replace(" ", "  "),
                 "https://www.isbank.com.tr/kampanyalar/b"),
        ]
        split_corpus(docs)
        self.assertEqual(docs[0].decision, R_UYGUN)
        self.assertEqual(docs[1].decision, R_MUKERRER)
        self.assertIn("is-bankasi--a", docs[1].detail)

    def test_mukerrer_karari_diger_kurallardan_once_gelir(self) -> None:
        """Mükerrer belge, başka bir gerekçeye de uysa MUKERRER raporlanır."""
        docs = [
            _row("halkbank--a", HALKBANK_BAGIS,
                 "https://www.halkbank.com.tr/tr/bireysel/odemeler/bagislar/x"),
            _row("halkbank--b", HALKBANK_BAGIS,
                 "https://www.halkbank.com.tr/tr/bireysel/odemeler/bagislar/y"),
        ]
        split_corpus(docs)
        self.assertEqual(docs[0].decision, R_URUN_DEGIL)
        self.assertEqual(docs[1].decision, R_MUKERRER)


class TestCekirdekAyiklama(unittest.TestCase):
    """`core_text` mekaniği."""

    def test_cercevesiz_belge_sozcuklerini_korur(self) -> None:
        """Çerçeve kümesi boşken tüm sözcükler çekirdekte kalır.

        `core_text` sözcük düzeyinde çalışır ve noktalama/kesme işaretlerini
        ayırır (`VakıfBank'ta` -> `VakıfBank ta`), bu yüzden karşılaştırma
        sözcük dizisi üzerinden yapılıyor.
        """
        core = core_text(VAKIFBANK_294, set())
        self.assertIn("IPARD Hibe Destekli Yatırım Kredisi", core)
        self.assertIn("Proje ve Yatırım Kredileri", core)
        self.assertEqual(len(core.split()), 37)

    def test_cerceve_ngrami_tum_pencereyi_siler(self) -> None:
        """Kapsama: n-gramın ilk sözcüğü değil, tüm pencere atılır."""
        docs = [_row(f"b--{i}", f"{QNB_MENU} ozgun{i} icerik{i} burada{i}",
                     f"https://x.example/kampanyalar/{i}") for i in range(3)]
        split_corpus(docs)
        for i, doc in enumerate(docs):
            self.assertIn(f"ozgun{i}", doc.core_text)
            self.assertNotIn("Hemen Başvur QNB Mobil", doc.core_text)

    def test_kisa_belgede_cerceve_ayiklanmaz(self) -> None:
        """Sözcük sayısı n-gram boyundan azsa hiçbir şey atılmaz."""
        self.assertEqual(core_text("bir iki üç", {"bir iki üç"}), "bir iki üç")


class TestSessizKayipYok(unittest.TestCase):
    """Toplam korunmalı: trainable + excluded == toplam."""

    def _korpus(self, kok: str) -> None:
        ornekler = {
            "qnb": [("kart-sozlugu", QNB_SOZLUK,
                     "https://www.qnbcard.com.tr/kart-sozlugu"),
                    ("zara", f"{QNB_MENU} ZARA'da Peşin Fiyatına 6 Taksit! "
                             f"QNB Kredi Kartı'nızla Zara mağazalarından "
                             f"31 Ocak 2027'ye kadar 6 taksit fırsatı!",
                     "https://www.qnbcard.com.tr/kampanyalar/zara"),
                    ("koton", f"{QNB_MENU} Koton'da Peşin Fiyatına 6 Taksit! "
                              f"QNB Kredi Kartı'nızla Koton mağazalarından "
                              f"31 Aralık 2026'ya kadar 6 taksit fırsatı!",
                     "https://www.qnbcard.com.tr/kampanyalar/koton"),
                    ("kartlar", f"{QNB_MENU} Kartlar",
                     "https://www.qnbcard.com.tr/kartlar-listesi")],
            "halkbank": [("bagis", HALKBANK_BAGIS,
                          "https://www.halkbank.com.tr/tr/bireysel/odemeler/"
                          "bagislar/kurban"),
                         ("reklam", HALKBANK_REKLAM,
                          "https://www.halkbank.com.tr/tr/bankamiz/haberler/x")],
            "is-bankasi": [("arsiv", ISBANK_ARSIV_743,
                            "https://www.isbank.com.tr/kampanyalar/akzonobel"),
                           ("kabuk", BOS_KABUK_METNI,
                            "https://www.isbank.com.tr/kampanyalar/bos"),
                           ("mukerrer", ISBANK_ARSIV_743,
                            "https://www.isbank.com.tr/kampanyalar/kopya")],
            "vakifbank": [("proje", VAKIFBANK_294,
                           "https://www.vakifbank.com.tr/tr/bireysel/krediler/"
                           "proje")],
            "teb": [("filenotfound", TEB_404,
                     "https://www.teb.com.tr/FileNotFound.aspx")],
        }
        for bank, rows in ornekler.items():
            bdir = os.path.join(kok, bank, "live")
            os.makedirs(bdir)
            for name, text, url in rows:
                with open(os.path.join(bdir, f"{name}.txt"), "w",
                          encoding="utf-8") as fh:
                    fh.write(text)
                with open(os.path.join(bdir, f"{name}.txt.meta.json"), "w",
                          encoding="utf-8") as fh:
                    json.dump({"bank_slug": bank, "source_url": url,
                               "title": name}, fh)

    def test_hicbir_belge_kaybolmaz(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kok = os.path.join(tmp, "docs")
            out = os.path.join(tmp, "out")
            os.makedirs(kok)
            self._korpus(kok)
            rc = main(["--docs", kok, "--out-dir", out])
            self.assertEqual(rc, 0)
            tr = _oku(os.path.join(out, "trainable.jsonl"))
            ex = _oku(os.path.join(out, "excluded.jsonl"))
            toplam = len(iter_docs(kok))
            self.assertEqual(toplam, 11)
            self.assertEqual(len(tr) + len(ex), toplam)
            kimlikler = {r["doc_id"] for r in tr} | {r["doc_id"] for r in ex}
            self.assertEqual(len(kimlikler), toplam)
            for row in ex:
                self.assertNotEqual(row["reason"], R_UYGUN)
            for row in tr:
                self.assertEqual(row["reason"], R_UYGUN)

    def test_her_gerekce_kodu_gercek_ornekle_ateslenir(self) -> None:
        """Kurgu korpusu 6 eleme kodunun 5'ini ateşler (R_KISA ayrı test edilir).

        R_KISA burada YOK, çünkü toplayıcı 200 karakterin altını hiç yazmıyor;
        onu ayrıca `TestKisa` sentetik olarak doğruluyor.
        """
        with tempfile.TemporaryDirectory() as tmp:
            kok = os.path.join(tmp, "docs")
            os.makedirs(kok)
            self._korpus(kok)
            docs = split_corpus(iter_docs(kok))
            kodlar = {d.decision for d in docs}
            for beklenen in (R_UYGUN, R_MUKERRER, R_BOS_KABUK, R_BLOG,
                             R_URUN_DEGIL, R_CERCEVE_AGIRLIKLI):
                self.assertIn(beklenen, kodlar, f"{beklenen} ateşlenmedi")

    def test_rapor_toplami_dogrular(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            kok = os.path.join(tmp, "docs")
            os.makedirs(kok)
            self._korpus(kok)
            docs = split_corpus(iter_docs(kok))
            rapor = build_report(docs, kok)
            self.assertIn("(TAMAM)", rapor)
            self.assertNotIn("(BOZUK)", rapor)
            self.assertIn("**Toplam belge:** 11", rapor)

    def test_bozuk_meta_belgeyi_dusurmez(self) -> None:
        """Okunamayan `.meta.json` sessiz kayba yol açmamalı."""
        with tempfile.TemporaryDirectory() as tmp:
            bdir = os.path.join(tmp, "vakifbank", "live")
            os.makedirs(bdir)
            with open(os.path.join(bdir, "a.txt"), "w", encoding="utf-8") as fh:
                fh.write(VAKIFBANK_294)
            with open(os.path.join(bdir, "a.txt.meta.json"), "w",
                      encoding="utf-8") as fh:
                fh.write("{bozuk json")
            docs = iter_docs(tmp)
            self.assertEqual(len(docs), 1)
            self.assertIsNone(docs[0].source_url)
            self.assertEqual(split_corpus(docs)[0].decision, R_UYGUN)


def _oku(path: str) -> list[dict[str, object]]:
    """JSONL satırlarını oku (dosyayı kapatarak — ResourceWarning çıkmasın)."""
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh]


def _row(doc_id: str, text: str, url: str) -> Doc:
    """`split_corpus`e verilecek ham belge (ölçümler orada dolduruluyor)."""
    bank = doc_id.split("--", 1)[0]
    return Doc(doc_id=doc_id, bank=bank,
               rel_path=f"{bank}/live/{doc_id.split('--', 1)[1]}.txt",
               text=text, title=doc_id, source_url=url)


if __name__ == "__main__":
    unittest.main()
