"""Sahne videoları + kartlar + anlatım seslerini tek mp4'e birleştirir.

## Süre otoritesi sestir

Her sahnenin uzunluğunu ANLATIM belirler. Görüntü ona uydurulur, tersi değil:
bir sahneyi sesinden kısa tutmak cümleyi ortadan kesmek, uzun tutmak da
sessizlik biriktirmek olurdu.

## Fazlalık baştan kırpılır, sondan değil

Panel sahneleri bilerek anlatımdan uzun kaydedildi. Fazlalığı sondan kırpmak
en kötü seçenekti: sonuç tabloları sahnenin SONUNDA görünür (çıkarım ~20 sn
sürüyor), yani kırpma tam olarak kanıtı kesiyordu. Bunun yerine fazlalığın bir
kısmı ölçülü bir hızlandırmayla (en çok 1.25×, göz fark etmez), kalanı
sahnenin BAŞINDAN — sayfa yüklenmesi, ilk boş kaydırma — alınıyor.

## Geçiş 0,35 sn ve ses örtüşmüyor

Sahne videosu anlatımdan 0,35 sn uzun bırakılıp geçiş o paya yerleştiriliyor.
Böylece çapraz geçiş sırasında iki konuşma üst üste binmiyor; örtüşen kısım
sahnenin sonundaki sessizlik oluyor. Toplam süre = anlatım toplamı + 0,35 sn.
"""

import json
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).parent
SENARYO = json.loads((KOK / "senaryo.json").read_text(encoding="utf-8"))
SESLER = {
    s["id"]: s["sure"]
    for s in json.loads((KOK / "sesler.json").read_text(encoding="utf-8"))["sahneler"]
}
CIKTI = KOK / "cikti"
ARA = KOK / "cikti" / "ara"
V = SENARYO["video"]
EN, BOY, FPS = V["cikti_en"], V["cikti_boy"], V["fps"]

GECIS = 0.35        # çapraz geçiş süresi (sn)
AZAMI_HIZ = 1.25    # bunun üstünde hızlandırma gözle görülür


def kos(argumanlar: list[str]) -> None:
    subprocess.run(argumanlar, check=True, capture_output=True)


def sure(dosya: pathlib.Path) -> float:
    c = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(dosya)],
        capture_output=True, text=True, check=True,
    )
    return float(c.stdout.strip())


def kart_sahnesi(png: pathlib.Path, hedef: float, cikti: pathlib.Path) -> None:
    """Duran kartı yavaş yakınlaşan bir çekime çevirir.

    Tamamen hareketsiz bir kare, videonun donduğu izlenimi veriyor; %3'lük
    yavaş bir yakınlaşma kartı canlı tutuyor ve metni bozmuyor.
    """
    kare = int((hedef + GECIS) * FPS)
    suzgec = (
        f"scale={EN * 2}:-2,"
        f"zoompan=z='min(1.03,1+0.03*on/{kare})':d=1:"
        f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={EN}x{BOY}:fps={FPS},"
        f"setsar=1,format=yuv420p"
    )
    kos(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(png),
         "-t", f"{hedef + GECIS:.3f}", "-vf", suzgec, "-r", str(FPS),
         "-c:v", "libx264", "-crf", "16", "-preset", "medium",
         "-pix_fmt", "yuv420p", str(cikti)])


def panel_sahnesi(webm: pathlib.Path, hedef: float, cikti: pathlib.Path) -> None:
    """Kaydı hedef süreye oturtur: gerekirse hızlandırır, fazlasını baştan atar."""
    ham = sure(webm)
    istenen = hedef + GECIS
    if ham > istenen:
        hiz = min(AZAMI_HIZ, ham / istenen)
        kirpma_sonrasi = istenen * hiz          # hızlandırma öncesi gereken uzunluk
        basla = max(0.0, ham - kirpma_sonrasi)
        girdi = ["-ss", f"{basla:.3f}", "-i", str(webm)]
        zaman = f"setpts=PTS/{hiz:.6f},"
    else:
        # Kayıt kısa kaldı: son kare hedefe kadar dondurulur. Yavaşlatmak
        # kaydırmaları ağırlaştırıyordu; donan bir son kare göze batmıyor.
        girdi = ["-i", str(webm)]
        zaman = f"tpad=stop_mode=clone:stop_duration={istenen - ham + 0.5:.3f},"
    suzgec = (
        f"{zaman}scale={EN}:{BOY}:flags=lanczos,setsar=1,"
        f"fps={FPS},format=yuv420p"
    )
    kos(["ffmpeg", "-y", "-v", "error", *girdi, "-an",
         "-vf", suzgec, "-t", f"{istenen:.3f}",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium",
         "-pix_fmt", "yuv420p", str(cikti)])


