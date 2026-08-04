"""Etiketleyici ve denetleyici prompt şablonları.

İlgili: ./contract.py, ./consensus.py

## Neden prompt'lar repoda

Veri setinin kökeni savunulabilir olmalı. "Bir LLM etiketledi" bir yöntem
açıklaması değildir; şartname §6 dokümantasyonda *"Kullanılan veri seti ve
açıklaması"* ile *"Model veya kural yapısının açıklaması"* istiyor. Prompt
metni burada durursa etiketleme **yeniden üretilebilir** olur — hangi model
koşarsa koşsun (harici asistan bugün, yerel Qwen/Trendyol yarın).

## Tasarımdaki iki bilinçli kısıt

1. **Alıntı zorunlu.** Model etiketi gerekçelendirmek için belgeden birebir
   bir parça vermek zorunda. `contract.evidence_is_verbatim` bunu mekanik
   olarak doğrular; uydurma alıntı kaydı düşürür.
2. **Denetleyici önce kendi etiketini söyler.** Prompt sırası bunu zorlar.
   Aksi hâlde denetleyici, önerilen etiketi görüp onaylama eğilimine girer
   (lastik damga) ve iki bağımsız oy aslında tek oya iner.

Ayrıca ikisi de "emin değilsen null" diyor — CLAUDE.md §19 halüsinasyon
yasağının etiketleme tarafındaki karşılığı. Boş etiket bir kayıptır; yanlış
etiket eğitim setine giren bir zehirdir.

## Kırpma penceresi neden 6000 değil (2026-08-04 ölçümü)

İlk sürüm metni 6000 karaktere kırpıyordu; gerekçesi "kampanya sayfalarının
ana konusu başta geçer, kuyrukta çerez/KVKK gürültüsü birikir" idi. Bu varsayım
KAMPANYA sayfaları için doğru, **ÜRÜN sayfaları için yanlış**: ürün sayfalarında
başta dev bir gezinme (navigation) bloğu duruyor, gövde ortada.

`data/raw-classic/*/products/` altındaki 106 ürün belgesi üzerinde ölçüldü —
sınıfı gerekçelendiren alıntının belge içindeki konumu:

    Yapı Kredi (10 belge)  : ~17.500-18.400 karakter
    Garanti BBVA (10 belge): ~6.000-6.200 karakter
    kalan 76 belge         : < 6.000 karakter

Yani etiketlenebilir 96 belgenin **20'sinde (%21)** gövde 6000 penceresinin
tamamen dışındaydı; o pencereyle etiketleyici de denetleyici de yalnız menü
metni görüyordu. Daha kötüsü sessiz bir başarısızlıktı: `consensus.decide`
kanıtı TAM metinde arıyor, denetleyici ise kırpılmış metinde — alıntı mekanik
kapıdan geçip denetleyici tarafından "belgede yok" diye reddediliyordu
(`R_EVIDENCE_WEAK` → kuyruk). Kayıp tam olarak hasadın hedefi olan
Konut/Taşıt belgelerinde yoğunlaşıyordu.

Pencere ölçülen en uzak konuma (18.321) pay bırakılarak 24000'e çıkarıldı.
Kırpma tamamen kaldırılmadı: `data/raw-classic` içinde 70 KB'lik belgeler var
ve sınırsız prompt, kırpma bilgisinin (`note`) anlamını da yok eder.
"""

from __future__ import annotations

from ...schemas import CAMPAIGN_TYPES

# Bkz. modül docstring'i "Kırpma penceresi neden 6000 değil". Ölçüm:
# ürün sayfalarında gerekçe alıntısı en uzak 18.321. karakterde çıktı.
MAX_PROMPT_CHARS = 24000

_TYPES = "\n".join(f"- {t}" for t in CAMPAIGN_TYPES)

# Klasik (katılım olmayan) banka metinleri için terminoloji uyarısı.
# Kapsam dışı bankalar "faiz", "kredi", "mevduat" kullanıyor; hedef taksonomi
# katılım bankacılığı sözlüğüyle tanımlı. Eşleme ÜRÜN TÜRÜNE göre yapılır,
# sözcüğe göre değil — yoksa "konut kredisi" hiçbir sınıfa düşmez.
_TERMINOLOJI = """\
Metin klasik (katılım olmayan) bir bankaya ait olabilir. O durumda ürün
sözlüğü farklıdır ve eşleme ÜRÜN TÜRÜNE göre yapılır, sözcüğe göre değil:
  faiz oranı        -> kâr payı oranının karşılığı (aynı ürün rolü)
  kredi             -> finansman
  konut kredisi     -> Konut Finansmanı
  taşıt/araç kredisi-> Taşıt Finansmanı
  ihtiyaç kredisi   -> İhtiyaç Finansmanı
  mevduat / vadeli hesap / altın hesabı -> Yatırım Ürünü
  leasing (icara), işletme/ticari finansman -> Finansman
UYARI: sınıf, metnin KAMPANYA/ÜRÜN türüdür. Sayfada birden çok ürün varsa
ve hangisinin ana konu olduğu belirsizse label=null ver."""

