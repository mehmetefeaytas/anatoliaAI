"""Colab duman testi — LLM ilk kez gerçek Türkçe kampanya metninde çalışıyor mu?

Kullanım (tek Colab hücresi, kopyala-yapıştır hatası olmaz):

    !wget -qO smoke.py https://raw.githubusercontent.com/mehmetefeaytas/anatoliaAI/main/colab/00_smoke_test.py
    %run smoke.py

Önkoşul: Ollama ayakta ve model çekilmiş (bkz. colab/01_setup.py).

Neyi ölçüyor:
  1) "%1,89 ile 120 aya kadar" -> 1.89 (ARALIK DEĞİL; "120 ay" bir vadedir)
  2) gerçek aralık + fiil negasyonu ("alınmaz") + hedef kitle
  3) çelişki sinyali: masrafsız iddiası + pozitif tahsis ücreti
  4) nötr metin -> HEPSİ null   <-- en kritik: halüsinasyon testi

İlgili: app/CLAUDE.md §6 (zor anlama vakaları), §21 (halüsinasyon yasağı)
        şartname §5.5 (terminoloji), §5.6 (normalizasyon denklikleri)
"""

import json
import os
import urllib.request

MODEL = os.environ.get("SMOKE_MODEL", "qwen3:32b")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

# --------------------------------------------------------------------------- #
# Şema — alan tipli, her anahtar zorunlu
# --------------------------------------------------------------------------- #
SEGMENTS = [
    "yeni_musteri",
    "mevcut_musteri",
    "maas_musterisi",
    "belirli_segment",
]

NUM_OR_RANGE = {
    "anyOf": [
        {"type": "number"},
        {
            "type": "object",
            "properties": {
                "min": {"type": "number"},
                "max": {"type": "number"},
            },
            "required": ["min", "max"],
        },
        {"type": "null"},
    ]
}

FEE_STATUS = {
    "anyOf": [
        {
            "type": "object",
            "properties": {
                "has_fee": {"type": "boolean"},
                "amount": {"anyOf": [{"type": "number"}, {"type": "null"}]},
            },
            "required": ["has_fee"],
        },
        {"type": "null"},
    ]
}

AUDIENCE = {
    "anyOf": [
        {"type": "array", "items": {"type": "string", "enum": SEGMENTS}},
        {"type": "null"},
    ]
}

FIELDS = [
    "kar_payi_orani",
    "vade_ay",
    "tahsis_ucreti",
    "masraf_durumu",
    "hedef_kitle",
]

SCHEMA = {
    "type": "object",
    "properties": {
        "kar_payi_orani": NUM_OR_RANGE,
        "vade_ay": {"anyOf": [{"type": "integer"}, {"type": "null"}]},
        "tahsis_ucreti": {"anyOf": [{"type": "number"}, {"type": "null"}]},
        "masraf_durumu": FEE_STATUS,
        "hedef_kitle": AUDIENCE,
    },
    # Modeli HER anahtarı üretmeye zorla: olmayan alan açıkça null olsun.
    # "Atlandı" ile "yok" karışırsa halüsinasyon oranı ölçülemez.
    "required": FIELDS,
}

# --------------------------------------------------------------------------- #
# Sistem promptu — §5.5 terminolojisi açık tanımlarla
# --------------------------------------------------------------------------- #
SYSTEM = """Sen katılım bankacılığı (faizsiz finans) metinlerinden bilgi çıkaran bir asistansın.

TERMİNOLOJİ (doğru yorumlaman zorunlu):
- kâr payı oranı: FAİZ DEĞİLDİR. Murabahada önceden ilan edilen kâr marjıdır.
- finansman: kredi yerine kullanılır (konut/taşıt/ihtiyaç finansmanı).
- katılım fonu: mevduat yerine kullanılır.
- masrafsız finansman: masraf SIFIR demektir, "bilgi yok" DEĞİL.
- tahsis ücreti: finansman tahsisinde alınan tek seferlik ücret.

KURALLAR:
- Metinde AÇIKÇA yazmayan hiçbir değeri UYDURMA. Yoksa null yaz.
- "alınmaz / talep edilmez / yoktur" negasyondur -> ücret 0, null değil.
- Aylık ve yıllık oranları karıştırma.
- TR sayı biçimi: 1.500,00 = bin beş yüz. Nokta binlik, virgül ondalıktır.
- "X aya kadar vade" bir VADEDİR; oran aralığının üst sınırı DEĞİLDİR."""

