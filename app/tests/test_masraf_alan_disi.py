"""`masraf_durumu`: "ücretsiz"in ÖZNESİ ürün değilse masraf iddiası değildir.

İlgili: ../src/extraction/rules/extract.py (`extract_masraf`),
        ./test_vade_tetikleyici.py (kardeş kapı — aynı hata sınıfı),
        ../src/preprocessing/blocks.py (bölge tespiti — neden yetmediği aşağıda)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-12, `data/gold/gold.v2.json`)

`masraf_durumu` gold setinde en çok DEĞER UYDURAN alandı: 10 yanlış
pozitifin **9'u halüsinasyondu** (gold "YOK" diyor, çıkarıcı değer üretti).
Alan aynı zamanda bileşik avantaj skorunda **ikinci en yüksek ağırlığa**
sahip (0,20 — `comparison/compare.py:697`), yani uydurma bir "masrafsız"
doğrudan "En Avantajlı" sıralamasını bozuyordu.

Dokuz halüsinasyonun kaynak metni tarandı; ikisi n>=3'lük TEK BİR AİLE:

| n | kaynak cümle | "ücretsiz" neyi niteliyor |
|---|---|---|
| 4 | "Katılım SMS'i ücretsiz olup; ... Turkcell, Vodafone ..." | SMS bedeli — KANAL |
| 3 | "Talebiniz ... otuz (30) gün içinde ücretsiz olarak sonuçlandırılmaktadır" | KVKK başvurusu — YASAL TALEP |

İkisinde de bedava olan şey **kampanyanın ürünü değil**: biri katılım
kanalı, biri kanuni başvurunun işlenmesi. Ürünün masrafı hakkında hiçbir
iddia yok.

## Ayırt ediciliğin ölçüsü — kapı meşru çıkarımı ELEMİYOR

Aynı yordam gold'daki 6 MEŞRU `masraf_durumu` çıkarımına da uygulandı:

| yordam | halüsinasyonda | meşruda |
|---|---|---|
| SMS cümlesi | **4/4** eşleşti | **0/6** |
| talep-sonuçlandırma cümlesi | **3/3** eşleşti | **0/6** |

Ayrım tesadüf değil, mesafeyle de doğrulandı: halüsinasyonlarda "SMS"
jetonu span'dan **3 karakter** geride; en yakın meşru vakada **5.222**.

## Neden `blocks.py` bölge tespiti YETMEDİ (ölçüldü, denendi)

`preprocessing/blocks.py` tam bu sorunu çözmek için yazılmış ve docstring'i
"KVKK'daki ücretsiz" örneğini birebir anıyor. Ama iki sebeple bu vakayı
kurtarmıyor:

1. `extract_all` `blocks.py`'ye **hiç danışmıyor** — modül yalnız özet
   (`summarize/ozet.py:109`) ve görünürlük (`api/main.py:195`) yollarında.
2. Danışsaydı bile yakalamazdı: `dunya-katilim--kampanyalar-carter-s`
   belgesinde son `alan_disi` işareti blok **[52]**, bölge `YAYILIM_BLOK=6`
   ile 53-58 bloklarını kapsıyor ve "ücretsiz" cümlesi blok **[59]** —
   yayılım tam bir blok önce sönüyor.

`YAYILIM_BLOK`'u büyütmek paylaşılan bir sabiti değiştirir ve özet/görünürlük
yollarını 1.782 belgede etkiler; bu yüzden burada CÜMLE kapsamlı yerel bir
kapı seçildi. Bölge yaklaşımı bir sonraki turun işi.

## Kapsam dışı bırakılan 2 halüsinasyon (bilerek)

- `dunya-katilim--kampanyalar-tod-paraf` — "TOD ayrıcalığını ücretsiz yaşa".
  Yapısal ikizi gold'da MEŞRU sayılıyor ("GastroClub üyeliği ... ücretsiz",
  `hayat-finans--...-gastroclub`). İki vaka çelişiyor; n=1 üzerinde kural
  yazmak ölçülmemiş bir desene kural yazmak olur.
- `albaraka--tr-kampanyalar` — "Ücretsiz İSPARK Otopark Kampanyası".
  Anotatör bunu BELGE düzeyinde gerekçelendirmiş (`notes._belge`:
  "KAMPANYA LİSTELEME sayfası ... tek bir kampanyaya ait olmayan
  değerler"). Çözümü cümle kapısı değil, liste sayfası tespiti.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.extraction.rules.extract import extract_masraf

# --------------------------------------------------------------------------- #
# Gerçek korpus cümleleri. Kısaltılmadı: kapı cümle kapsamıyla çalıştığı için
# cümle sınırları davranışın parçasıdır.
# --------------------------------------------------------------------------- #

SMS_METNI = (
    "Kampanyaya katılım için 5 TL'lik SMS gönderimi gerekmez. Banka "
    "sisteminde adınıza tanımlı telefon numarasından katılım sağlanmalıdır. "
    "Katılım SMS'i ücretsiz olup; kampanyaya katılabilmek için SMS'in "
    "Turkcell, Vodafone veya Türk Telekom operatörlerinden gönderilmesi "
    "gerekmektedir."
)

KVKK_METNI = (
    "Başvuruda; a) ad, soyadı ve başvuru yazılı ise imza b) Türkiye "
    "Cumhuriyeti vatandaşları için T.C. kimlik numarası d) talep konusu "
    "bulunmalıdır. Talebiniz en kısa sürede ve en geç otuz (30) gün içinde "
    "ücretsiz olarak sonuçlandırılmaktadır. Başvurunuza yönelik işlemlerin "
    "ayrı bir maliyeti gerektirmesi hâlinde, Kurul tarafından belirlenen "
    "tarifedeki ücret tarafınıza yansıtabilmektedir."
)


class AlanDisiOzneMasrafIddiasiDegil(unittest.TestCase):
    """Bedava olan şey ürün değilse `masraf_durumu` üretilmez."""

    def test_katilim_SMSi_ucretsiz_masraf_iddiasi_DEGIL(self) -> None:
        """SMS bedeli, ürünün masrafı hakkında bir şey söylemez."""
        self.assertIsNone(
            extract_masraf(SMS_METNI),
            "SMS'in ücretsiz olması 'ürün masrafsız' diye okundu")

    def test_KVKK_talep_ucretsiz_masraf_iddiasi_DEGIL(self) -> None:
        """Kanuni başvurunun ücretsiz işlenmesi ürün masrafı değildir."""
        self.assertIsNone(
            extract_masraf(KVKK_METNI),
            "KVKK başvuru cümlesi 'ürün masrafsız' diye okundu")


class MesruIddialarKORUNUR(unittest.TestCase):
    """Kapı, gerçek masraf iddiasına DOKUNMAZ — kazancın ön koşulu bu."""

    def test_masrafsiz_bankacilik_hala_yakalanir(self) -> None:
        f = extract_masraf(
            "Masrafsız bankacılık ile tanışabilir; mobil ve İnternet Şube "
            "üzerinden 7/24 FAST, havale ve EFT yapabilirsiniz.")
        self.assertIsNotNone(f, "'Masrafsız bankacılık' iddiası kayboldu")
        self.assertIs(f.canonical_value["has_fee"], False)

    def test_hesap_isletim_ucreti_alinmamaktadir_yakalanir(self) -> None:
        """Ürün-masrafı ismine bağlı negasyon — gold'un asıl dayanağı.

        Bu test önce `@unittest.expectedFailure` olarak yazıldı: ölçüldüğünde
        (2026-08-12) `normalize_fee_status` `-mAmAktAdIr` biçimini
        tanımıyordu ve cümle sessizce düşüyordu. Sonucu şuydu:
        `vakif-katilim--hesaplar-ozel-cari-hesaplar` belgesinde anotatörün
        gerekçe olarak yazdığı cümle ("hesap işletim ücreti alınmamaktadır",
        `notes.masraf_durumu`) HİÇ çıkarılmıyor; o belgedeki doğru sonuç
        ilgisiz bir "PTT ATM'lerinden ücretsiz" cümlesinden geliyordu —
        yani doğru cevap YANLIŞ span'dan.

        Kusur `test_masraf_negasyon_bicimleri.py` ile kapatıldı; işaret o
        yüzden kaldırıldı. Kapsam ayrımı bilinçliydi: orası KAPSAMA
        (recall), burası KESİNLİK (precision) kusuru.
        """
        f = extract_masraf(
            "Özel Cari Hesaplarda hesap işletim ücreti alınmamaktadır.")
        self.assertIsNotNone(f, "ürün ücreti negasyonu kayboldu")
        self.assertIs(f.canonical_value["has_fee"], False)

    def test_dosya_masrafi_tutari_yakalanir(self) -> None:
        f = extract_masraf("Konut finansmanında dosya masrafı 500 TL'dir.")
        self.assertIsNotNone(f)
        self.assertIs(f.canonical_value["has_fee"], True)

    def test_ayni_belgede_alan_disi_cumle_MESRU_iddiayi_gizlemez(self) -> None:
        """Kapı eşleşmeyi ATLAR, taramayı BİTİRMEZ.

        `finditer` döngüsünden erken çıkılsaydı, alan-dışı bir cümle
        belgenin gerçek masraf iddiasını gölgeleyebilirdi — halüsinasyonu
        susturup bilgi kaybı üretmek, kazanç değil takas olurdu.
        """
        f = extract_masraf(SMS_METNI + " Ayrıca dosya masrafı alınmaz.")
        self.assertIsNotNone(f, "alan-dışı cümle sonraki meşru iddiayı yuttu")
        self.assertIs(f.canonical_value["has_fee"], False)


class GoldSetiUzerindeUCTANUCA(unittest.TestCase):
    """Kapı gold'da ölçülen kazancı gerçekten veriyor mu?

    Birim testler deseni sınar; bu test SONUCU sınar. İkisi ayrı: desen
    doğru olup çağıran tarafta etkisiz kalabilir (`vade_ay`'da yaşandı).
    """

    @classmethod
    def setUpClass(cls) -> None:
        yol = _ROOT / "data/gold/gold.v2.json"
        cls.kayitlar = json.loads(yol.read_text("utf-8"))

    def _halusinasyon_sayisi(self) -> int:
        n = 0
        for kayit in self.kayitlar:
            if "masraf_durumu" not in set(kayit.get("absent_fields") or []):
                continue
            if extract_masraf(kayit["text"]) is not None:
                n += 1
        return n

    def _mesru_sayisi(self) -> int:
        n = 0
        for kayit in self.kayitlar:
            if "masraf_durumu" not in (kayit.get("fields") or {}):
                continue
            if extract_masraf(kayit["text"]) is not None:
                n += 1
        return n

    def test_halusinasyon_9dan_2ye_dustu(self) -> None:
        """Kalan 2, yukarıda gerekçesiyle kapsam dışı bırakılanlar."""
        self.assertLessEqual(
            self._halusinasyon_sayisi(), 2,
            "masraf_durumu halüsinasyonu 2'nin üstüne çıktı")

    def test_mesru_cikarim_sayisi_GERILEMEDI(self) -> None:
        """Gold'da değer taşıyan belgelerde üretim sürüyor mu.

        Sayı 6 → **5** düştü (19 Ağu 2026) ve bu bir gerileme DEĞİL, bir
        kapsam düzeltmesidir. `hayat-finans--…-gastroclub-ayricaliklari`
        belgesinde gold `masraf_durumu = {has_fee:false}` taşıyordu; kaynak
        cümle *"GastroClub üyeliği … ücretsiz!"*. HAKEM-03 turu bu değeri
        `absent_fields`'a taşıdı: üçüncü taraf bir avantaj programının üyelik
        bedeli, kampanyanın/ürünün kendisini kullanmanın maliyeti değildir ve
        belge kıyas tablosunda **"masrafsız" rozetiyle** görünüyordu
        (gerekçe: `data/gold/review/_hakem-turu-03-masraf-durumu.md`,
        kapsam kuralı: `ANNOTATION_GUIDE.md` §4).

        Yani payda küçüldü çünkü o belge artık "değer taşıyan" kümede değil.
        Motor tarafında da aynı kapsam kapısı açıldı (`_ALAN_DISI_OZNE_RE`
        club/kulüp kolu), bu yüzden halüsinasyon sayısı 2'de kaldı.
        """
        self.assertEqual(
            self._mesru_sayisi(), 5,
            "kapı meşru bir masraf iddiasını de eledi")


if __name__ == "__main__":
    unittest.main()