def srt_yaz(sahneler: list[dict], yol: pathlib.Path) -> None:
    """Anlatımı altyazıya döker — sesi kapalı izleyen jüri için."""

    def damga(sn: float) -> str:
        s, ms = divmod(round(sn * 1000), 1000)
        d, s = divmod(s, 60)
        sa, d = divmod(d, 60)
        return f"{sa:02d}:{d:02d}:{s:02d},{ms:03d}"

    satirlar, t = [], 0.0
    for i, sahne in enumerate(sahneler, 1):
        s = SESLER[sahne["id"]]
        satirlar.append(f"{i}\n{damga(t)} --> {damga(t + s)}\n{sahne['anlatim']}\n")
        t += s
    yol.write_text("\n".join(satirlar), encoding="utf-8")


def main() -> None:
    CIKTI.mkdir(exist_ok=True)
    ARA.mkdir(parents=True, exist_ok=True)
    sahneler = SENARYO["sahneler"]

    # 1) Her sahneyi sessiz, tam süreli, aynı biçimde bir mp4'e indir.
    parcalar = []
    for sahne in sahneler:
        sid = sahne["id"]
        hedef = SESLER[sid]
        hedef_dosya = ARA / f"{sid}.mp4"
        if sahne["tur"] == "kart":
            kart_sahnesi(KOK / "kart" / f"{sahne['kart']}.png", hedef, hedef_dosya)
        else:
            panel_sahnesi(KOK / "sahne" / f"{sid}.webm", hedef, hedef_dosya)
        parcalar.append(hedef_dosya)
        print(f"  hazır: {sid:<24} {sure(hedef_dosya):6.2f} sn (anlatım {hedef:.2f})")

    # 2) Tek geçişte çapraz geçişli video zinciri + hizalı ses karışımı.
    #    Ara birleştirme yapılmıyor: her adım yeniden kodlama demek olurdu.
    girdiler: list[str] = []
    for p in parcalar:
        girdiler += ["-i", str(p)]
    for sahne in sahneler:
        girdiler += ["-i", str(KOK / "ses" / f"{sahne['id']}.mp3")]

    n = len(parcalar)
    suzgec: list[str] = []
    onceki = "0:v"
    offset = 0.0
    for i in range(1, n):
        offset += SESLER[sahneler[i - 1]["id"]]
        etiket = f"v{i}"
        suzgec.append(
            f"[{onceki}][{i}:v]xfade=transition=fade:"
            f"duration={GECIS}:offset={offset:.3f}[{etiket}]"
        )
        onceki = etiket

    gecikme = 0.0
    ses_etiketleri = []
    for i, sahne in enumerate(sahneler):
        etiket = f"a{i}"
        ms = int(round(gecikme * 1000))
        suzgec.append(f"[{n + i}:a]adelay={ms}|{ms},aresample=48000[{etiket}]")
        ses_etiketleri.append(f"[{etiket}]")
        gecikme += SESLER[sahne["id"]]
    # loudnorm: ham karışım -16,9 LUFS ölçüldü — yayın hedefine yakın ama
    # sahneler arası küçük farklar var. `-ac 2`: kaynak anlatım tek kanallı
    # ve mono bir yayın bazı kurulumlarda tek hoparlörden çıkıyor.
    suzgec.append(
        f"{''.join(ses_etiketleri)}amix=inputs={n}:normalize=0:"
        f"dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    hedef_mp4 = CIKTI / "anatolia-ai-demo.mp4"
    kos(["ffmpeg", "-y", "-v", "error", *girdiler,
         "-filter_complex", ";".join(suzgec),
         "-map", f"[{onceki}]", "-map", "[a]",
         "-c:v", "libx264", "-crf", "19", "-preset", "slow",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         str(hedef_mp4)])

    srt_yaz(sahneler, CIKTI / "anatolia-ai-demo.tr.srt")
    toplam = sure(hedef_mp4)
    print(f"\nyazıldı: {hedef_mp4}")
    print(f"süre   : {toplam:.2f} sn ({toplam / 60:.2f} dk) · sınır 5 dk")
    if toplam > 300:
        print("UYARI: 5 dakikalık sınır aşıldı.", file=sys.stderr)


main()
