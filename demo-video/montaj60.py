"""Bir dakikalık sürümü kurar: sahne-60 kayıtları + kartlar + etiket şeritleri.

Beş dakikalık sürümün montajıyla (`montaj.py`) aynı iskelet — süreyi ses
belirler, geçiş anlatımın bittiği sessizliğe yerleşir — üç farkla:

## Hız sahne başına seçilir, tek bir sınır dayatılmaz

Beş dakikalık sürümde tek kural vardı: mümkün olduğunca doğal hız, en çok
1,25×. Burada tek bir sayı işe yaramıyor — sahnenin işi hızı belirliyor:

* Sonuç okunacak sahneler (çıkarım çıktısı, ürün tablosu, zor vaka
  karşılaştırması) 1,3–1,5× civarında kalır; hızlandırmak tabloyu okunmaz
  yapar ve zaten fazlalık kaydın BAŞINDAN atılıyor.
* Tek sahnede üç ekran gezen operasyon turu 3× koşar; oradaki içerik statik
  ekranlar, hız "tur atma" hissi veriyor.

Bu yüzden hız `senaryo-60.json` içindeki sahne alanı. Kayıt istenen kesiti
karşılamıyorsa hız kendiliğinden düşürülür, gerekirse son kare dondurulur.

## Kesit hangi uçtan alınır — sahne söyler

`yer: son` sonucu gösteren sahneler için (çıkarım sonucu, tablo, cevap
sahnenin sonunda oluşur). `yer: bas` ise eylemin başta olduğu sahneler için:
panelin açılışı, metnin kutuya yazılması. `ofset` verilirse baş kesiti o
saniyeden başlar — sayfa yüklenirken geçen ilk saniyeleri atmaya yarar.

## İki sütunlu kadraj — ekran kesilmesin diye

1080p'de tek sütun panelin ancak bir ekranını taşıyor: sayfanın devamı hep
kadrajın dışında kalıyordu ve üç saniyelik bir sahnede kaydırarak yetişmek
mümkün değil. `duzen: cift` sahnelerinde panel uzun bir kadrajda (1280×2304)
kaydediliyor, montaj kareyi ortadan ikiye bölüp yan yana koyuyor: SOL sütun
sayfanın üstü, SAĞ sütun hemen devamı. Böylece tek karede iki ekran dolusu
içerik var ve kaydırma ilerledikçe içerik soldan yukarı çıkıp sağdan giriyor.

Geniş matrisler (ısı haritası) bölünmeye uygun değil — onlar `duzen: tek` ile
klasik 16:9 kayıttan geliyor.

`duzen: yan` ise İKİ AYRI kaydı yan yana koyuyor (banka künyesi | banka içi
delta). Akraba iki ekranı tek sahnede göstermek, on iki ekranı altmış saniyeye
sığdırırken anlatımı da telgrafa çevirmemenin tek yolu oldu: iki sahne yerine
bir sahne, ama iki ekran da görünüyor.

## Etiket bandı panelin ÜSTÜNE değil, ALTINA eklenir

İlk turda şerit köşeye bindirildi ve tam da okunması gereken yeri kapattı
(çıkarım künyesi, zor vaka tablosunun başı, banka sayfasının bölüm başlığı).
Şimdi panel görüntüsü 1768×994'e indirilip üste yaslanıyor; altta kalan 86
piksele `etiket-60/<id>.png` bandı oturuyor. Panelden hiçbir şey örtülmüyor.

`BANT` burada ile etiket şablonundaki bant yüksekliği aynı sayı olmak
zorunda — biri değişirse bant videonun üstüne biner ya da boşluk kalır.

Kartlarda bant yok: kart kendi başlığını taşıyor ve tam kare kullanılıyor.
"""

import json
import pathlib
import subprocess
import sys

KOK = pathlib.Path(__file__).parent
SENARYO = json.loads((KOK / "senaryo-60.json").read_text(encoding="utf-8"))
SESLER = {
    s["id"]: s["sure"]
    for s in json.loads((KOK / "sesler-60.json").read_text(encoding="utf-8"))["sahneler"]
}
CIKTI = KOK / "cikti"
ARA = CIKTI / "ara-60"
SAHNE_DIZIN = KOK / "sahne-60"
ETIKET_DIZIN = KOK / "etiket-60"
SES_DIZIN = KOK / "ses-60"
V = SENARYO["video"]
EN, BOY, FPS = V["cikti_en"], V["cikti_boy"], V["fps"]

