"""Yayın paketinin kapıları — sızıntı, şema, dürüstlük uyarıları.

Çalıştır:  .venv/bin/python -m pytest tests/test_veri_seti_paketle.py -q
           (ya da: .venv/bin/python -m unittest tests.test_veri_seti_paketle)

## Neden bu testler — üç geri alınamaz hata

Yayımlanan bir veri seti geri çağrılamaz. İndirilen kopya, biz düzeltsek bile
yanlış kalır. Bu dosya üç hatayı çitler:

1. **Bölme sızıntısı.** Aynı belge hem `train` hem `test` içinde olursa,
   o bölme üzerinde ölçülen her sayı şişer ve kimse fark etmez. Burada
   gerçek risk somuttur: `gold.round1` ile `gold.v2` **5 `source_url`
   paylaşıyor** (aynı sayfa, iki hasat, farklı `content_hash`). Naif kayıt
   düzeyi bölme tam olarak buradan sızardı.

2. **Dataset card'dan bir dürüstlük uyarısının düşmesi.** Kartın tek
   farklılaştırıcısı, ölçümün kısıtlarını jüri fark etmeden bizim
   söylememizdir: makine anotasyonu, insan hakemliğinin olmayışı, iki κ'nın
   simetrik olmayışı, iki setin kıyaslanamazlığı. Bir yeniden yazımda
   bunlardan biri sessizce düşerse kart yalan söylemeye başlar.

3. **κ'ların rapor dosyalarından kayması.** Kart κ'ları sabit olarak taşır
   (rapor markdown'ını ayrıştırmak kırılgan olurdu). Karşılığında burada
   sabitin kaynak raporda GERÇEKTEN geçtiği doğrulanır.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.veri_seti_paketle import (
    ALANLAR,
    BEKLENEN,
    BOLME_ADLARI,
    KAPPA,
    ORANLAR,
    TOHUM,
    VARSAYILAN_ROUND1,
    VARSAYILAN_V2,
    bol,
    grupla,
    oku,
    paketle,
    sizinti_denetimi,
)
from tests._ortam_gereksinimleri import dosya_gerekir

ROUND1 = _ROOT / VARSAYILAN_ROUND1
V2 = _ROOT / VARSAYILAN_V2


def _kayit(kid: str, url: str, chash: str) -> dict:
    return {"id": kid, "bank_slug": "ornek", "source_url": url,
            "content_hash": chash, "text": "metin", "fields": {}, "absent_fields": []}


class Gruplama(unittest.TestCase):
    """Belge grubu = `source_url` VEYA `content_hash` paylaşan kayıtlar."""

    def test_ayni_url_tek_grup(self):
        kayitlar = [_kayit("a", "u1", "h1"), _kayit("b", "u1", "h2"),
                    _kayit("c", "u2", "h3")]
        gruplar = grupla(kayitlar)
        self.assertEqual(sorted(len(g) for g in gruplar), [1, 2])

    def test_ayni_hash_farkli_url_tek_grup(self):
        """Aynı metin başka bir URL altında duruyorsa da bölünemez."""
        kayitlar = [_kayit("a", "u1", "h1"), _kayit("b", "u2", "h1")]
        self.assertEqual(len(grupla(kayitlar)), 1)

    def test_zincirleme_birlesim(self):
        """a—b URL'den, b—c hash'ten bağlıysa üçü tek gruptur."""
        kayitlar = [_kayit("a", "u1", "h1"), _kayit("b", "u1", "h2"),
                    _kayit("c", "u3", "h2")]
        self.assertEqual([len(g) for g in grupla(kayitlar)], [3])

    def test_gruplama_kararli(self):
        kayitlar = [_kayit(f"k{i}", f"u{i // 2}", f"h{i}") for i in range(10)]
        self.assertEqual(grupla(kayitlar), grupla(kayitlar))


class Sizinti(unittest.TestCase):
    """Sızıntı denetimi hem yakalamalı hem de gerçek veride temiz çıkmalı."""

    def test_denetim_uydurma_sizintiyi_yakalar(self):
        """Denetim önce KENDİ çalıştığını ispatlamalı; yoksa 'temiz' anlamsız."""
        ihlaller = sizinti_denetimi({
            "train": [_kayit("a", "u1", "h1")],
            "val": [_kayit("b", "u1", "h9")],     # URL sızıntısı
            "test": [_kayit("c", "u5", "h1")],    # hash sızıntısı
        })
        birlesik = " ".join(ihlaller)
        self.assertIn("source_url", birlesik)
        self.assertIn("content_hash", birlesik)

    def test_gercek_bolme_sizintisiz(self):
        hepsi = oku(str(ROUND1)) + oku(str(V2))
        self.assertEqual(sizinti_denetimi(bol(hepsi)), [])

    def test_naif_kayit_duzeyi_bolme_sizardi(self):
        """Bu testin varlık sebebi: risk teorik değil, ÖLÇÜLDÜ.

        İki gold seti ortak `source_url` taşıyor. Grup birleştirmesi
        olmasaydı o belgeler iki bölmeye düşebilirdi.
        """
        r1, v2 = oku(str(ROUND1)), oku(str(V2))
        ortak = {r["source_url"] for r in r1} & {r["source_url"] for r in v2}
        self.assertGreater(len(ortak), 0,
                           "iki set artık ortak belge taşımıyorsa bu kapı gevşetilebilir")
        # Ortak URL'li her kayıt aynı bölmede olmalı.
        bolmeler = bol(r1 + v2)
        nerede: dict[str, set[str]] = {}
        for ad in BOLME_ADLARI:
            for k in bolmeler[ad]:
                nerede.setdefault(k["source_url"], set()).add(ad)
        for url in ortak:
            self.assertEqual(len(nerede[url]), 1, f"{url} birden çok bölmede")


class Bolme(unittest.TestCase):
    def setUp(self):
        self.hepsi = oku(str(ROUND1)) + oku(str(V2))
        self.bolmeler = bol(self.hepsi, tohum=TOHUM)

    def test_hicbir_kayit_kaybolmuyor_cogalmiyor(self):
        toplam = sum(len(self.bolmeler[a]) for a in BOLME_ADLARI)
        self.assertEqual(toplam, len(self.hepsi))
        kimlikler = [k["id"] for a in BOLME_ADLARI for k in self.bolmeler[a]]
        self.assertEqual(len(kimlikler), len(self.hepsi))

    def test_oranlar_hedefe_yakin(self):
        """Grup bölünmesindense sapma tercih edilir — tolerans %3 puan."""
        toplam = len(self.hepsi)
        for ad, hedef in zip(BOLME_ADLARI, ORANLAR, strict=True):
            gercek = len(self.bolmeler[ad]) / toplam
            self.assertAlmostEqual(gercek, hedef, delta=0.03, msg=ad)

    def test_deterministik(self):
        yeniden = bol(self.hepsi, tohum=TOHUM)
        for ad in BOLME_ADLARI:
            self.assertEqual([k["id"] for k in self.bolmeler[ad]],
                             [k["id"] for k in yeniden[ad]])

    def test_farkli_tohum_farkli_bolme(self):
        """Tohum gerçekten etkili olmalı; sabit bir bölmeyi 'seed=42' diye sunmayalım."""
        baska = bol(self.hepsi, tohum=7)
        self.assertNotEqual([k["id"] for k in self.bolmeler["test"]],
                            [k["id"] for k in baska["test"]])

    def test_bolme_alani_isaretli(self):
        for ad in BOLME_ADLARI:
            self.assertTrue(all(k.get("bolme") == ad for k in self.bolmeler[ad]))

    def test_kaynak_gold_kirletilmedi(self):
        """`bol` girdiyi kopyalar; `bolme` alanı gold kayıtlarına sızmamalı."""
        self.assertFalse(any("bolme" in k for k in self.hepsi))


class Sema(unittest.TestCase):
    def test_on_iki_alan(self):
        self.assertEqual(len(ALANLAR), 12)

    def test_alan_listesi_veriyle_ortusuyor(self):
        """Şema tablosu elle yazıldı; veride başka bir alan belirirse kart eskir."""
        veride = set()
        for r in oku(str(ROUND1)) + oku(str(V2)):
            veride |= set((r.get("fields") or {}).keys())
            veride |= set(r.get("absent_fields") or [])
        self.assertEqual(veride, {ad for ad, _, _ in ALANLAR})

    def test_beklenen_kayit_sayilari(self):
        self.assertEqual(len(oku(str(ROUND1))), BEKLENEN["gold.round1"])
        self.assertEqual(len(oku(str(V2))), BEKLENEN["gold.v2"])


class KappaSabitleri(unittest.TestCase):
    """Kart κ'ları sabit taşır; sabitin kaynak raporda geçtiği burada çitlenir."""

    def test_kappa_raporda_geciyor(self):
        for tur, k in KAPPA.items():
            rapor = _ROOT / k["rapor"]
            self.assertTrue(rapor.is_file(), f"{tur}: {rapor} yok")
            metin = rapor.read_text(encoding="utf-8")
            nokta = k["deger"].replace(",", ".")
            self.assertIn(nokta, metin, f"{tur}: κ={k['deger']} raporda yok")

    def test_hakemlik_konumlari_farkli(self):
        """İki κ'nın asimetrisi kartın omurgası; sabitler de bunu yansıtmalı."""
        self.assertNotEqual(KAPPA["round0"]["hakemlik"], KAPPA["round1"]["hakemlik"])
        self.assertNotEqual(KAPPA["round0"]["olcut"], KAPPA["round1"]["olcut"])


