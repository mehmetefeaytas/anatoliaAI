"""P4: yakınlık kanıtının kaybı, sıra bağımlılığı DEĞİLDİR.

İlgili: ../eval/properties.py (`check_sentence_order_invariance`),
        ../src/comparison/contradiction.py (`_in_same_scope`, `MAX_SCOPE_CHARS`)

## Bu testlerin varlık sebebi — ÖLÇÜLDÜ (2026-08-12, CI koşusu 31642385024)

`eval.properties` CI'da BLOKLAYICI bir adımdır ve 1.782 belgede 1 ihlal
veriyordu. İhlal `test` işinin ikinci bloklayıcı hatasıydı: `unittest`
adımı düzeltilince ortaya çıktı — kapının beş koşu boyunca işe yaramamasının
sebebi buydu (ilk hata ikincisini gizliyordu).

İhlal:

    [P4_cumle_sirasi] kuveyt-turk/docs/medium-bireysel-finansman-talebi-
                      onay-ve-bilgilendirme-fo-4012-pdf.txt
        önce =['masrafsiz_ama_ucret']
        sonra=[]

## Kök neden: iki ÖLÇÜLMÜŞ kararın çatışması, hata değil

Ölçüldü, aynı belgede:

    düz metin : masraf@1641  tahsis bitiş@1294  ->  mesafe  347  < 400  ✓ yakalandı
    ters metin: masraf@6942  tahsis bitiş@2753  ->  mesafe 4189  > 400  ✗ yakalanmadı

`contradiction._in_same_scope` iki alanın `MAX_SCOPE_CHARS = 400` içinde
olmasını şart koşuyor. O şart keyfi değil: onsuz 849 belgedeki 4 adayın
**4'ü de hayaletti** ve aralarındaki mesafe 2.176–6.916 karakterdi; gerçek
çelişkiler 20–55 karakter aralığında duruyor.

Cümleleri ters çevirmek bu mesafeyi 347'den 4.189'a taşıyor. Yani ters
metinde çelişkinin kaybolması kuralın DOĞRU davranışıdır — 4.189 karakter
tam olarak hayalet profilidir. Bir **yakınlık** kuralından sıra
değişmezliği istemek, kuralın kendi kanıtını yok saymasını istemektir.

## Ayrım mekanik olarak ölçülüyor, elle muafiyet verilmiyor

Fark "kapsam etkisi mi, sıra bağımlılığı mı" sorusu tahminle değil ölçümle
cevaplanıyor: aynı iki metin, kapsam kapısı DEVRE DIŞI bırakılarak yeniden
değerlendiriliyor. Kapı kapalıyken kümeler eşitleniyorsa farkı yalnız
kapsam üretmiştir.

    kapsam 400      : ['masrafsiz_ama_ucret']  vs  []
    kapsam sınırsız : ['masrafsiz_ama_ucret']  vs  ['masrafsiz_ama_ucret']

Bu yüzden belge adına göre bir muafiyet listesi (allowlist) YAZILMADI:
liste, kuralın neden esnediğini değil hangi belgenin affedildiğini kaydeder
ve yeni bir belge aynı desene girdiğinde sessizce kırmızı yanar.

## Değişmezin dişleri KORUNUYOR

P4 asıl olarak H2 için yazılmıştı: "masrafsız ... tahsis 500 TL" çelişkiyi
yakalıyor, ters sırası kaçırıyordu (kök neden `re.search`in yalnız ilk
eşleşmeye bakmasıydı; `finditer` ile kapatıldı). O vakada iki span KOMŞU
cümlelerdedir ve ters çevirmek onları komşu BIRAKIR — mesafe küçük kalır,
kapsam değişmez, dolayısıyla kapsam kapısı farkı AÇIKLAMAZ ve P4 ihlali
bildirmeye devam eder. Muafiyet yalnız spanların birbirinden uzaklaştığı
durumda devreye giriyor.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eval.properties import check_sentence_order_invariance, kapsam_etkisi_mi
from src.comparison import contradiction as C
from src.preprocessing.clean import split_sentences

_BELGE = (_ROOT / "data/raw/kuveyt-turk/docs"
          / "medium-bireysel-finansman-talebi-onay-ve-bilgilendirme-fo-4012-pdf.txt")


class KapsamEtkisiIhlalSayilmaz(unittest.TestCase):
    """Gerçek korpus belgesi artık ihlal üretmiyor — ve sebebi ölçülüyor."""

    @classmethod
    def setUpClass(cls) -> None:
        if not _BELGE.exists():
            raise unittest.SkipTest(f"korpus belgesi yok: {_BELGE.name}")
        cls.metin = _BELGE.read_text(encoding="utf-8")

    def test_gercek_belge_ARTIK_ihlal_degil(self) -> None:
        ihlaller = check_sentence_order_invariance(self.metin, "kuveyt-turk-4012")
        self.assertEqual(
            [], ihlaller,
            "kapsam etkisi hâlâ sıra bağımlılığı sayılıyor: "
            + "; ".join(f"{v.before}->{v.after}" for v in ihlaller))

    def test_fark_gercekten_KAPSAMDAN_geliyor(self) -> None:
        """Muafiyetin dayanağı: kapı kapalıyken kümeler eşitleniyor."""
        ters = " ".join(reversed(split_sentences(self.metin)))
        self.assertTrue(
            kapsam_etkisi_mi(self.metin, ters),
            "fark kapsamla açıklanmıyor — o hâlde muafiyet dayanaksız")

    def test_belge_ARTIK_hic_celiski_uretmiyor_ve_SEBEBI(self) -> None:
        """⚠️ 2026-08-15: bu çit belgesi P4'ü ARTIK ZORLAMIYOR — sebebi ölçüldü.

        Eskiden bu test "kapı açıkken kümeler farklı olmalı" diyordu ve
        geçiyordu. Artık iki küme de BOŞ; yani yukarıdaki iki test bedava
        geçiyor. Bunu gizlemek yerine kayda geçiriyoruz.

        Sebep, oransal tahsis ücreti türetmesinin kaldırılmasıdır
        (`tests/test_tahsis_oransal_turetme.py`). Bu belgede ölçüldü:

            önce : tahsis_ucreti = 50,0 TL  @span 1221
                   kaynak "Tahsis Ücreti Limitin Anaparasının %0,5'i"
                   -> 50 TL sayısı metinde HİÇ GEÇMİYOR (uydurma)
                   masraf @1641 -> mesafe 347 < 400 -> çelişki YAKALANDI

            sonra: tahsis_ucreti = 57,5 TL  @ileride
                   kaynak "Tahsis Ücreti : 57,5 TL" -> metinde BİREBİR yazılı
                   masraf'a mesafe > 400 -> çelişki yakalanmıyor

        Yani `masrafsiz_ama_ucret` çelişkisi UYDURMA bir değere dayanıyordu.
        Değer düzeldi, çelişki düştü. Bu bir kayıp değil; CLAUDE.md §18/2'nin
        (bankalar arası çelişki tespiti) sahte bir dayanaktan kurtulmasıdır.

        Korpus genelinde doğrulandı: `python -m eval.properties` 1782 belgede
        **0 ihlal** veriyor — muafiyet yolu artık hiçbir belgede tetiklenmiyor.
        `kapsam_etkisi_mi`'nin dişleri sentetik olarak `DegismezinDisleriKORUNUYOR`
        sınıfında test edilmeye devam ediyor.

        Bu test, uydurma değer geri gelirse KIRILIR ve durumu haber verir.
        """
        ters = " ".join(reversed(split_sentences(self.metin)))
        from src.extraction.rules.extract import extract_all
        from src.schemas import Campaign

        def turler(t: str) -> set[str]:
            return {c.kind for c in C.detect(
                Campaign(bank_slug="?", raw_text=t, fields=extract_all(t)))}

        self.assertEqual(
            (turler(self.metin), turler(ters)), (set(), set()),
            "belge yeniden çelişki üretiyor — oransal türetme geri gelmiş "
            "olabilir; `tests/test_tahsis_oransal_turetme.py`'yi kontrol edin")

        alan = {f.field_name: f for f in extract_all(self.metin)}["tahsis_ucreti"]
        self.assertEqual(alan.canonical_value, {"value": 57.5, "currency": "TRY"})
        self.assertIn("57,5 TL", self.metin,
                      "değer metinde birebir geçmeli — türetilmiş olamaz")


class DegismezinDisleriKORUNUYOR(unittest.TestCase):
    """Muafiyet blanket değil: kapsamla açıklanmayan fark hâlâ ihlaldir."""

    def test_kapsam_ACIKLAMIYORSA_yordam_False_doner(self) -> None:
        """Muafiyet blanket değil: False dalı gerçekten çalışıyor.

        `kapsam_etkisi_mi` iki metin üzerinde saf bir yordamdır. Kapsam
        kapısı kapalıyken kümeler HÂLÂ farklıysa farkı kapsam üretmiyordur
        ve yordam False demek zorundadır. Aksi hâlde muafiyet her farkı
        yutar ve P4 tamamen susmuş olurdu.

        Burada ters çevirme değil, çelişkisi OLAN ve OLMAYAN iki ayrı metin
        veriliyor — fark hiçbir kapsam ayarıyla kapanamaz.
        """
        celiskili = "Masrafsızdır. Tahsis ücreti 500 TL."
        celiskisiz = "Konut finansmanında vade 120 aydır."
        self.assertFalse(
            kapsam_etkisi_mi(celiskili, celiskisiz),
            "kapsamla kapanamayan fark 'kapsam etkisi' sayıldı — "
            "muafiyet blanket hâle gelmiş")

    def test_fark_yoksa_P4_zaten_susar(self) -> None:
        """Sıraya duyarsız metin ihlal üretmez (muafiyete hiç gerek kalmaz)."""
        duz = "Konut finansmanında dosya masrafı 500 TL'dir. Vade 120 aydır."
        self.assertEqual([], check_sentence_order_invariance(duz, "sentetik"))

    def test_komsu_span_ters_cevrilse_de_KAPSAMDA_kalir(self) -> None:
        """H2 vakasının korunma mekanizması: komşuluk ters çevrilince bozulmaz."""
        duz = "Masrafsızdır. Tahsis ücreti 500 TL."
        ters = " ".join(reversed(split_sentences(duz)))
        for ad, metin in (("düz", duz), ("ters", ters)):
            with self.subTest(sira=ad):
                from src.extraction.rules.extract import extract_all
                f = {x.field_name: x for x in extract_all(metin)}
                m, t = f.get("masraf_durumu"), f.get("tahsis_ucreti")
                if m is None or t is None:
                    continue
                self.assertTrue(
                    C._in_same_scope(m, t),
                    f"{ad} sırada komşu spanlar kapsam dışına düştü — "
                    "H2 koruması bu varsayıma dayanıyor")


if __name__ == "__main__":
    unittest.main()