GECIS = 0.25        # kısa sürümde geçiş de kısa; 0,35 burada ağır duruyor
AZAMI_HIZ = 3.2     # üstünde kaydırma okunmaz hâle geliyor — uyarı eşiği
BANT = 117          # etiket bandının yüksekliği; etiket şablonuyla aynı olmalı
ZEMIN = "0xf0f1f5"  # panel görüntüsünün yanında kalan çerçeve rengi
AYRAC = 6           # iki sütun arasındaki çizgi kalınlığı


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
    """Duran kartı yavaş yakınlaşan bir çekime çevirir."""
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


def kesit(sahne: dict, webm: pathlib.Path, istenen: float) -> tuple[list[str], str, float]:
    """Kaydın hangi parçasının hangi hızla alınacağını hesaplar.

    Dönenler: ffmpeg girdi argümanları, zaman süzgeci öneki, seçilen hız.
    """
    ham = sure(webm)
    hiz = float(sahne.get("hiz", 1.0))
    gereken = istenen * hiz                     # hızlandırma öncesi ham uzunluk

    if sahne.get("yer") == "bas":
        # Baş kesiti: ofsetten başla, ama kaydın sonuna taşacak kadar değil.
        basla = min(float(sahne.get("ofset", 0.0)), max(0.0, ham - gereken))
    else:
        basla = max(0.0, ham - gereken)

    mevcut = ham - basla
    if mevcut < gereken:
        # Kayıt istenen kesiti karşılamıyor: senaryodaki hızı zorlamak yerine
        # elde olanı doğala yaklaştır. Kalan açık son karenin dondurulmasıyla
        # kapanır — yavaşlatmak kaydırmaları ağırlaştırıyordu.
        hiz = max(1.0, mevcut / istenen)

    zaman = f"setpts=PTS/{hiz:.6f},"
    sonuc = mevcut / hiz
    if sonuc < istenen - 0.02:
        zaman += f"tpad=stop_mode=clone:stop_duration={istenen - sonuc + 0.5:.3f},"
    return ["-ss", f"{basla:.3f}", "-i", str(webm)], zaman, hiz


