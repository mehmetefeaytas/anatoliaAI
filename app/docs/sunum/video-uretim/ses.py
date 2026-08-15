"""Türkçe seslendirme — cümle cümle, süreleri ölçülerek.

Her cümle AYRI dosya. Sebep: kullanıcı bu geçici sesi kendi sesiyle
değiştirecek; tek tek değiştirilebilsin ve kurgu bozulmasın.

Süreler ölçülüp `ses.json`a yazılıyor; video zaman çizgisi bu ölçülen
sürelere göre kuruluyor — tahmin edilen süreye göre değil.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
CIK = T / "ses"
CIK.mkdir(parents=True, exist_ok=True)

SES = "Yelda"
HIZ = 168          # kelime/dk — ürün lansmanı temposu, acele yok

# (numara, sahne, metin)
CUMLELER = [
    (1,  "acilis",  "Anatolia AI."),
    (2,  "acilis",  "Katılım bankacılığı kampanya metinlerinden, ölçülen ve kanıtlanan bilgi çıkarımı."),
    (3,  "problem", "Aynı bilgi, on bankada on farklı biçimde yazılıyor."),
    (4,  "problem", "İlk altı ay masrafsız. Yüzde bir doksan dokuz ile iki kırk dokuz arası. Yüz yirmi aya kadar vade."),
    (5,  "problem", "Hangisinin daha uygun olduğunu elle karşılaştırmak pratikte mümkün değil."),
    (6,  "pano",    "Anatolia AI on katılım bankasından bin yedi yüz seksen iki belgeyi topladı ve karşılaştırılabilir yapısal veriye dönüştürdü."),
    (7,  "cetvel",  "Karşılaştırılacak alanı seçiyoruz."),
    (8,  "cetvel",  "Sistem kâr payı oranına göre sıralıyor."),
    (9,  "cetvel",  "Ama iki kampanyayı sıralamayı reddediyor."),
    (10, "cetvel",  "Çünkü oranları koşullu. Doğrudan kıyaslanamazlar, ve sistem bunu uydurmak yerine söylüyor."),
    (11, "kanit",   "Peki bu değer nereden geldi?"),
    (12, "kanit",   "Kanıt defteri her alan için ham ifadeyi, güven skorunu ve üreten katmanı gösteriyor."),
    (13, "kanit",   "Her değer, kaynak belgede bir karakter aralığına bağlı. Bu bağ programatik olarak doğrulanıyor."),
    (14, "sohbet",  "Sohbet katmanı soruyu anlıyor ve cevabı kaynağıyla veriyor."),
    (15, "sohbet",  "Hangi yolu seçtiğini de cevabın yanında yazıyor."),
    (16, "celiski", "Bir banka masrafsız derken ücret tarifesinde tahsis ücreti alıyorsa, sistem bunu yakalıyor."),
    (17, "mimari",  "Arkada iki katman var. Kurallar birincil; dil modeli yalnızca kuralların boş bıraktığı yerleri dolduruyor."),
    (18, "mimari",  "Bilgi metinde yoksa hiçbir değer üretilmiyor."),
    (19, "olcum",   "Ve şu: yayımladığımız her sayı, onu üreten komutun çıktısıyla eşleşmek zorunda. Ayrışırsa yapı kırmızı yanıyor."),
    (20, "kapanis", "Tek bir parlak yüzde vermiyoruz. Çünkü bir alanı kaçırmak ile uydurmak aynı hata değil."),
]


def sure(yol: Path) -> float:
    cikti = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(yol)],
        capture_output=True, text=True, check=True).stdout.strip()
    return round(float(cikti), 3)


def main() -> None:
    kayit = []
    for no, sahne, metin in CUMLELER:
        aiff = CIK / f"S{no:02d}.aiff"
        wav = CIK / f"S{no:02d}.wav"
        subprocess.run(["say", "-v", SES, "-r", str(HIZ), "-o", str(aiff), metin],
                       check=True)
        # 48 kHz mono — ffmpeg birleştirmesinde yeniden örnekleme olmasın
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(aiff),
                        "-ar", "48000", "-ac", "1", str(wav)], check=True)
        aiff.unlink()
        s = sure(wav)
        kayit.append({"no": no, "sahne": sahne, "sure": s, "metin": metin,
                      "dosya": wav.name})
        print(f"S{no:02d} {sahne:8s} {s:5.2f}s  {metin[:58]}")
    toplam = round(sum(k["sure"] for k in kayit), 2)
    (T / "ses.json").write_text(json.dumps(kayit, ensure_ascii=False, indent=2),
                                encoding="utf-8")
    print(f"\ntoplam konuşma: {toplam}s ({toplam/60:.2f} dk)")


if __name__ == "__main__":
    main()