TESTS = [
    (
        "aralik-tuzagi",
        "Konut finansmanında kâr payı oranı %1,89 ile 120 aya kadar vade. "
        "Tahsis ücreti 1.500,00 TL. "
        "Kampanya 31.12.2026 tarihine kadar geçerlidir.",
    ),
    (
        "gercek-aralik+negasyon",
        "YENİ MÜŞTERİLERE ÖZEL. Taşıt finansmanı kâr payı oranı "
        "%1,99 - %2,49 arasında, 48 ay vade. Yıllık kart ücreti alınmaz.",
    ),
    (
        "celiski",
        "Bu kampanya masrafsızdır. "
        "Ancak tahsis ücreti 500 TL olarak tahsil edilir.",
    ),
    (
        "halusinasyon-testi",
        "Şubelerimiz hafta içi 09:00-17:00 arası hizmet vermektedir.",
    ),
]


def sor(metin: str) -> dict:
    """Tek bir metni modele sorar, şema-geçerli JSON döndürür."""
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": metin},
        ],
        "format": SCHEMA,
        "stream": False,
        "options": {
            "temperature": 0,   # deterministik -> eval tekrar-üretilebilir
            "seed": 42,
            # KRİTİK: Ollama varsayılanı 2048 token. Prompt + şema + metin
            # bunu aşar ve Ollama SESSİZCE kırpar -> bozuk JSON üretir,
            # biz de modeli suçlarız.
            "num_ctx": 8192,
            "num_predict": 512,
        },
    }
    req = urllib.request.Request(
        f"{OLLAMA_URL}/api/chat",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return json.loads(body["message"]["content"])


def main() -> None:
    print(f"model = {MODEL}")
    print(f"url   = {OLLAMA_URL}\n")

    sonuclar = {}
    for etiket, metin in TESTS:
        print(f"--- [{etiket}] {metin[:64]}...")
        try:
            out = sor(metin)
            sonuclar[etiket] = out
            print(json.dumps(out, ensure_ascii=False, indent=2))
        except Exception as exc:
            print(f"HATA: {type(exc).__name__}: {exc}")
        print()

    # Otomatik değerlendirme — elle bakmaya gerek kalmasın
    print("=" * 62)
    print("OTOMATIK KONTROL")
    print("=" * 62)

    a = sonuclar.get("aralik-tuzagi") or {}
    ok1 = a.get("kar_payi_orani") == 1.89
    print(f"[{'GECTI' if ok1 else 'KALDI'}] 1) oran 1.89, aralik degil "
          f"-> {a.get('kar_payi_orani')!r}")

    b = sonuclar.get("gercek-aralik+negasyon") or {}
    kp = b.get("kar_payi_orani")
    ok2 = isinstance(kp, dict) and kp.get("min") == 1.99
    ok2b = (b.get("masraf_durumu") or {}).get("has_fee") is False
    print(f"[{'GECTI' if ok2 else 'KALDI'}] 2a) gercek aralik -> {kp!r}")
    print(f"[{'GECTI' if ok2b else 'KALDI'}] 2b) fiil negasyonu "
          f"-> {b.get('masraf_durumu')!r}")

    c = sonuclar.get("celiski") or {}
    ok3 = (
        (c.get("masraf_durumu") or {}).get("has_fee") is False
        and (c.get("tahsis_ucreti") or 0) > 0
    )
    print(f"[{'GECTI' if ok3 else 'KALDI'}] 3) celiski sinyali -> "
          f"masraf={c.get('masraf_durumu')!r} "
          f"tahsis={c.get('tahsis_ucreti')!r}")

    d = sonuclar.get("halusinasyon-testi") or {}
    uydurma = [k for k in FIELDS if d.get(k) is not None]
    ok4 = not uydurma
    print(f"[{'GECTI' if ok4 else 'KALDI'}] 4) HALUSINASYON: notr metinde "
          f"uydurulan alan -> {uydurma or 'YOK'}")

    print()
    if ok4:
        print("EN KRITIK TEST GECTI: model bilmedigini biliyor.")
    else:
        print("!!! DIKKAT: model notr metinde deger UYDURDU.")
        print("    250 belgeye gecmeden once prompt sikilmalidir.")


if __name__ == "__main__":
    main()