def panel_sahnesi(sahne: dict, hedef: float, cikti: pathlib.Path) -> str:
    """Kaydı hedef süreye oturtur, etiket şeridini bindirir.

    Dönen değer, ekrana basılacak kısa künye: hangi kesit hangi hızla alındı.
    """
    kaynaklar = sahne.get("kaynaklar", [sahne.get("kaynak")])
    webm = SAHNE_DIZIN / f"{kaynaklar[0]}.webm"
    ham = sure(webm)
    istenen = hedef + GECIS
    girdi, zaman, hiz = kesit(sahne, webm, istenen)
    basla = float(girdi[1])
    ic_boy = BOY - BANT
    kx, ken, kboy = V["sutun_kirp_x"], V["sutun_kirp_en"], V["sutun_boy"]
    if sahne.get("duzen") == "yan":
        # İki ayrı kayıt: her birinin ÜST sütunu alınır, yan yana konur.
        ikinci = SAHNE_DIZIN / f"{kaynaklar[1]}.webm"
        girdi2, zaman2, hiz2 = kesit(sahne, ikinci, istenen)
        girdi = girdi + girdi2
        zincir = (
            f"[0:v]{zaman}fps={FPS},crop={ken}:{kboy}:{kx}:0[sol];"
            f"[1:v]{zaman2}fps={FPS},crop={ken}:{kboy}:{kx}:0[sag];"
            f"[sol][sag]hstack=inputs=2,"
            f"scale={EN}:{ic_boy}:flags=lanczos,"
            # İki sütun arasına ince bir zemin çizgisi: bitişik iki ekran
            # tek sayfa gibi okunuyordu.
            f"drawbox=x={(EN - AYRAC) // 2}:y=0:w={AYRAC}:h={ic_boy}:"
            f"color={ZEMIN}:t=fill,"
            f"pad={EN}:{BOY}:0:0:color={ZEMIN},setsar=1,format=yuv420p[v]"
        )
        hiz = max(hiz, hiz2)
    elif sahne.get("duzen") == "cift":
        # Uzun kayıt ortadan ikiye: üst yarı sol sütun, alt yarı sağ sütun.
        # Kırpma main sütununu alıyor — sayfa kenarındaki boşluğu taşımanın
        # anlamı yok, o pikseller okunacak içerik olabilirdi.
        zincir = (
            f"[0:v]{zaman}fps={FPS},split=2[a][b];"
            f"[a]crop={ken}:{kboy}:{kx}:0[sol];"
            f"[b]crop={ken}:{kboy}:{kx}:{kboy}[sag];"
            f"[sol][sag]hstack=inputs=2,"
            f"scale={EN}:{ic_boy}:flags=lanczos,"
            # İki sütun arasına ince bir zemin çizgisi: bitişik iki ekran
            # tek sayfa gibi okunuyordu.
            f"drawbox=x={(EN - AYRAC) // 2}:y=0:w={AYRAC}:h={ic_boy}:"
            f"color={ZEMIN}:t=fill,"
            f"pad={EN}:{BOY}:0:0:color={ZEMIN},setsar=1,format=yuv420p[v]"
        )
    else:
        # 16:9 kayıt: bant payı çıkınca kalan yüksekliğe oranı bozulmadan
        # oturtulur, yanlarda kalan boşluk zeminle dolar.
        ic_en = round(ic_boy * 16 / 9 / 2) * 2
        zincir = (
            f"[0:v]{zaman}scale={ic_en}:{ic_boy}:flags=lanczos,"
            f"pad={EN}:{BOY}:{(EN - ic_en) // 2}:0:color={ZEMIN},setsar=1,"
            f"fps={FPS},format=yuv420p[v]"
        )
    etiket = ETIKET_DIZIN / f"{sahne['id']}.png"
    if etiket.exists():
        # Etiketin girdi numarası kaynak sayısına bağlı: «yan» sahnelerde iki
        # video girdisi var ve sabit [1:v] yazmak etiket yerine ikinci kaydı
        # bindiriyordu — bant kayboluyor, ham kayıt karenin üstüne biniyordu.
        girdi += ["-i", str(etiket)]
        zincir += (f";[v][{len(kaynaklar)}:v]overlay=0:0:format=auto,"
                   f"format=yuv420p[o]")
        cikis = "[o]"
    else:
        cikis = "[v]"

    kos(["ffmpeg", "-y", "-v", "error", *girdi, "-an",
         "-filter_complex", zincir, "-map", cikis, "-t", f"{istenen:.3f}",
         "-c:v", "libx264", "-crf", "16", "-preset", "medium",
         "-pix_fmt", "yuv420p", str(cikti)])

    if hiz > AZAMI_HIZ:
        print(f"   ! {sahne['id']}: {hiz:.1f}× hız okunurluk eşiğinin üstünde",
              file=sys.stderr)
    return (f"{sahne.get('duzen', 'tek'):>4} · {sahne.get('yer', 'son')} "
            f"{basla:4.1f}–{ham:4.1f} sn · {hiz:.1f}×")


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

    parcalar = []
    for sahne in sahneler:
        sid = sahne["id"]
        hedef = SESLER[sid]
        hedef_dosya = ARA / f"{sid}.mp4"
        if sahne["tur"] == "kart":
            kart_sahnesi(KOK / "kart" / f"{sahne['kart']}.png", hedef, hedef_dosya)
            not_ = "kart"
        else:
            not_ = panel_sahnesi(sahne, hedef, hedef_dosya)
        parcalar.append(hedef_dosya)
        print(f"  hazır: {sid:<26} {sure(hedef_dosya):5.2f} sn "
              f"(anlatım {hedef:4.2f}) {not_}")

    girdiler: list[str] = []
    for p in parcalar:
        girdiler += ["-i", str(p)]
    for sahne in sahneler:
        girdiler += ["-i", str(SES_DIZIN / f"{sahne['id']}.mp3")]

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
    suzgec.append(
        f"{''.join(ses_etiketleri)}amix=inputs={n}:normalize=0:"
        f"dropout_transition=0,loudnorm=I=-16:TP=-1.5:LRA=11[a]"
    )

    hedef_mp4 = CIKTI / "anatolia-ai-demo-60sn.mp4"
    kos(["ffmpeg", "-y", "-v", "error", *girdiler,
         "-filter_complex", ";".join(suzgec),
         "-map", f"[{onceki}]", "-map", "[a]",
         "-c:v", "libx264", "-crf", "19", "-preset", "slow",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
         str(hedef_mp4)])

    srt_yaz(sahneler, CIKTI / "anatolia-ai-demo-60sn.tr.srt")
    toplam = sure(hedef_mp4)
    print(f"\nyazıldı: {hedef_mp4}")
    print(f"süre   : {toplam:.2f} sn · hedef ~60 sn")
    if toplam > 66:
        print("UYARI: bir dakikalık sürüm 66 sn'yi aştı.", file=sys.stderr)


main()