# `absent` hücre sayısı 446 → 447 (19 Ağu 2026): HAKEM-03 turu
# `hayat-finans--…-gastroclub` kaydında `masraf_durumu`'nu `fields`'ten
# `absent_fields`'a taşıdı (üçüncü taraf avantaj programı üyeliği,
# ürünün masrafı değil — `_hakem-turu-03-masraf-durumu.md`). Halüsinasyon
# oranının PAYDASI bu küme olduğu için sayı pakette birinci sınıf bir
# veridir ve sabiti güncellemek, ölçümü izlemek demektir.
class Paket(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = Path(cls.tmp.name) / "paket"
        cls.ozet = paketle(str(ROUND1), str(V2), str(cls.out),
                           str(_ROOT / "data/gold/ANNOTATION_GUIDE.md"))
        cls.kart = (cls.out / "README.md").read_text(encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_beklenen_dosyalar(self):
        for ad in ("gold.round1.jsonl", "gold.v2.jsonl", "train.jsonl",
                   "val.jsonl", "test.jsonl", "README.md", "LISANS.md",
                   "ANNOTATION_GUIDE.md"):
            self.assertTrue((self.out / ad).is_file(), f"{ad} yok")

    def test_jsonl_satir_basina_bir_kayit(self):
        for ad, beklenen in (("gold.round1.jsonl", BEKLENEN["gold.round1"]),
                             ("gold.v2.jsonl", BEKLENEN["gold.v2"])):
            satirlar = (self.out / ad).read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(satirlar), beklenen, ad)
            for satir in satirlar:
                self.assertIsInstance(json.loads(satir), dict)

    def test_absent_bilgisi_jsonlda_duruyor(self):
        """Halüsinasyon oranının paydası; taşınmazsa dışarıdan yeniden üretilemez."""
        satirlar = (self.out / "gold.v2.jsonl").read_text(encoding="utf-8").splitlines()
        toplam = sum(len(json.loads(s).get("absent_fields") or []) for s in satirlar)
        # 447: hakem turu 02'de iki kayda `hedef_kitle` absent kararı eklendi
        # (2026-08-19, data/gold/review/_hakem-turu-02-hedef-kitle.md).
        self.assertEqual(toplam, 447)

    def test_provenance_alanlari_duruyor(self):
        kayit = json.loads(
            (self.out / "gold.round1.jsonl").read_text(encoding="utf-8").splitlines()[0])
        for alan in ("id", "source_url", "content_hash", "text"):
            self.assertTrue(kayit.get(alan), alan)

    def test_ham_html_yok(self):
        """`app/.gitignore` gerekçesi: ham HTML yeniden dağıtılmaz."""
        for yol in self.out.rglob("*"):
            if yol.is_file():
                self.assertNotIn(yol.suffix, {".html", ".htm"}, str(yol))

    def test_paket_sizintisiz(self):
        self.assertEqual(self.ozet["ihlaller"], [])

    def test_kart_dursutluk_uyarilarini_tasiyor(self):
        """Kartın tek farklılaştırıcısı bu uyarılar; biri düşerse kart yalan söyler."""
        for parca in (
            "İNSAN HAKEMLİĞİ YAPILMADI",
            "MAKİNE",
            "makine kör hakem",
            "adjudicated: true",
            "simetrik değildir",
            "KIYASLANAMAZ",
            "SEÇİM ETKİSİDİR",
            "Fleiss",
            "Cohen",
            "0,302",
            "0,274",
            "Söylenemez",
            "tahsis_ucreti",
            "protokol v2",
        ):
            self.assertIn(parca, self.kart, f"kartta eksik: {parca}")

    def test_kart_iki_turu_ayirarak_veriyor(self):
        """Tek bir κ vermek en kolay yalandır; ikisi de ve konumlarıyla olmalı."""
        self.assertIn("SONRASI", self.kart)
        self.assertIn("ÖNCESİ", self.kart)

    def test_kart_kiyas_sayilari_gercek(self):
        # `absent` paydası 60 -> 61: HAKEM-04 turu (2026-08-20) round1'de
        # `…-2000-tlye-varan-parafpara` kaydının `odul_miktari`nı
        # `absent_fields`e taşıdı (değer `alisveris_puani`na geçti).
        # Gerekçe: data/gold/review/_hakem-turu-04-gold-kilavuz-celiskisi.md
        #
        # 61 -> 74: HAKEM-05 turu (2026-08-21, ANOTATÖR ONAYLI) round1'de
        # `finansman_tutari`nın **13** hücresini `absent_fields`e taşıdı.
        # Taşınanların hiçbiri finansman tutarı DEĞİLDİ: temassız ödeme
        # limiti, katılma hesabı açılış limiti, vade kademesi eşiği, örnek
        # ödeme planının "ödenecek toplam tutar"ı, ve bir vakada sayfa
        # altındaki "Diğer Kampanyalar" kutusundan sızmış BAŞKA kampanyanın
        # ödülü. Gerekçe ve 23 vakanın tamamı:
        # data/gold/review/_hakem-turu-05-finansman-tutari-round1.md
        #
        # Bu testin işi sayıyı DONDURMAK değil, sayı değiştiğinde bir
        # insanın SEBEBİNİ yazmaya zorlamak. İki kez işe yaradı.
        for parca in ("| **40** | **3** |", "| **447** | **74** |"):
            self.assertIn(parca, self.kart, f"kıyas tablosu sayısı yanlış: {parca}")

    def test_kart_bolme_sayilari_gercek(self):
        for ad in BOLME_ADLARI:
            n = len((self.out / f"{ad}.jsonl").read_text(encoding="utf-8").splitlines())
            self.assertIn(f"| `{ad}.jsonl` | {n} |", self.kart, ad)

    def test_kart_sizinti_denetimini_raporluyor(self):
        self.assertIn("**0 ihlal**", self.kart)

    def test_kart_tablolari_bozuk_degil(self):
        """Hücre içindeki kaçışsız `|` tabloyu böler — ölçüldü: `float | {min,max}`.

        HF dataset card'ı markdown olarak render edilir; bozuk bir şema
        tablosu kartın en çok okunan bölümünü okunmaz hâle getirir.
        """
        satirlar = self.kart.splitlines()
        beklenen = None   # yürürlükteki tablonun sütun sayısı
        denetlenen = 0
        for i, satir in enumerate(satirlar):
            if not satir.startswith("|"):
                beklenen = None          # tablo bitti
                continue
            boru = satir.count("|") - satir.count(r"\|")
            if set(satir) <= set("|-: "):
                beklenen = boru          # ayraç satırı sütun sayısını çiviler
                continue
            if beklenen is None:
                continue                 # başlık satırı; ayraç henüz görülmedi
            denetlenen += 1
            self.assertEqual(
                boru, beklenen,
                f"{i + 1}. satırda sütun sayısı tablo başlığıyla uyuşmuyor "
                f"({boru} ≠ {beklenen}) — hücrede kaçışsız `|` olabilir:\n{satir}")
        # Testin boşa dönmediğini çitle: kartta gerçekten tablo var.
        self.assertGreater(denetlenen, 40, "tablo satırı denetlenmedi")

    def test_yuzdeler_turkce_ondalik(self):
        """Belgenin geri kalanı `0,302` diyorsa bölme oranı da `%69,8` demeli."""
        import re
        self.assertFalse(re.search(r"%\d+\.\d", self.kart),
                         "kartta nokta ondalıklı yüzde var")

    def test_lisans_kokeni_yaziyor(self):
        lisans = (self.out / "LISANS.md").read_text(encoding="utf-8")
        for parca in ("Apache License\n2.0", "Apache License 2.0"):
            if parca in lisans:
                break
        else:
            self.fail("LISANS.md Apache-2.0 demiyor")
        for parca in ("telif hakkı **ilgili kurumlara aittir**",
                      "Ham HTML bilinçli olarak dışarıda",
                      "robots.txt", "kişisel veri"):
            self.assertIn(parca, lisans, f"LISANS.md'de eksik: {parca}")

    def test_sir_sizmiyor(self):
        """CLAUDE.md §19 — pakette anahtar/token görünmemeli."""
        for ad in ("README.md", "LISANS.md"):
            metin = (self.out / ad).read_text(encoding="utf-8")
            for kalip in ("hf_", "HF_TOKEN=", "sk-", "Bearer "):
                self.assertNotIn(kalip, metin, f"{ad}: {kalip}")


class Yukleyici(unittest.TestCase):
    """Yükleme betiği: token sızdırmamalı, varsayılanı kuru koşu olmalı."""

    def test_token_ekrana_basilmiyor(self):
        from scripts import veri_seti_yukle as y
        eski = __import__("os").environ.get(y.TOKEN_DEGISKENI)
        __import__("os").environ[y.TOKEN_DEGISKENI] = "hf_cokgizlibirdeger123"
        try:
            var, durum = y.token_durumu()
            self.assertTrue(var)
            self.assertNotIn("hf_cokgizlibirdeger123", durum)
            self.assertNotIn("cokgizli", durum)
        finally:
            if eski is None:
                __import__("os").environ.pop(y.TOKEN_DEGISKENI, None)
            else:
                __import__("os").environ[y.TOKEN_DEGISKENI] = eski

    def test_token_bayragi_yok(self):
        """Argüman olarak verilen token `ps` çıktısına ve kabuk geçmişine düşer."""
        from scripts import veri_seti_yukle as y
        self.assertNotIn("--token", Path(y.__file__).read_text(encoding="utf-8")
                         .split('"""', 2)[2])

    def test_kuru_kosu_varsayilan(self):
        from scripts import veri_seti_yukle as y
        ap_kaynak = Path(y.__file__).read_text(encoding="utf-8")
        self.assertIn("--gercekten-yukle", ap_kaynak)
        self.assertIn('default=True', ap_kaynak)

    def test_eksik_dosya_kapiyi_kapatir(self):
        from scripts import veri_seti_yukle as y
        self.assertEqual(y.eksikler([{"ad": "README.md"}]),
                         [a for a in y.ZORUNLU if a != "README.md"])

    def test_eksik_paket_mesaji_kurulum_komutunu_veriyor(self):
        """Türkçe, net ve kopyalanabilir olmalı — üstelik DOĞRU pip'i göstermeli."""
        from scripts import veri_seti_yukle as y
        self.assertIn("kurulu değil", y.KURULUM_MESAJI)
        self.assertIn("pip install huggingface_hub", y.KURULUM_MESAJI)
        self.assertIn("requirements.txt", y.KURULUM_MESAJI)

    @dosya_gerekir("requirements.txt")
    def test_huggingface_hub_requirements_disinda(self):
        """Teslim edilen sistem bu paketi kullanmaz; listeye girmesi yanlış iddia olur."""
        for ad in ("requirements.txt", "requirements-api.txt"):
            metin = (_ROOT / ad).read_text(encoding="utf-8")
            for satir in metin.splitlines():
                temiz = satir.split("#")[0].strip()
                self.assertNotIn("huggingface_hub", temiz.replace("-", "_"), ad)

    def test_envanter_boyut_ve_sha256_veriyor(self):
        """Betik ne yükleyeceğini önce LİSTELER — liste eksiksiz olmalı."""
        from scripts import veri_seti_yukle as y
        with tempfile.TemporaryDirectory() as tmp:
            kok = Path(tmp)
            (kok / "README.md").write_text("merhaba", encoding="utf-8")
            (kok / ".gizli").write_text("x", encoding="utf-8")
            dosyalar = y.envanter(tmp)
        self.assertEqual([d["ad"] for d in dosyalar], ["README.md"])  # gizli dosya elendi
        self.assertEqual(dosyalar[0]["bayt"], len("merhaba".encode()))
        self.assertEqual(len(dosyalar[0]["sha256"]), 64)

    def test_envanter_huggingface_hub_gerektirmiyor(self):
        """Ana kullanım biçimi kuru koşu; paket kurulu olmasa da çalışmalı."""
        from scripts import veri_seti_yukle as y
        self.assertTrue(callable(y.hub_var))
        kaynak = Path(y.__file__).read_text(encoding="utf-8")
        # Modül tepesinde `import huggingface_hub` OLMAMALI.
        tepe = kaynak.split("def ", 1)[0]
        self.assertNotIn("import huggingface_hub", tepe)
        self.assertNotIn("from huggingface_hub", tepe)


if __name__ == "__main__":
    unittest.main()
