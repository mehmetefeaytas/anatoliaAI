"""Seslendirme — Microsoft (Bing) nöral Türkçe sesi, edge-tts ile.

Neden ayrı dosyalar: her cümle kendi dosyasında; kurgu cümleyi MUTLAK
saniyeye yerleştiriyor. Bir cümleyi kendi sesinle yeniden kaydetmek
istersen yalnız o dosyayı değiştirmen yeterli — zaman çizgisi bozulmaz.

Not: edge-tts Microsoft'un genel uçlarını kullanır ve İNTERNET ister.
Bu yalnız videonun ÜRETİMİNDE geçerlidir; teslim edilen sistemin
offline kısıtıyla ilgisi yoktur (video bir sunum malzemesidir, ürün değil).
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
from pathlib import Path

import edge_tts

T = Path(os.environ["CLAUDE_JOB_DIR"]) / "tmp"
CIK = T / "ses2"
CIK.mkdir(parents=True, exist_ok=True)

SES = "tr-TR-AhmetNeural"
HIZ = "+14%"       # kullanıcı isteği: biraz daha hızlı, insan gibi
PERDE = "+0Hz"

# Sayılar okunacağı gibi yazılıyor: "0,671" nöral seste "sıfır virgül altı yüz
# yetmiş bir" olur ve kulakta kaybolur. Ondalıklar hane hane yazıldı.
CUMLELER: list[str] = [
    # 1 — açılış
    "Anatolia AI, katılım bankalarının kampanya metinlerinden finansal bilgiyi "
    "çıkarıp karşılaştırılabilir hâle getiren bir sistem.",
    "Şu anda gördüğünüz her şey gerçek: bin yedi yüz seksen iki belge, "
    "on katılım bankasından canlı toplandı.",
    "Panelin tamamı kendi makinenizde, internetsiz çalışıyor.",
    # 4 — karşılaştırma
    "Karşılaştırma sekmesi, şartnamenin on iki alanının tamamını tek cetvele indiriyor.",
    "Alanı değiştirdiğimde tablo yeniden kuruluyor: önce vade, sonra kâr payı oranı.",
    "Her değerin yanında güven skoru var; sistem ne kadar emin olduğunu saklamıyor.",
    "Birimler farklıysa kıyas yapılmıyor. Uydurma sıralama yerine, "
    "doğrudan kıyaslanamaz diyoruz.",
    # 8 — ısı haritası
    "Isı haritası, hangi bankanın hangi alanı yayımladığını tek bakışta gösteriyor.",
    "Boş hücreler gizlenmiyor. Çünkü bilgi metinde yoksa sistem değer üretmiyor.",
    # 10 — en avantajlı
    "En avantajlı sekmesi yalnızca aynı birime normalize edilmiş alanlar üzerinden sıralıyor.",
    "Sıralamanın dayandığı belge her zaman tek tıkla açılıyor.",
    # 12 — banka sayfası
    "Banka sayfası, tek bir kurumun bütün kampanyalarını toplandığı tarihle "
    "birlikte getiriyor.",
    # 13 — banka içi delta
    "Banka içi delta, aynı bankanın kendi kampanyaları arasındaki farkı ölçüyor. "
    "Kurumun kendi içindeki tutarsızlık da bir bulgudur.",
    # 14 — çelişki
    "Çelişki tespiti, üç yenilik hedefimizden biri.",
    "Bir yerde masrafsız deyip başka bir yerde tahsis ücreti belirten kampanyaları "
    "otomatik yakalıyor.",
    "Tarama örneklem üzerinde değil, korpusun tamamı üzerinde koşuyor.",
    # 17 — jüri audit
    "Jüri denetim paneli bu projenin merkezinde duruyor.",
    "Her değer, çıkarıldığı cümlenin karakter aralığına bağlı.",
    "Paragraf numarasına tıkladığınızda kaynak cümle açılıyor. "
    "Sayı, kanıtından ayrılamıyor.",
    "Ölçülen sonuç: yapılandırılmış alanlarda mikro F bir, sıfır virgül altmış yedi; "
    "halüsinasyon oranı yüzde dört virgül yedi.",
    # 21 — canlı çıkarım
    "Canlı çıkarım, sistemin gerçekten çalıştığının en dolaysız kanıtı.",
    "Metni veriyorsunuz, çıkarım o anda koşuyor. Önceden hazırlanmış bir cevap yok.",
    # 23 — sohbet
    "Sohbet katmanı hibrit çalışıyor: sayısal ve karşılaştırmalı sorular yapısal "
    "sorguya, koşul soruları getirimli üretime gidiyor.",
    "Cevap yine belgeye bağlı. Kaynağı olmayan cümle kurmuyoruz.",
    # 25 — veri tazeleme
    "Veri tazeleme, yeni bir bankayı tek satırlık yapılandırmayla sisteme sokuyor.",
    # 26 — işlem günlüğü
    "İşlem günlüğü her koşuyu, süresiyle ve sonucuyla birlikte kaydediyor.",
    "Yayımladığımız her sayıyı kendi sürekli tümleştirme hattımız denetliyor. "
    "Sayı kanıtından ayrışırsa yapı düşer.",
    "İki bin dokuz yüz kırk altı test, doksan altı paketlik yazılım malzeme listesi, "
    "ve tamamı açık kaynak.",
]


def sure(yol: Path) -> float:
    ç = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(yol)],
        capture_output=True, text=True, check=True)
    return float(ç.stdout.strip())


async def uret() -> None:
    kayit = []
    for i, metin in enumerate(CUMLELER, start=1):
        yol = CIK / f"{i:02d}.mp3"
        await edge_tts.Communicate(metin, SES, rate=HIZ, pitch=PERDE).save(str(yol))
        s = sure(yol)
        kayit.append({"no": i, "dosya": yol.name, "sure": round(s, 3), "metin": metin})
        print(f"{i:2d}  {s:5.2f}s  {metin[:62]}…")
    (T / "ses2.json").write_text(
        json.dumps(kayit, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\ntoplam konuşma: {sum(k['sure'] for k in kayit):.1f}s  ({len(kayit)} cümle)")


if __name__ == "__main__":
    asyncio.run(uret())
