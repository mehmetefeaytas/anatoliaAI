"""1 dakikalık kesit — detaylı anlatım, hızlandırılmış konuşma.

Sayfa başına tek cümle yerine iki-üç cümle: ekranda ne olduğu değil, ne
ANLAMA geldiği anlatılıyor. Süre bütçesi değişmediği için konuşma hızı
%38'e çekildi (kullanıcı isteği).

Sayılar `sqlite3 data/demo.db` ölçümünden; hiçbiri yuvarlanmadı.
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

import edge_tts

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
CIK = T / "ses3"
CIK.mkdir(parents=True, exist_ok=True)

SES, HIZ = "tr-TR-AhmetNeural", "+38%"

# (sahne, cümle) — sahne adları kurgu3.PLAN ile eşleşiyor
CUMLELER: list[tuple[str, str]] = [
    # SIRA EKRANA GÖRE: pencere sona yaslandığı için önce oturmuş masraf
    # tablosu, sonra altındaki kanıt tablosu görünüyor. Cümleler o sırayı
    # izliyor — ilk denemede "9/10" iddiası kanıt tablosuna denk gelmişti.
    ("cetvel3", "Karşılaştırma cetveli on bankanın bin yedi yüz seksen iki "
                "belgesini tek tabloya indiriyor; masraf durumunda onun "
                "dokuzu ölçülebiliyor."),
    ("cetvel3", "Altındaki kanıt tablosunda ham ifade, güven skoru, katman "
                "ve kaynak paragraf yan yana."),
    ("cetvel3", "Her satır kendi kaynağına bağlı."),

    ("avantaj3", "En avantajlı, Yatırım Ürünü'ndeki doksan sekiz kampanyayı "
                 "bileşik skorla sıralıyor."),
    ("avantaj3", "Yalnız aynı birime normalize alanlar giriyor; girmeyen "
                 "kıyas dışı yazılıyor."),

    ("banka3", "Kuveyt Türk: beş yüz otuz yedi belge, on iki alanın on ikisi dolu."),
    ("banka3", "Sayfa her türde yıldızı kırıp hangi alanın doldurduğunu söylüyor."),

    ("celiski", "Çelişki tespiti, masrafsız deyip ücret alan kampanyaları "
                "tüm korpusta tarıyor."),

    ("sohbet", "Sohbet sayısal soruyu yapısal sorguya çeviriyor; her satır "
               "kaynak belgeye bağlı."),

    ("tazele", "Veri tazeleme her bankayı tek tıkla, robots.txt ve hız sınırıyla "
               "yeniden topluyor."),

    ("kanit", "Her değer, çıkarıldığı cümlenin karakter aralığına bağlı."),
    ("kanit", "Paragrafa tıklayınca kaynak cümle açılıyor; sayı kanıtından "
              "ayrılamıyor."),

    ("ayarlar", "Veri ekleme uçlarının şeması hazır: iş birliği kurulup API "
                "verildiğinde sistem açılmaya hazır bekliyor."),
]


def sure(yol: Path) -> float:
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(yol)],
        capture_output=True, text=True, check=True).stdout.strip())


async def uret() -> None:
    kayit = []
    for i, (sahne, metin) in enumerate(CUMLELER, start=1):
        yol = CIK / f"{i:02d}.mp3"
        await edge_tts.Communicate(metin, SES, rate=HIZ).save(str(yol))
        s = sure(yol)
        kayit.append({"no": i, "sahne": sahne, "dosya": yol.name,
                      "sure": round(s, 3), "metin": metin})
        print(f"{i:2d} {sahne:9s} {s:5.2f}s  {metin[:56]}…")
    (T / "ses3.json").write_text(
        json.dumps(kayit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ntoplam konuşma: {sum(k['sure'] for k in kayit):.1f}s  "
          f"({len(kayit)} cümle, {len({k['sahne'] for k in kayit})} sahne)")


if __name__ == "__main__":
    asyncio.run(uret())
