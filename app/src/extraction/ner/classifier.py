"""8-sınıf kampanya türü sınıflandırıcı.

İlgili: ../../../decisions/ner-fine-tune-yerine-kural-few-shot.md
        ../../../concepts/kampanya-turleri.md  ../../../concepts/metin-siniflandirma.md
        CLAUDE.md §4 (fine-tune YALNIZ bu sınıflandırma için)

İki yol:
- RuleHintClassifier: URL yolu + anahtar-kelime ipuçlu, sıfır bağımlılık,
  offline fallback.
- BerturkClassifier: fine-tune edilmiş BERTurk (transformers). Model yoksa
  otomatik olarak RuleHint'e düşülür.

## 2026-08-20 onarımı — ölçüm raporu: docs/rapor/campaign-type-onarimi.md

Eski `RuleHintClassifier` üç kusur taşıyordu ve üçü de ÖLÇÜLDÜ:

1. **Beraberlik kırıcı `Konut`u varsayılan galip yapıyordu.** Puan eşitliğinde
   `_ORDER` sırası karar veriyordu ve sıranın başı `Konut Finansmanı`ydı.
   1.657 sınıflanan belgenin %31,5'i beraberlikle karara bağlanıyordu;
   `Konut Finansmanı` etiketli 179 belgenin 114'ü (%64) beraberlikten geliyor
   ve yalnız 45'inin URL'sinde `konut` geçiyordu. ARTIK: eşitlikte `None`
   (CLAUDE.md §19 — bilgi yoksa `null`; uydurma tür yanlış tür kadar pahalı).
2. **URL yolu hiç kullanılmıyordu.** En güçlü kullanılmayan sinyal buydu:
   aynı ürünün uzun ve kısa iki kopyası farklı tür alıyordu, yani etiket
   ürüne değil sayfa çerçevesinin hacmine bağlıydı. ARTIK: URL yolu
   deterministik bir kova tablosundan geçirilir; eşleşme varsa metne
   BAKILMAZ, eşleşme yoksa metin kolu koşar. Kalıp
   `scripts/build_demo_db.py::belge_turu_ata`den alındı (URL + korpus yolu →
   deterministik, eşleşmezse `NULL`, tür uydurma yok).
3. **`kredi kartı` iki etikete birden oy veriyordu.** `Kart` ipucu
   "kredi kartı", `Finansman` ipucu "kredi" — aynı sözcük öbeği iki etiketi
   birden puanlıyor ve yapay bir beraberlik üretiyordu. Ölçülen dört belgede
   (`avvada-500-tl-indirim`, `business-plus-ile-akaryakitta-indirim`,
   `cok-kazananlar-kulubu`, `akaryakit-harcamalarinda-5e-varan-iade`) gold
   `Kart`tı ve sonuç beraberlikten `None` çıkıyordu. ARTIK: BİLEŞİK İPUÇLARI
   (`_BILESIK_IPUCLARI`) + KAPSAMA KURALI — daha uzun ve daha özgül bir öbeğin
   İÇİNE düşen başka-etiket eşleşmesi sayılmaz ("kredi kartı" bir karttır,
   finansman değil).

ÇÜRÜTÜLEN üç hipotez (ölçüldü, uygulanmadı — sayılar raporda):
  * puan anahtarını çeşit yerine FREKANS yapmak (round1 0,667 -> 0,526),
  * sınıflandırma girdisini gezinme şeridinden arındırmak (v2 0,615 -> 0,564),
  * negasyon/dışlama penceresi uygulamak (round1 0,754 -> 0,737; üstelik
    `synonyms.NEGATION_RE` gerekçe olarak gösterilen id 601 cümlesiyle
    HİÇ eşleşmiyor).
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional, Protocol

from ...preprocessing.clean import tr_fold_ascii
from ...schemas import CAMPAIGN_TYPES
from ..rules.synonyms import FOLDED_TYPE_HINTS, keyword_pattern

logger = logging.getLogger(__name__)


class Classifier(Protocol):
    def classify(self, text: str,
                 source_url: Optional[str] = None) -> tuple[Optional[str], float]: ...


# --------------------------------------------------------------------------- #
# URL YOLU SİNYALİ
# --------------------------------------------------------------------------- #
#: Sıra ÖNEMLİ: özgül ürün kovaları genel kovalardan (`Kart`, `Finansman`)
#: önce gelir; `Alışveriş Puanı` `Kart`tan önce gelir çünkü "parafpara" bir
#: puan programıdır ve "paraf" kart markasını gölgelemesi gerekir.
#:
#: Kova sözcükleri korpusun GERÇEK URL yollarından çıkarıldı, tahminle değil.
#: Kasıtlı olarak DIŞARIDA bırakılanlar ve gerekçeleri:
#:   * `arac` tek başına YOK — `hesaplama-araclari` ve `elektrikli-arac-sarj`
#:     yollarını taşıt sanıyordu; yalnız `arac-finansman` bileşiği alındı.
#:   * `musteri-ol` YOK — ölçüldü, +1 doğru / -1 yanlış (net sıfır).
#:   * `iade` YOK — gold "5'e varan iade"yi `Kart`, "3 nakit iade"yi
#:     `Alışveriş Puanı` etiketliyor; ayırt etmiyor.
#:   * `bankkart` YOK — tek örnekten kural çıkarmak aşırı uyumdur.
_URL_KOVALARI: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("Konut Finansmanı", ("konut", "mortgage", "kentsel")),
    ("Taşıt Finansmanı", ("tasit", "togg", "motosiklet", "vavacars",
                          "arac-finansman", "oto-finansman", "deniz-tasit")),
    ("Alışveriş Puanı", ("parafpara", "puan", "mil", "chip")),
    ("İhtiyaç Finansmanı", ("ihtiyac",)),
    ("Kart", ("kart", "paraf")),
    ("Yatırım Ürünü", ("hesaplar", "hesabi", "katilma", "yatirim", "birikim",
                       "sukuk", "sertifikasi", "altin", "hisse", "sermaye",
                       "fonlar", "fon")),
    # Kılavuz §4.13/1: leasing / finansal kiralama -> `Finansman`.
    ("Finansman", ("leasing", "kiralama", "finansman", "kredi")),
)

#: URL yolu jetonlara ayrılırken kullanılan ayırıcı (tire, alt çizgi, nokta…).
_URL_AYIRICI_RE = re.compile(r"[^a-z0-9]+")
_URL_SEMA_RE = re.compile(r"^\w+://")

#: Jeton eşleşme eşikleri. Türkçe SONDAN EKLEMELİ bir dildir, bu yüzden uzun
#: sözcüklerde ön ek eşleşmesi doğru davranıştır (`konut` -> `konutunuz`).
#: ÖLÇÜLEN istisna: slug'lar bitişebiliyor (`kuveyt-turkandvavacars`), bu
#: yüzden >= 6 karakterli sözcükler alt-dize olarak da aranır. Kısa sözcükler
#: (`fon`, `mil`) TAM jeton eşleşmesi ister — aksi halde `fon` `fonksiyon`
#: içinde, `mil` `milyon` içinde eşleşirdi.
_URL_ALTDIZE_ASGARI = 6
_URL_ONEK_ASGARI = 4


def _url_jetonlari(source_url: Optional[str]) -> tuple[str, ...]:
    """URL'nin YOL kısmını katlanmış jetonlara ayırır (alan adı HARİÇ).

    Alan adı bilerek atılır: `kuveytturk.com.tr` her belgede geçer ve
    `turk`/`tr` gibi jetonlarla hiçbir türü ayırt etmez. Sorgu dizesi de
    atılır (`?IsArchived=true`).
    """
    if not source_url:
        return ()
    yol = _URL_SEMA_RE.sub("", tr_fold_ascii(source_url)).split("?", 1)[0]
    parca = yol.split("/", 1)
    return tuple(t for t in _URL_AYIRICI_RE.split(parca[1] if len(parca) > 1 else "")
                 if t)


def _url_eslesir(sozcuk: str, jetonlar: tuple[str, ...]) -> bool:
    """Kova sözcüğü URL jetonlarında geçiyor mu (bkz. eşik yorumları)."""
    if "-" in sozcuk:
        # Bileşik desen: ardışık jetonlarda sırayla aranır.
        parca = sozcuk.split("-")
        n = len(parca)
        return any(all(parca[k] in jetonlar[i + k] for k in range(n))
                   for i in range(len(jetonlar) - n + 1))
    if len(sozcuk) < _URL_ONEK_ASGARI:
        return sozcuk in jetonlar
    if len(sozcuk) >= _URL_ALTDIZE_ASGARI:
        return any(sozcuk in t for t in jetonlar)
    return any(t.startswith(sozcuk) for t in jetonlar)


def url_turu(source_url: Optional[str]) -> Optional[str]:
    """URL yolundan kampanya türü — deterministik, eşleşmezse `None`.

    `scripts/build_demo_db.py::belge_turu_ata` kalıbı: kaynağın YOLU bir
    taksonomi taşıyor; taşımıyorsa tür UYDURULMAZ.
    """
    jetonlar = _url_jetonlari(source_url)
    if not jetonlar:
        return None
    for etiket, sozcukler in _URL_KOVALARI:
        if any(_url_eslesir(s, jetonlar) for s in sozcukler):
            return etiket
    return None


# --------------------------------------------------------------------------- #
# METİN KOLU
# --------------------------------------------------------------------------- #
#: BİLEŞİK İPUÇLARI — `TYPE_HINTS`in tek sözcüklü ipuçlarının üstüne binen,
#: DAHA UZUN ve daha özgül ad öbekleri. İki işi birden yapar:
#:   1. sahibi etikete puan verir,
#:   2. daha uzun oldukları için, içlerine düşen BAŞKA etiketin eşleşmesini
#:      kapsama kuralıyla (bkz. `_metin_puanlari`) düşürür.
#:
#: Dilbilgisel gerekçe: Türkçe'de bileşik ad öbeğinin anlamı öbeğin TAMAMINA
#: aittir; "kredi kartı" bir karttır, "konut finansmanı" bir konut ürünüdür.
#: Genel baş sözcüğün (`kredi`, `finansman`) öbek içinde ayrıca genel sınıfa oy
#: vermesi ölçülmüş bir hataydı (modül başlığı, kusur 3).
#:
#: Desenler `\w*` ile biter çünkü Türkçe sondan eklemelidir ve `TYPE_HINTS`in
#: kısa (<= 4 karakter) ipuçları İKİ TARAFTAN sınırlı eşleşir — yani "kart"
#: ipucu "kartları"na uymaz. Ölçüldü: bu katman puanlı olduğunda round1
#: 0,789 -> 0,798 ve gold.v2 0,744 -> 0,769; çekimserlik 5 -> 2 ve uydurma
#: 16 -> 13 düşüyor. Puansız (yalnız gölgeleyen) sürüm de denendi ve daha
#: kötüydü; sayılar docs/rapor/campaign-type-onarimi.md içinde.
_BILESIK_IPUCLARI: dict[str, tuple[str, ...]] = {
    "Konut Finansmanı": (r"konut\s+(?:finansman|kredi)\w*", r"ev\s+kredi\w*"),
    "Taşıt Finansmanı": (
        r"(?:tasit|arac|otomobil|araba)\s+(?:finansman|kredi)\w*",),
    "İhtiyaç Finansmanı": (r"ihtiyac\s+(?:finansman|kredi)\w*",),
    "Kart": (r"(?:kredi|banka|debit)\s+kart\w*",),
    "Alışveriş Puanı": (r"alisveris\s+puan\w*",),
    "Yatırım Ürünü": (r"(?:katilim|yatirim)\s+fon\w*",
                      r"(?:katilma|altin|yatirim|birikim)\s+hesab\w*"),
}
_BILESIK_DERLI: dict[str, tuple[re.Pattern[str], ...]] = {
    etiket: tuple(re.compile(p) for p in desenler)
    for etiket, desenler in _BILESIK_IPUCLARI.items()
}


class RuleHintClassifier:
    """URL yolu + anahtar-kelime ipuçlarıyla sınıflandırma.

    Karar sırası (deterministik):
      1. URL yolu bir tür kovasıyla eşleşiyorsa O TÜR döner.
      2. Aksi halde metinde ETİKET BAŞINA KAÇ FARKLI ipucu geçtiği sayılır;
         gölgelenen eşleşmeler düşülür.
      3. Tek bir en yüksek etiket varsa o döner.
      4. BERABERLİK ya da hiç ipucu yoksa `(None, 0.0)` — uydurma yok.
    """

    #: Etiketler üzerinde DETERMİNİSTİK gezinme sırası. Eskiden bu sıra aynı
    #: zamanda beraberlik kırıcıydı ve `Konut Finansmanı`nı varsayılan galip
    #: yapıyordu; o yetki KALDIRILDI (modül başlığı, kusur 1). Sıra artık
    #: yalnız çıktının tekrar-üretilebilirliği içindir.
    _ORDER = [
        "Konut Finansmanı", "Taşıt Finansmanı", "İhtiyaç Finansmanı",
        "Alışveriş Puanı", "Yeni Müşteri", "Yatırım Ürünü", "Kart", "Finansman",
    ]

    #: URL'den gelen kararın güveni. Metin kolundan (0,5–0,9) AYRI bir sabit:
    #: karar deterministik bir yol eşleşmesine dayanıyor, ipucu yoğunluğuna
    #: değil, dolayısıyla yoğunluk formülü burada anlamsız olurdu.
    _URL_CONF = 0.8

    def classify(self, text: str, source_url: Optional[str] = None
                 ) -> tuple[Optional[str], float]:
        """Kampanya türü + kaba güven. Karar veremezse `(None, 0.0)`."""
        u = url_turu(source_url)
        if u is not None:
            return u, self._URL_CONF

        scores = self._metin_puanlari(text)
        if not scores:
            return None, 0.0
        en = max(scores.values())
        kazananlar = [l for l in self._ORDER if scores.get(l) == en]
        if len(kazananlar) != 1:
            # BERABERLİK -> çekimser. Korpusta 125 belge zaten `NULL`; meşru
            # bir çıktıdır (kılavuz §4.13/1: "`null` bir hatanın değil bir
            # kararın adıdır").
            return None, 0.0
        # güven: eşleşme yoğunluğuna göre kaba [0.5, 0.9]
        return kazananlar[0], min(0.9, 0.5 + 0.1 * en)

    def _metin_puanlari(self, text: str) -> dict[str, int]:
        """Etiket -> metinde geçen FARKLI ipucu sayısı (gölgeler düşülmüş).

        Frekans DEĞİL çeşit sayılır. Frekans denendi ve ÖLÇÜLDÜ: round1
        doğruluğu 0,667'den 0,526'ya düştü — çünkü çerçeve metninde onlarca
        kez tekrarlanan genel sözcükler ("kart", "finansman") özgül tek bir
        ipucunu (bir kez geçen "parafpara") eziyor.
        """
        # TR-doğru katlama: ALL-CAPS başlıklar ve diakritiksiz yazımlar da
        # eşleşir. Düz .lower() burada 'TAŞIT' -> 'taşit' üretip eşleşmeyi
        # kaçırıyordu.
        low = tr_fold_ascii(text)

        # (bas, son, etiket) — gölgeleme hesabına giren TÜM aralıklar.
        araliklar: list[tuple[int, int, str]] = []
        # (bas, son, etiket, ipucu) — yalnız PUAN VEREN eşleşmeler.
        puanli: list[tuple[int, int, str, str]] = []
        for label in self._ORDER:
            # SÖZCÜK SINIRLI eşleşme (bkz. synonyms.keyword_pattern). Düz
            # alt-dize araması 'ev' anahtarını 'devam'/'seviye' içinde
            # buluyordu ve gerçek korpusun %48'ini sahte Konut Finansmanı
            # yapıyordu.
            for kw in sorted(FOLDED_TYPE_HINTS.get(label, frozenset())):
                for m in re.finditer(keyword_pattern(kw), low):
                    araliklar.append((m.start(), m.end(), label))
                    puanli.append((m.start(), m.end(), label, kw))
        for label, desenler in _BILESIK_DERLI.items():
            for desen in desenler:
                for m in desen.finditer(low):
                    araliklar.append((m.start(), m.end(), label))
                    puanli.append((m.start(), m.end(), label, desen.pattern))

        scores: dict[str, set[str]] = {}
        for bas, son, label, kw in puanli:
            if any(a <= bas and son <= b and (b - a) > (son - bas) and l2 != label
                   for a, b, l2 in araliklar):
                continue  # daha uzun ve BAŞKA etikete ait bir öbeğin içinde
            scores.setdefault(label, set()).add(kw)
        return {k: len(v) for k, v in scores.items()}


class BerturkClassifier:
    """Fine-tune BERTurk yolu. Model yüklenemezse RuleHint'e düşer.

    model_dir: kaydedilmiş HuggingFace modeli (offline, **MIT** BERTurk).

    Lisans doğrulandı (2026-08-07): `dbmdz/bert-base-turkish-cased`
    `cardData.license = "mit"`, `base_model` beyanı YOK — zincirin kökü,
    yani "türev kökünden serbest olamaz" tuzağı oluşmuyor. Kaynak:
    https://huggingface.co/api/models/dbmdz/bert-base-turkish-cased
    Bu satır eskiden "Apache-2.0" diyordu; ikisi de izinli listede
    (CLAUDE.md §7) ama yanlış lisans beyanı uyumluluk iddiasını çürütür.
    """

    def __init__(self, model_dir: Optional[str] = None):
        self._pipe = None
        self._fallback = RuleHintClassifier()
        self._calisma_zamani_hatasi_loglandi = False

        # Geri düşüş (fallback) DAVRANIŞI kasıtlı: çevrimdışı demoda ağırlık
        # yoksa sistem çökmemeli, kural katmanıyla çalışmalı. Ama SESSİZ geri
        # düşüş kusurluydu: model beklerken kural koşuyorsa çıktıyı okuyan
        # kişi hangi kolun ölçüldüğünü bilemez ve "BERTurk sonucu" sanılan
        # sayı aslında kural sonucudur. Davranış aynı kaldı, görünürlük eklendi.
        md = model_dir or os.environ.get("BERTURK_MODEL_DIR")
        if not md:
            logger.info(
                "BERTURK_MODEL_DIR tanımsız -> RuleHintClassifier "
                "(kural-ipucu, kasıtlı offline varsayılan)")
            return
        if not os.path.isdir(md):
            logger.warning(
                "BERTurk model dizini YOK: %r -> RuleHintClassifier'a "
                "düşülüyor. Model bekleniyorsa ölçülen kol KURAL'dır.", md)
            return
        try:
            from transformers import pipeline  # type: ignore
            # `local_files_only=True` KOŞULSUZ: `md` yukarıda `os.path.isdir`
            # ile doğrulanmış YEREL bir dizin, dolayısıyla hub'a çıkmak için
            # hiçbir meşru sebep yok. Bayrak olmadan `transformers`, eksik bir
            # yardımcı dosya için (tokenizer, config) **sessizce ağa çıkar** —
            # çevrimdışı makinede bu, yükleme anında değil ÇALIŞMA ANINDA
            # patlar. `src/rag/embedding.py:102` aynı korumayı zaten
            # uyguluyordu; burada atlanmıştı.
            #
            # Konteynerde `HF_HUB_OFFLINE=1` + `TRANSFORMERS_OFFLINE=1` bunu
            # ayrıca zorluyor (`Dockerfile.api`), ama kod konteyner dışında da
            # koşuyor ve doğruluğu ortam değişkenine bağlı olmamalı.
            self._pipe = pipeline("text-classification", model=md, top_k=1,
                                  model_kwargs={"local_files_only": True})
            logger.info("BERTurk yüklendi: %s", md)
        except Exception as exc:
            # Geniş yakalama bilinçli: eksik `transformers`, bozuk ağırlık,
            # uyumsuz sürüm — hepsinde kural katmanı çalışmaya devam etmeli.
            self._pipe = None
            logger.warning(
                "BERTurk yüklenemedi (%s: %s) -> RuleHintClassifier'a "
                "düşülüyor. Dizin: %r", type(exc).__name__, exc, md)

    @property
    def available(self) -> bool:
        return self._pipe is not None

    def classify(self, text: str, source_url: Optional[str] = None
                 ) -> tuple[Optional[str], float]:
        # `source_url` modele GİRMEZ (BERTurk yalnız metinle eğitildi) ama
        # geri düşüş kolu onu KULLANIR; imzadan düşürmek kural kolunu en
        # güçlü sinyalinden sessizce mahrum bırakırdı.
        if self._pipe is None:
            return self._fallback.classify(text, source_url)
        try:
            res = self._pipe(text[:512])
            top = res[0][0] if isinstance(res[0], list) else res[0]
            label = top["label"]
            # model etiketi geçerli türe eşlenir; değilse fallback
            if label not in CAMPAIGN_TYPES:
                logger.warning(
                    "BERTurk taksonomi dışı etiket üretti: %r -> "
                    "RuleHintClassifier. Model `id2label` haritası "
                    "CAMPAIGN_TYPES ile uyumlu mu?", label)
                return self._fallback.classify(text, source_url)
            return label, float(top["score"])
        except Exception as exc:
            # Belge başına log basmamak için yalnız İLK hata uyarı seviyesinde.
            if not self._calisma_zamani_hatasi_loglandi:
                self._calisma_zamani_hatasi_loglandi = True
                logger.warning(
                    "BERTurk çıkarımı başarısız (%s: %s) -> "
                    "RuleHintClassifier. Sonraki hatalar debug seviyesinde.",
                    type(exc).__name__, exc)
            else:
                logger.debug("BERTurk çıkarımı başarısız (%s): %s",
                             type(exc).__name__, exc)
            return self._fallback.classify(text, source_url)


def default_classifier() -> Classifier:
    """Ortama göre sınıflandırıcı (model varsa BERTurk, yoksa kural-ipucu)."""
    clf = BerturkClassifier()
    return clf if clf.available else RuleHintClassifier()
