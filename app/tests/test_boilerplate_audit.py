"""Çerçeve kapsam denetimi testleri.

İlgili: ../scripts/boilerplate_audit.py · ../scripts/split_trainable.py
        ../docs/rapor/boilerplate-kapsam.md

## Neden bu testler

`boilerplate_audit.py` bir KARAR aracıdır: çıktısına bakarak "hangi bölüme
çerçeve ayıklaması uygulanmalı" sorusu cevaplanıyor. Ölçüm aracı sessizce
yanlış ölçerse, yanlış kararın kaynağı sonradan bulunamaz. Bu yüzden test
edilen şey "kod çalışıyor mu" değil, **ölçümün anlamı korunuyor mu**:

- **Referans hattan sapma yasağı.** `noktalama="kapali"` kipinin,
  `split_trainable.boilerplate_sets` ile BİREBİR aynı kümeleri üretmesi
  gerekir. Aksi hâlde raporlanan "önce/sonra" farkı noktalama sinyalinin
  katkısı değil, iki ayrı uygulamanın farkı olurdu ve bu fark hiçbir yerde
  görünmezdi.
- **Gruplama tanımının doğru ayırması.** Alt alan adları (Kuveyt Türk
  `saglamkart.`) ayrı şablon kullanıyor; gruplama bunları ayırmıyorsa
  "gruplama alternatifi ölçüldü" iddiası boştur.
- **Kayıp sınıflandırması.** Çerez/KVKK bloğundan çıkan bir alanın kaybı
  KAZANÇTIR; gerçek kampanya koşulundan çıkanınki zarardır. İkisi karışırsa
  rapor tam ters karar önerir.

## Metinlerin kaynağı

Aşağıdaki sabitler `data/raw/` altındaki GERÇEK belgelerden alınmıştır;
hangisinden geldiği her sabitin üstünde yazılıdır. Testler korpus
sayılarına BAĞLI DEĞİL — korpus büyüdükçe kırılmasınlar diye davranışı
sentetik kurgularla doğruluyorlar.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.boilerplate_audit import (
    LOSS_CHROME,
    LOSS_CROSS,
    LOSS_MENU,
    LOSS_REAL,
    LOSS_TITLES,
    ProseStats,
    _host,
    audit,
    boilerplate_sets_ext,
    classify_loss,
    clean_gold,
    group_docs,
    prose_stats,
    section_of,
    shingle_index,
    url_prefix,
)
from scripts.split_trainable import Doc, boilerplate_sets, core_text

# `data/raw/dunya-katilim/live/*.txt` belgelerinin HEPSİNDE birebir geçen
# çerez/KVKK bloğunun başı. Belge başına ~8,7 KB tutuyor ve 9 KB'lık sayfanın
# %96'sı bu blok.
CEREZ_BLOGU = (
    "Tüm site ziyaretçilerimizi daha iyi tanımak, sitemizdeki kullanıcı "
    "deneyimini kişiselleştirmek ve iyileştirmek için web sitemizde çerezler "
    "kullanıyoruz. Çerez ayarlarınızı yönetmek için Tercihler seçeneğine "
    "tıklayabilirsiniz. Talebiniz en kısa sürede ve en geç otuz (30) gün "
    "içinde ücretsiz olarak sonuçlandırılmaktadır."
)

# `data/raw/kuveyt-turk/products/isim-icin-leasing.txt` gezinme çubuğu —
# noktalama YOK, cümle yok, yalnız ürün adları.
MENU_METNI = (
    "Ana Sayfa İşim İçin Leasing Finansman Ürünleri Kartlar ve POS Nakit "
    "Yönetimi Dış Ticaret Sigorta ve Emeklilik Yatırım Leasing Tarım "
    "Bankacılığı Esnaf ve KOBİ ler Diğer Ürün ve Hizmetlerimiz Sürdürülebilir "
    "Ürünler Leasing Nedir Avantajları Nelerdir Kuveyt Türk avantajlar ile"
)

# `data/raw/albaraka/live/detay-giyim-ve-kozmetik-harcamalarinizda-...` —
# GERÇEK kampanya koşulu; noktalı, cümle yapılı.
KAMPANYA_KOSULU = (
    "Kampanya Başlangıç ve Bitiş Tarihi: Kampanya 1 Ağustos – 31 Ağustos 2026 "
    "tarihlerinde geçerlidir. Kampanya Kimler Faydalanabilir: 1 – 31 Ağustos "
    "2026 tarihleri arasında Albaraka Mobil'den kampanyaya katılıp, Albaraka "
    "World özellikli kredi kartını kullanan müşteriler faydalanabilir."
)

# `data/raw/turkiye-finans/products/altin-urunleri-default.txt` kenar
# çubuğundaki blog başlığı listesi — soru işaretli ama cümle değil.
BASLIK_LISTESI = (
    "Sağlık Sigortası Nedir? Neden Sağlık Sigortası Yaptırmalıyız? Katılma "
    "Hesabı Nedir, Nasıl Açılır? Tüm Renkleri Buluşturan Güzellikleriyle Hoş "
    "Geldin Ramazan! İşsizlik Maaşı Nedir? Trafik Cezası Sorgulama"
)


def _doc(doc_id: str, bank: str, rel_path: str, text: str,
         url: str | None = None) -> Doc:
    return Doc(doc_id=doc_id, bank=bank, rel_path=rel_path, text=text,
               source_url=url)


class BolumVeUrlTesti(unittest.TestCase):
    """Gruplama anahtarının parçaları doğru okunuyor mu?"""

    def test_bolum_yolun_ikinci_parcasidir(self):
        """Bölüm bir TOPLAMA KANALIDIR ve şablonu belirler.

        Aynı bankanın `docs` PDF'i ile `live` HTML sayfası tek bir ortak
        n-gram bile paylaşmaz; ikisi aynı gruba konursa `BOILERPLATE_MIN_DOCS`
        eşiği hiçbir kromu yakalamaz ve ayıklama sessizce hiç çalışmaz.
        """
        self.assertEqual(section_of(os.path.join("albaraka", "live", "a.txt")),
                         "live")
        self.assertEqual(section_of(os.path.join("albaraka", "docs", "a.txt")),
                         "docs")

    def test_kokteki_belge_bolumsuz_kalir(self):
        """Bölümsüz belge kendi kovasına düşmeli, `live`e karışmamalı."""
        self.assertEqual(section_of(os.path.join("albaraka", "a.txt")),
                         "(kok)")

    def test_port_alan_adini_bolmez(self):
        """`...com.tr` ile `...com.tr:443` AYNI sitedir.

        Korpusta Türkiye Finans'ın 7 belgesi `:443` portuyla geliyor. Ayrı
        grup sayılırlarsa `BOILERPLATE_MIN_DOCS`ın altında kalıp hiç
        ayıklanmazlar ve raporda "bu belgelerde çerçeve yok" görünür — oysa
        gruplama hatasıdır.
        """
        self.assertEqual(_host("https://www.turkiyefinans.com.tr:443/tr-tr/a"),
                         _host("https://www.turkiyefinans.com.tr/tr-tr/a"))

    def test_yerellik_parcasi_onek_sayilmaz(self):
        """`/tr/` ve `/tr-tr/` hiçbir şeyi ayırmaz.

        Albaraka'nın TÜM yolları `/tr/...` ile başlıyor. Yerelleştirme parçası
        önek sayılsaydı `banka-bolum-yol` gruplaması `banka-bolum`e çöker ve
        "daha ince gruplama ölçüldü" iddiası yanlış olurdu.
        """
        self.assertEqual(url_prefix("https://www.albaraka.com.tr/tr/kampanyalar/x"),
                         "kampanyalar")
        self.assertEqual(url_prefix("https://x.com.tr/tr-tr/urunler/y"),
                         "urunler")

    def test_alt_alan_adi_ayri_grup_olur(self):
        """Mentör uyarısı: şablon banka İÇİNDE değişiyor.

        Kuveyt Türk'ün `saglamkart.` ve `milesandsmiles.` alt alan adları ayrı
        şablon kullanıyor. `banka-bolum-yol` bunları ayırmıyorsa gruplama
        alternatifi hiçbir şey ölçmüyor demektir.
        """
        docs = [
            _doc("a", "kuveyt-turk", os.path.join("kuveyt-turk", "live", "a.txt"),
                 "x", "https://www.kuveytturk.com.tr/kampanyalar/a"),
            _doc("b", "kuveyt-turk", os.path.join("kuveyt-turk", "live", "b.txt"),
                 "x", "https://saglamkart.kuveytturk.com.tr/kampanyalar/b"),
        ]
        self.assertEqual(len(group_docs(docs, "banka-bolum-yol")), 2)
        self.assertEqual(len(group_docs(docs, "banka-bolum")), 1)

    def test_melez_gruplama_kucuk_alan_adini_ana_kovaya_dusurur(self):
        """Eşiğin altında kalan alan adı AYRI GRUP OLMAMALI.

        3 belgenin altındaki bir grup `BOILERPLATE_MIN_DOCS` yüzünden hiç
        çerçeve üretmez; ayrı bırakılırsa o belgeler sessizce hiç
        temizlenmez ve rapor bunu "o sayfalarda krom yok" diye gösterir.
        `banka-bolum-konak` bu yüzden küçük alan adlarını ana kovaya geri
        düşürüyor — `banka-bolum-yol`un ölçülen kaybı (çerçeve %42,4 → %41,5)
        tam olarak bu parçalanmadan geliyordu.
        """
        ana = [
            _doc(f"a{i}", "banka-x", os.path.join("banka-x", "live", f"a{i}.txt"),
                 "x", f"https://www.banka-x.com.tr/kampanyalar/a{i}")
            for i in range(4)
        ]
        tek = _doc("z", "banka-x", os.path.join("banka-x", "live", "z.txt"),
                   "x", "https://kart.banka-x.com.tr/kampanyalar/z")
        gruplar = group_docs([*ana, tek], "banka-bolum-konak")
        self.assertEqual(len(gruplar), 2)
        buyuk = max(gruplar.values(), key=len)
        self.assertEqual(len(buyuk), 4)
        self.assertIn("z", {d.doc_id for g in gruplar.values() for d in g})

    def test_melez_gruplama_buyuk_alan_adini_ayirir(self):
        """Eşiği aşan alt alan adı KENDİ şablonunu beslemeli.

        Ölçüm: 41 alt alan adı belgesinde çerçeve %32,7'den %43,1'e çıkıyor.
        Ayırma çalışmazsa bu 10,4 puan sessizce kaybolur.
        """
        docs = [
            _doc(f"a{i}", "banka-x", os.path.join("banka-x", "live", f"a{i}.txt"),
                 "x", f"https://www.banka-x.com.tr/kampanyalar/a{i}")
            for i in range(4)
        ] + [
            _doc(f"k{i}", "banka-x", os.path.join("banka-x", "live", f"k{i}.txt"),
                 "x", f"https://kart.banka-x.com.tr/kampanyalar/k{i}")
            for i in range(3)
        ]
        gruplar = group_docs(docs, "banka-bolum-konak")
        self.assertEqual(sorted(len(g) for g in gruplar.values()), [3, 4])


class NoktalamaSinyaliTesti(unittest.TestCase):
    """İkinci sinyal gerçekten menüyü düzyazıdan ayırıyor mu?"""

    def test_menu_duzyazi_degildir(self):
        """Menüde nokta-virgül yoktur; sinyalin varlık sebebi budur."""
        self.assertFalse(prose_stats(MENU_METNI).is_prose)

    def test_kampanya_kosulu_duzyazidir(self):
        """Gerçek kampanya koşulu noktalı ve cümle yapılıdır."""
        self.assertTrue(prose_stats(KAMPANYA_KOSULU).is_prose)

    def test_virgullu_liste_duzyazi_sayilmaz(self):
        """Noktalama oranı TEK BAŞINA yetmez, CÜMLE SONU da aranır.

        Virgülle ayrılmış bir menü listesi noktalama oranı testini rahatça
        geçer. Kısa bloklarda ortalama cümle uzunluğu da eşiğin altında kalır
        (25 sözcük < 30), yani o koşul da kurtarmaz. Ayrımı yapan tek şey
        `sentences >= 1` koşuludur — bu yüzden ayrı bir koşul olarak duruyor.
        """
        liste = ("Krediler, Kartlar, Mevduat, Sigorta, Yatırım, Leasing, "
                 "Faktoring, Dış Ticaret, Nakit Yönetimi, POS, Sigorta, "
                 "Emeklilik, Tarım, Esnaf, KOBİ, Kurumsal, Ticari, Bireysel, "
                 "Dijital, Şube, ATM, Çağrı Merkezi, İnternet, Mobil, Web")
        stats = prose_stats(liste)
        self.assertGreater(stats.punct_per_word, 0.04)
        self.assertLess(stats.mean_sentence_words, 30)
        self.assertEqual(stats.sentences, 0)
        self.assertFalse(stats.is_prose)

    def test_bos_blok_cokmez(self):
        """Sözcüksüz blok sıfır döner, sıfıra bölme yapmaz."""
        self.assertEqual(prose_stats("   ").is_prose, False)
        self.assertEqual(prose_stats(""), ProseStats(0, 0.0, 0.0, 0))

    def test_indeks_duzyazi_kumesini_ayirir(self):
        """`shingle_index` düzyazı gramları menü gramlarından ayırmalı.

        Düzyazı testi ±24 sözcüklük GENİŞ blokta yapıldığı için metnin
        düzyazı yarısı yeterince uzun olmalı; bu kurguda koşul metni iki kez
        yazılarak menünün pencereyi bastırması engellendi. Ölçülen davranış
        budur: menüye komşu ilk kampanya cümlesi, penceresi menüyle dolduğu
        için düzyazı sayılmayabilir — sinyalin ölçülmüş zayıflığı (bkz.
        `PROSE_MIN_PUNCT_RATIO` yorumu) burada da görünür.
        """
        metin = MENU_METNI + " " + KAMPANYA_KOSULU + " " + KAMPANYA_KOSULU
        _, _, prose = shingle_index([metin, metin, metin])
        self.assertTrue(any("geçerlidir" in g for g in prose))
        self.assertFalse(any("nakit yönetimi dış ticaret" in g for g in prose))


class ReferansHattanSapmaTesti(unittest.TestCase):
    """`kapali` kipi mevcut mekanizmayla BİREBİR aynı olmalı."""

    def test_kapali_kip_split_trainable_ile_ayni(self):
        """Ayrılık olursa 'noktalamanın katkısı' ölçümü anlamsızlaşır.

        `boilerplate_audit` çerçeve kümesini yeniden uyguluyor; `kapali` kipi
        referans hattır. İki uygulama ayrışırsa raporlanan önce/sonra farkı
        noktalama sinyalinin değil, iki ayrı kodun farkı olur ve bu fark
        hiçbir yerde görünmez.
        """
        metinler = [
            CEREZ_BLOGU + " Konut finansmanı %2,05 kâr payı oranı 120 ay vade.",
            CEREZ_BLOGU + " Taşıt finansmanı %3,15 kâr payı oranı 48 ay vade.",
            CEREZ_BLOGU + " İhtiyaç finansmanı %4,25 kâr payı oranı 36 ay vade.",
            CEREZ_BLOGU + " " + MENU_METNI,
        ]
        beklenen = boilerplate_sets(metinler)
        alinan = boilerplate_sets_ext(metinler, punctuation="kapali")
        self.assertEqual(beklenen[0], alinan[0])
        self.assertEqual(beklenen[1], alinan[1])

    def test_bilinmeyen_kip_reddedilir(self):
        """Yazım hatası sessizce referans hatta düşmemeli."""
        with self.assertRaises(ValueError):
            boilerplate_sets_ext(["a b c"] * 3, punctuation="noktalama")

    def test_esik_alti_grup_hic_ayiklanmaz(self):
        """3 belgenin altında çerçeve çıkarılmaz — iki belgenin ORTAK gerçek
        içeriği silinirdi. Kip ne olursa olsun bu koruma geçerli."""
        for kip in ("kapali", "dar", "genis"):
            boiler, protected = boilerplate_sets_ext(
                [KAMPANYA_KOSULU, KAMPANYA_KOSULU], punctuation=kip)
            self.assertEqual((boiler, protected), (set(), set()), kip)


class NoktalamaKipleriTesti(unittest.TestCase):
    """`dar` daraltmalı, `genis` genişletmeli — yön testleri."""

    def _kurgu(self) -> list[str]:
        """24 belgelik bir `live` bölümü; 5'i aynı kampanya ŞABLONUNU paylaşır.

        Grup boyu KASITLI olarak büyük: koruma eşiği
        `max(3, ceil(0,25 · N))` olduğu için 5 belgelik bir grupta eşik 3'e
        düşer ve 5 kardeşte geçen metin hiçbir kipte korunamaz. Albaraka'nın
        gerçek durumu bu değil — `albaraka/live` 91 belge, "World'e özel N
        taksit" ailesi 5-10 belge, yani ailenin payı %25'in ALTINDA.
        """
        ortak = ("Kampanyadan Kimler Faydalanabilir? Albaraka World özellikli "
                 "kredi kartını kullanarak ilgili koşullarda harcama yapan "
                 "tüm müşterilerimiz kampanyadan faydalanabilir. Kampanya "
                 "koşullarında değişiklik yapma hakkı saklıdır.")
        aile = [f"{m} mağazasında alışveriş yapın. {ortak}"
                for m in ("Bauhaus", "Civil", "Deichmann", "LCW", "Pegasus")]
        digerleri = [
            f"Konut finansmanı {n} numaralı sayfa. Detaylı bilgi şubelerimizde."
            for n in range(19)
        ]
        return aile + digerleri

    def test_genis_kip_ortak_kosulu_korur(self):
        """Şablon kardeşlerinin ortak KOŞUL metni SAYISIZDIR.

        `SIGNAL_MIN_FRACTION` koruması yalnız oran/tutar/taksit/vade taşıyan
        gramları görür; bu koşul metninde sayı yok, dolayısıyla koruma devreye
        girmez ve gerçek koşul metni menüyle aynı kefeye düşer — ölçülen 37
        `kampanya_kosullari` kaybının kaynağı bu. `genis` kip tam olarak bu
        boşluğu kapatmak için var.
        """
        metinler = self._kurgu()
        _, korunan_kapali = boilerplate_sets_ext(metinler, punctuation="kapali")
        boiler, korunan_genis = boilerplate_sets_ext(metinler,
                                                     punctuation="genis")
        self.assertEqual(korunan_kapali, set())
        self.assertGreater(len(korunan_genis), 0)
        self.assertIn("faydalanabilir",
                      core_text(metinler[0], boiler, korunan_genis))

    def test_kapali_kip_ortak_kosulu_yer(self):
        """Referans hat aynı metni YİYOR — `genis` kipin varlık gerekçesi.

        Bu test `test_genis_kip_ortak_kosulu_korur` ile ÇİFT oluşturuyor:
        biri kazancı, öbürü kaybı gösteriyor. Tek başına "genis korudu"
        demek, referans hattın zaten koruyor olma ihtimalini elemez.
        """
        metinler = self._kurgu()
        boiler, korunan = boilerplate_sets_ext(metinler, punctuation="kapali")
        self.assertNotIn("faydalanabilir",
                         core_text(metinler[0], boiler, korunan))

    def test_dar_kip_korumayi_daraltir(self):
        """`dar` kipte koruma `kapali` kipin ALT KÜMESİ olmalı.

        Daralma yönü tersine dönerse rapordaki "sızıntı azaldı" yorumu
        yanlış sebebe bağlanır.
        """
        metinler = [
            f"{ad} Taksitli Nakit Avans Vadeli Mevduat Kredi Kartı POS "
            f"Sigorta Yatırım Leasing Faktoring Dış Ticaret Nakit Yönetimi"
            for ad in ("Bir", "Iki", "Uc", "Dort")
        ]
        _, kapali = boilerplate_sets_ext(metinler, punctuation="kapali")
        _, dar = boilerplate_sets_ext(metinler, punctuation="dar")
        self.assertTrue(dar.issubset(kapali))


class KayipSiniflandirmasiTesti(unittest.TestCase):
    """Kaybın zararlı mı temizlik mi olduğu doğru okunuyor mu?"""

    def test_cerez_blogundan_cikan_alan_krom_sayilir(self):
        """KVKK metnindeki 'ücretsiz' masraf_durumu DEĞİLDİR.

        Ölçülen halüsinasyon: 91 belgede `masraf_durumu = "ücretsiz"` KVKK
        başvuru cümlesinden geliyordu. Bu alanın çekirdekte kaybolması
        KAZANÇTIR; 'zararlı kayıp' sayılırsa rapor ayıklamayı haksız yere
        suçlar.
        """
        yer = CEREZ_BLOGU.index("ücretsiz")
        self.assertEqual(
            classify_loss(CEREZ_BLOGU, yer, yer + len("ücretsiz")),
            LOSS_CHROME)

    def test_menuden_cikan_alan_menu_sayilir(self):
        """Gezinme çubuğundaki 'Emeklilik' hedef_kitle DEĞİLDİR."""
        yer = MENU_METNI.index("Emeklilik")
        self.assertEqual(
            classify_loss(MENU_METNI, yer, yer + len("Emeklilik")), LOSS_MENU)

    def test_baslik_listesi_ayri_sinifta(self):
        """Blog başlıkları soru işaretiyle düzyazı testini geçiyor.

        Yapısal ayrım: başlık listesinde NOKTA yok, soru işareti çok. Bu
        kural olmadan 60 `hedef_kitle` halüsinasyonu 'gerçek kayıp' sayılıyor
        ve kapsam kararı ters yöne dönüyordu.
        """
        yer = BASLIK_LISTESI.index("Hoş Geldin")
        self.assertEqual(
            classify_loss(BASLIK_LISTESI, yer, yer + len("Hoş Geldin")),
            LOSS_TITLES)

    def test_gercek_kampanya_kosulu_zararli_sayilir(self):
        """Gerçek koşul metninin kaybı ZARARDIR ve öyle raporlanmalı."""
        yer = KAMPANYA_KOSULU.index("Kampanya Kimler")
        self.assertEqual(
            classify_loss(KAMPANYA_KOSULU, yer, yer + 15), LOSS_REAL)

    def test_capraz_kampanya_blogu_isaretlenir(self):
        """Komşu kampanyanın oranı bu belgenin oranı değildir (T-019)."""
        metin = ("Diğer Kampanyalar English Home'da %15 İndirim! Detaylı "
                 "Bilgi. Sepetinizde geçerlidir, kaçırmayın.")
        yer = metin.index("15")
        self.assertEqual(classify_loss(metin, yer, yer + 2), LOSS_CROSS)

    def test_offset_yoksa_zararli_sayilir(self):
        """Bilinmeyen lehimize yazılmaz — offset yoksa kayıp zararlıdır."""
        self.assertEqual(classify_loss("herhangi bir metin", None, None),
                         LOSS_REAL)


class DenetimAkisiTesti(unittest.TestCase):
    """Uçtan uca: denetim korpusu OKUR, hiçbir şey YAZMAZ."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        live = os.path.join(self.root, "banka-x", "live")
        os.makedirs(live)
        # 4 kardeş: ortak çerez bloğu + kendine özgü kampanya cümlesi.
        for i, magaza in enumerate(("Bauhaus", "Civil", "Deichmann", "Pegasus")):
            metin = (f"{magaza} alışverişlerinizde %{i + 2},05 indirim ve "
                     f"{12 + i} ay vade fırsatı sizi bekliyor. " + CEREZ_BLOGU)
            with open(os.path.join(live, f"k{i}.txt"), "w",
                      encoding="utf-8") as fh:
                fh.write(metin)
        self.addCleanup(self.tmp.cleanup)

    def test_denetim_korpusu_degistirmez(self):
        """Denetim aracı ham veriye DOKUNMAZ (CLAUDE.md: raw değişmezdir)."""
        onces = {p: os.path.getmtime(os.path.join(r, p))
                 for r, _, fs in os.walk(self.root) for p in fs}
        audit(list(_read(self.root)), "banka-bolum", "kapali")
        sonras = {p: os.path.getmtime(os.path.join(r, p))
                  for r, _, fs in os.walk(self.root) for p in fs}
        self.assertEqual(onces, sonras)

    def test_cerez_blogu_cerceveye_gider_kampanya_kalir(self):
        """Denetimin temel iddiası: krom gider, kampanya cümlesi kalır."""
        sonuc = audit(list(_read(self.root)), "banka-bolum", "kapali")
        self.assertGreater(sonuc.boiler_ratio, 0.5)
        self.assertEqual(sonuc.chrome_leaks, 0)

    def test_dusen_belge_finansal_sinyal_ister(self):
        """Sinyalsiz saf menü sayfasının %95 küçülmesi BAŞARIDIR, alarm değil.

        `dusen` ölçütü sinyal koşulunu düşürürse rapor her menü sayfasını
        'içerik kaybı' diye sayar ve kapsam kararı gereksiz yere daralır.
        """
        sonuc = audit(list(_read(self.root)), "banka-bolum", "kapali")
        self.assertTrue(all(d.has_signal for d in sonuc.dropped))

    def test_gold_temizleme_metni_degistirir_kaydi_korur(self):
        """Gold temizleme yalnız `text` alanına dokunmalı.

        Alan/etiket bilgisi bozulursa eval önce/sonra farkı temizliğin değil,
        bozulan gold'un farkı olur.
        """
        import json
        gold = os.path.join(self.root, "gold.json")
        with open(gold, "w", encoding="utf-8") as fh:
            json.dump([{"id": "banka-x--k0", "text": _read_text(self.root, 0),
                        "campaign_type": "Kart", "fields": {}}], fh)
        kayitlar = clean_gold(gold, list(_read(self.root)), "banka-bolum",
                              "kapali")
        self.assertEqual(kayitlar[0]["campaign_type"], "Kart")
        self.assertNotIn("çerezler", kayitlar[0]["text"])
        self.assertIn("Bauhaus", kayitlar[0]["text"])

    def test_korpusta_olmayan_gold_kaydi_dokunulmadan_gecer(self):
        """Eşleşmeyen kayıt SESSİZCE BOZULMAMALI.

        Metni boşaltmak, eval'de o belgenin tüm alanlarını kaçırma sayardı ve
        'temizlik gerileme yarattı' diye okunurdu — oysa eşleşme hatasıdır.
        """
        import json
        gold = os.path.join(self.root, "gold2.json")
        with open(gold, "w", encoding="utf-8") as fh:
            json.dump([{"id": "yok--boyle-bir-belge", "text": "el değmemiş"}],
                      fh)
        kayitlar = clean_gold(gold, list(_read(self.root)), "banka-bolum",
                              "kapali")
        self.assertEqual(kayitlar[0]["text"], "el değmemiş")


def _read(root: str):
    from scripts.split_trainable import iter_docs
    return iter_docs(root)


def _read_text(root: str, i: int) -> str:
    with open(os.path.join(root, "banka-x", "live", f"k{i}.txt"),
              encoding="utf-8") as fh:
        return fh.read()


if __name__ == "__main__":
    unittest.main()