LABELER_SYSTEM = f"""\
Türkçe banka kampanya metinlerini 8 sınıftan birine ayırıyorsun.

İzin verilen sınıflar (birebir bu yazımlar, başka hiçbir şey):
{_TYPES}

{_TERMINOLOJI}

Her belge için tam olarak şu JSON'u üret, başka hiçbir şey yazma:
{{"doc_id": "<verilen id>", "label": "<8 sınıftan biri ya da null>",
  "evidence": "<belgeden BİREBİR kopyalanmış, sınıfı gerekçelendiren alıntı>",
  "confidence": <0.0-1.0>}}

Kurallar:
1. `evidence` belgeden BİREBİR kopyalanacak. Özetleme, yeniden yazma,
   düzeltme yapma. En az 12 karakter olsun ve sınıfı gerçekten gerekçelendirsin.
   Uydurulmuş alıntı mekanik olarak yakalanır ve kayıt atılır.
2. Sınıf belirsizse, sayfada birden çok ürün ana konu ise, ya da metin bir
   ürün/kampanya sayfası değilse (çerez politikası, KVKK, iletişim, genel
   kurumsal sayfa): label=null, evidence="", confidence=0.0.
3. Emin olmadığın etiketi yazmak, boş bırakmaktan DAHA KÖTÜDÜR. Bu veri bir
   sınıflandırıcı eğitecek; yanlış etiket kalıcı hata öğretir."""

VERIFIER_SYSTEM = f"""\
Bir başka modelin ürettiği sınıf etiketini denetliyorsun.

İzin verilen sınıflar (birebir bu yazımlar):
{_TYPES}

{_TERMINOLOJI}

SIRA ÖNEMLİ. Şu adımları bu sırayla yap:
1. Önce belgeyi kendin oku ve KENDİ etiketini belirle. Bunu önerilen etiketten
   BAĞIMSIZ yap — önerilen etikete bakıp onaylama eğilimine girme.
2. Sonra önerilen alıntının belgede gerçekten geçtiğini ve önerilen etiketi
   gerçekten desteklediğini değerlendir.

Tam olarak şu JSON'u üret, başka hiçbir şey yazma:
{{"doc_id": "<verilen id>", "own_label": "<kendi etiketin ya da null>",
  "evidence_supports": true|false, "reason": "<tek cümle gerekçe>"}}

`evidence_supports` yalnızca şu iki koşul BİRLİKTE sağlanırsa true olur:
alıntı belgede birebir geçiyor VE önerilen etiketi gerekçelendiriyor.
Alıntı doğru ama etiketi desteklemiyorsa false ver.
Kendi etiketin önerilenden farklıysa bunu gizlemeye çalışma — ayrışma bilgidir
ve o belge insan hakemliğine gider."""


def labeler_user_prompt(doc_id: str, text: str,
                        max_chars: int = MAX_PROMPT_CHARS) -> str:
    """Etiketleyiciye gidecek kullanıcı mesajı.

    Metin kırpılır, ama pencere ürün sayfalarının gövde konumuna göre ölçülerek
    seçildi (bkz. modül docstring'i). Kırpma noktası `note` olarak belirtilir ki
    model eksik metinle çalıştığını bilsin.
    """
    body = text[:max_chars]
    kirpildi = " (metin kırpıldı)" if len(text) > max_chars else ""
    return f"doc_id: {doc_id}{kirpildi}\n\n--- BELGE ---\n{body}"


def verifier_user_prompt(doc_id: str, text: str, proposed_label: str,
                         evidence: str,
                         max_chars: int = MAX_PROMPT_CHARS) -> str:
    body = text[:max_chars]
    kirpildi = " (metin kırpıldı)" if len(text) > max_chars else ""
    return (
        f"doc_id: {doc_id}{kirpildi}\n\n"
        f"--- BELGE ---\n{body}\n\n"
        f"--- DENETLENECEK ÖNERİ ---\n"
        f"önerilen etiket: {proposed_label}\n"
        f"önerilen alıntı: {evidence}"
    )
