"""D3 — dipnot blokları ve `kampanya_kosullari` bağlantısı.

Mentörlük toplantısında tespit edilen çıkarım hatası (aksiyon planı §5.1-D3):
"gerçek kısıtlar sayfanın altındaki yıldızlı/küçük punto dipnotlarda saklı".

## Kök neden

`preprocessing.clean.split_sentences` cümle sınırını `[.!?]\\s+` + ileri-bakış
`[A-Za-zÇĞİÖŞÜçğıöşü0-9]` ile buluyor. Dipnot işaretleri (`*`, `•`) bu sınıfta
DEĞİL; dolayısıyla tüm dipnot listesi bir önceki cümleye yapışıyor, tek bir
400+ karakterlik "cümle" oluyor ve `kampanya_kosullari`nın uzunluk filtresine
takılıp tamamen düşüyordu. `clean.py` bu görevin dokunma alanı dışında olduğu
için segmentasyon `extract.py` içinde ayrıca yapılır.

## Ölçüm (2026-08-07, `data/raw` altındaki 1759 belge)

    dipnot/madde imli blok çıkarılan belge            : 242
      gerçek kısıt taşıyan dipnotu olan belge         :  46
        koşullara EKLENEN belge                       :  42  (74 kısıt)

    "ilk N müşteri/kişi" KONTENJANI geçen belge       :  25
      kontenjan koşullarda görünen belge   4 -> 23

Kontenjan kaçırmanın bedeli yüksek: kullanıcı için kampanyanın en belirleyici
kısıtıdır ve "sınırl…" tetikleyici listesinde HİÇ YOKTU.

## Ölçülmüş yanlış deneme — tekrarlanmasın

`_KISIT_RE`'nin tamamını GÖVDE cümlelerine tetikleyici yapmak denendi:
kontenjan görünürlüğü 4 -> 12'ye çıktı ama gold'da `kampanya_kosullari` F1'i
0.733 -> 0.400'e (TP 11 -> 6), mikro-F1 0.647 -> 0.571'e düştü. Sebep: gold'un
koşul listeleri bu çıkarıcının çıktısından ön-etiketlenip hakemlenmiş, yani
eşleşme KÜME BİREBİRdir ve listeye eklenen her cümle bir TP'yi düşürür.
Bu yüzden gövdeye yalnızca dar kontenjan kalıbı eklendi; geri kalan kısıtlar
SADECE dipnot bloklarında aranır. Gold'da hiçbir gerileme yok.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.extraction.rules.extract import (
    extract_dipnotlar,
    extract_kampanya_kosullari,
)


def _kosullar(metin: str) -> list[str]:
    f = extract_kampanya_kosullari(metin)
    return list(f.canonical_value) if f else []


class TestDipnotSegmentasyonu(unittest.TestCase):
    """`extract_dipnotlar` blokları AYRI çıkarır — kendi başına kullanılabilir."""

    def test_yildizli_dipnot_onceki_cumleden_ayrilir(self) -> None:
        """`albaraka--detay-vade-farksiz-kampanyasi` biçimi.

        Cümle bölücü `*`'ı sınır saymadığı için dipnot önceki cümleye
        yapışıyordu; ayrı segmentasyon olmadan hiç görünmüyor.
        """
        metin = ("Pratik Finansman Kart sayfasını ziyaret edebilirsiniz. "
                 "*Kampanya katılım sağlayan ilk 2.000 kişi ile sınırlandırılmıştır. "
                 "*Bankamız kampanyayı durdurma hakkını saklı tutar.")
        self.assertEqual(
            extract_dipnotlar(metin),
            ["Kampanya katılım sağlayan ilk 2.000 kişi ile sınırlandırılmıştır",
             "Bankamız kampanyayı durdurma hakkını saklı tutar"])

    def test_madde_imi_de_dipnottur(self) -> None:
        """`vakif-katilim/live/detay-troy-kredi-karti-ile-50si-bizden` biçimi.

        Kontenjan kısıtı geçen 25 belgenin 8'inde kısıt yıldızlı dipnotta
        değil, sayfa altındaki madde imli "Kampanya Şartları" listesindeydi.
        """
        metin = ("Kampanya Şartları • Kampanyaya katılan VKart TROY Kredi Kartı "
                 "sahiplerinden uygun koşulları sağlayan ilk 500 kişi "
                 "faydalanabilecektir. • Kuyum harcamaları dahil değildir.")
        dipnotlar = extract_dipnotlar(metin)
        self.assertEqual(len(dipnotlar), 2)
        self.assertIn("ilk 500 kişi", dipnotlar[0])

    def test_binlik_ayirici_dipnotu_bolmez(self) -> None:
        """'.' hem cümle sonu hem BİNLİK AYIRICIDIR: "2.000 kişi" bölünmemeli."""
        metin = "Açıklama. *Kampanya ilk 2.000 kişi ile sınırlandırılmıştır."
        self.assertEqual(extract_dipnotlar(metin),
                         ["Kampanya ilk 2.000 kişi ile sınırlandırılmıştır"])

    def test_kisa_baglanti_etiketi_dipnot_sayilmaz(self) -> None:
        """"*Detaylı bilgi" gibi kısa parçalar koşul değil, bağlantı etiketidir."""
        self.assertEqual(extract_dipnotlar("Metin. *Detaylı bilgi."), [])

    def test_mukerrer_dipnot_tekrar_eklenmez(self) -> None:
        metin = ("*Kampanya ilk 1.000 kişi ile sınırlıdır. "
                 "*Kampanya ilk 1.000 kişi ile sınırlıdır.")
        self.assertEqual(len(extract_dipnotlar(metin)), 1)


class TestDipnotKosullaraBaglanir(unittest.TestCase):
    """Dipnot blokları `kampanya_kosullari` alanına bağlanır."""

    def test_kontenjan_kisiti_kosullara_girer(self) -> None:
        """Ölçülen kaçırma sınıfı: "ilk N kişi ile sınırlıdır".

        `triggers` listesinde "sınırl…" hiç yoktu; 25 belgede geçen bu kısıt
        koşul olarak hiç görünmüyordu (ölçüm: 4 -> 23 belge).
        """
        metin = ("Kampanya kapsamında alışveriş yapabilirsiniz. "
                 "*Kampanya sonradan taksitlendirme yapan ilk 5.000 kişi ile "
                 "sınırlıdır.")
        self.assertTrue(any("ilk 5.000 kişi ile sınırlıdır" in k
                            for k in _kosullar(metin)))

    def test_uzun_govde_cumlesine_yapisan_dipnot_kurtarilir(self) -> None:
        """Gerçek sayfa düzeni: dipnot 400+ karakterlik bir gövdeye yapışır.

        Cümle bölücü `*`'ı sınır saymadığı için birleşik parça uzunluk
        filtresine takılıp DÜŞÜYORDU — yani kısıt tamamen kayboluyordu.
        Ayrı segmentasyon sayesinde dipnot tek başına kurtarılır.
        """
        govde = ("Kampanyadan yararlanmak isteyen müşterilerimiz mobil "
                 "uygulamamız üzerinden başvurularını tamamlayabilir ve "
                 "ilerleyen dönemde kampanya detaylarını yine aynı ekran "
                 "üzerinden takip edebilirler, ayrıca şubelerimizden de "
                 "bilgi alınabilir ve süreç hakkında ayrıntılı yönlendirme "
                 "talep edilebilir; başvuru sonrası bilgilendirme mesajı "
                 "kayıtlı cep telefonu numarasına iletilecektir. ")
        metin = govde + "*Kampanya katılımı ilk 1.000 kişi için geçerlidir."
        # Birleşik parça 400 karakter sınırını aşar -> gövde yolu onu ELER.
        self.assertGreater(len(metin), 400)
        self.assertEqual(_kosullar(metin),
                         ["Kampanya katılımı ilk 1.000 kişi için geçerlidir"])

    def test_kanal_ve_uyelik_sarti_kosullara_girer(self) -> None:
        """Katılım tarafında kısıt genelde ÜYELİK ya da KANAL şartıdır."""
        metin = ("Hemen başvurun ve kazanın. "
                 "*Kampanyadan yararlanmak için Paraf üye iş yerlerinde "
                 "alışveriş yapılması gerekir.")
        self.assertTrue(any("üye iş yer" in k for k in _kosullar(metin)))

    def test_pazarlama_dipnotu_kosul_sayilmaz(self) -> None:
        """Dipnotların çoğu sorumluluk reddi/yönlendirmedir; koşul değildir.

        Ölçütü dar tutmak (yalnız `_KISIT_RE`) alanın kesinliğini korur —
        `kampanya_kosullari` gold'da zaten P=0.611 ile en zayıf alan.
        """
        metin = ("Kampanya devam ediyor. "
                 "*Detaylı bilgi almak için Pratik Finansman Kart sayfasını "
                 "ziyaret edebilirsiniz.")
        self.assertEqual(_kosullar(metin), [])

    def test_kontenjan_govde_cumlesinde_de_yakalanir(self) -> None:
        """Kontenjan, gövdeye eklenen TEK yeni tetikleyicidir (dar ve tartışmasız)."""
        metin = ("Kampanya katılım sağlayan ilk 2.000 kişi ile "
                 "sınırlandırılmıştır. Albaraka Türk kampanyayı dilediği zaman "
                 "durdurabilir.")
        self.assertIn(
            "Kampanya katılım sağlayan ilk 2.000 kişi ile sınırlandırılmıştır.",
            _kosullar(metin))

    def test_boilerplate_dipnotta_da_elenir(self) -> None:
        """KVKK/çerez metni dipnotta da koşul değildir (mevcut filtre korunur)."""
        metin = ("Kampanya sürüyor. "
                 "*Kişisel veri işleme faaliyetleri yalnızca açık rıza ile "
                 "sınırlıdır.")
        self.assertEqual(_kosullar(metin), [])

    def test_mevcut_govde_kosullari_bozulmaz(self) -> None:
        """Gold'da TP olan davranış: tetikleyicili gövde cümleleri aynen gelir."""
        metin = ("Sadece TL cinsinde açılabilmektedir. "
                 "Katılma Hesabı açmak için hesabınızda bulunması gereken "
                 "minimum bakiye 5.000 TL'dir.")
        self.assertEqual(_kosullar(metin), [
            "Sadece TL cinsinde açılabilmektedir.",
            "Katılma Hesabı açmak için hesabınızda bulunması gereken "
            "minimum bakiye 5.000 TL'dir.",
        ])


if __name__ == "__main__":
    unittest.main()
