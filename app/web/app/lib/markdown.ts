/**
 * Markdown alt kümesi ayrıştırıcısı — sunucunun ÜRETTİĞİ kadarı.
 *
 * İlgili: ../components/ui/Markdown.tsx, src/chatbot/structured.py,
 *         src/chatbot/safety.py
 *
 * ## Neden var
 *
 * Chatbot cevabındaki `**kalın**` işaretleri ekranda ham yıldız olarak
 * görünüyordu. Bu bir "kullanıcı markdown yazdı, işe yaramadı" durumu
 * DEĞİLDİR: markdown'ı sunucunun kendi şablonları üretiyor —
 * `structured.py:125` (`**{name}**`), `:136` (`_(not: …)_`), `:137` (`- …`) ve
 * `safety.py` içinde 12 satır. Yani her yapısal cevapta jüriye şöyle bir metin
 * gidiyordu::
 *
 *     en düşük kâr payı oranı: **Kuveyt Türk** (%1,79).
 *
 * ## Neden kütüphane yok
 *
 * `react-markdown`/`marked` yeni bağımlılıktır (offline kısıtı + lisans
 * denetimi, CLAUDE.md §1/§20). İhtiyaç dört işaretle sınırlı olduğu için
 * ayrıştırıcı burada yazıldı.
 *
 * ## Güvenlik
 *
 * Bu modül HTML DİZGESİ ÜRETMEZ; yapısal token döndürür ve render katmanı
 * onlardan React elemanı kurar. Ham HTML enjeksiyonu yapan React kaçış kapısı
 * hiç kullanılmadığı için XSS yapı gereği imkânsızdır ve sanitizasyon
 * kütüphanesine (yine yeni bağımlılık) gerek kalmaz.
 *
 * ## Tanınmayan işaret
 *
 * Birebir basılır. Kapanmamış bir `**`, "bozuk" sayılıp yutulmaz — sunucunun
 * gerçekte ne gönderdiğini gizlemek, hata ayıklamayı imkânsızlaştırır ve
 * jüriye yanlış bir metin gösterir.
 */

/**
 * Satır içi parça.
 *
 * `strong` ve `em` ÇOCUK taşır, düz metin değil: sunucu şablonları iç içe
 * işaret üretiyor. Gerçek örnek (`safety.py:337`)::
 *
 *     _Not: Kâr payı oranı **beklenen / gerçekleşmiş** bir orandır…_
 *
 * İçerik düz metin olarak saklansaydı dıştaki italik çözülür, içteki kalın
 * ham `**` olarak ekrana basılırdı — ve bu, düzeltmeye çalıştığımız kusurun
 * ta kendisi olurdu.
 *
 * `code` özyinelemez: ters tırnak arası birebir korunur, yoksa
 * `` `kar_payi_orani` `` içindeki alt çizgiler italik sanılırdı.
 */
export type Inline =
  | { tur: "text"; icerik: string }
  | { tur: "strong"; cocuklar: Inline[] }
  | { tur: "em"; cocuklar: Inline[] }
  | { tur: "code"; icerik: string };

/** Blok düzeyi düğüm. */
export type Blok =
  | { tur: "p"; satirlar: Inline[][] }
  | { tur: "ul"; ogeler: Inline[][] };

/**
 * Sözcük karakteri mi — italik sınırı için.
 *
 * KRİTİK: alan adlarımız alt çizgi taşıyor (`kar_payi_orani`, `vade_ay`).
 * Sınır kontrolü olmasaydı `kar_payi_orani` içindeki `_payi_` italik sanılır
 * ve alan adı bozulurdu. Bu yüzden `_` yalnızca sözcük SINIRINDA açılır/kapanır.
 */
function sozcukKarakteri(k: string | undefined): boolean {
  return k !== undefined && /[\p{L}\p{N}_]/u.test(k);
}

/** İçerik geçerli bir işaretçi gövdesi mi (boş değil, kenarları boşluksuz). */
function gecerliGovde(icerik: string): boolean {
  return icerik.trim() !== "" && icerik === icerik.trim();
}

/**
 * `_italik_` için kapanış konumu.
 *
 * İlk alt çizgiyi körü körüne almak yetmez: `_not: kar_payi_orani_` satırında
 * ilk aday `kar_`'ın çizgisidir ve orada kapatmak alan adını ortadan ikiye
 * böler. Sözcük sınırında duran İLK aday aranır; yoksa -1.
 */
function italikKapanisi(satir: string, baslangic: number): number {
  let k = satir.indexOf("_", baslangic);
  while (k !== -1) {
    if (!sozcukKarakteri(satir[k + 1]) && gecerliGovde(satir.slice(baslangic, k))) {
      return k;
    }
    k = satir.indexOf("_", k + 1);
  }
  return -1;
}

/**
 * Bir satırı satır içi parçalara ayırır — İÇ İÇE işaretler dâhil.
 *
 * `strong`/`em` gövdeleri özyinelemeli ayrıştırılır; gövde her zaman girdiden
 * kısa olduğu için özyineleme sonlanır. Sunucu şablonları gerçekten iç içe
 * yazıyor (`safety.py:337`: italik bir notun içinde kalın bir terim).
 *
 * Lookbehind (`(?<=…)`) BİLEREK kullanılmadı: eski Safari sürümlerinde yok ve
 * demo makinesinin tarayıcısına bağımlılık bırakmak istemiyoruz. Sınır
 * kontrolü elle yapılıyor.
 */
export function satirAyristir(satir: string): Inline[] {
  const parcalar: Inline[] = [];
  let tampon = "";
  let i = 0;

  function tamponuBosalt() {
    if (tampon) {
      parcalar.push({ tur: "text", icerik: tampon });
      tampon = "";
    }
  }

  while (i < satir.length) {
    // **kalın**
    if (satir.startsWith("**", i)) {
      const kapanis = satir.indexOf("**", i + 2);
      const icerik = kapanis === -1 ? "" : satir.slice(i + 2, kapanis);
      // `** x **` markdown değildir, düz metindir.
      if (kapanis !== -1 && gecerliGovde(icerik)) {
        tamponuBosalt();
        parcalar.push({ tur: "strong", cocuklar: satirAyristir(icerik) });
        i = kapanis + 2;
        continue;
      }
    }

    // `kod` — özyinelemez, gövde birebir korunur
    if (satir[i] === "`") {
      const kapanis = satir.indexOf("`", i + 1);
      if (kapanis !== -1 && kapanis > i + 1) {
        tamponuBosalt();
        parcalar.push({ tur: "code", icerik: satir.slice(i + 1, kapanis) });
        i = kapanis + 1;
        continue;
      }
    }

    // _italik_ — yalnız sözcük sınırında açılır ve kapanır
    if (satir[i] === "_" && !sozcukKarakteri(satir[i - 1])) {
      const kapanis = italikKapanisi(satir, i + 1);
      if (kapanis !== -1) {
        tamponuBosalt();
        parcalar.push({
          tur: "em",
          cocuklar: satirAyristir(satir.slice(i + 1, kapanis)),
        });
        i = kapanis + 1;
        continue;
      }
    }

    // Hiçbir kalıba uymadı → işaret birebir metne akar.
    tampon += satir[i];
    i += 1;
  }

  tamponuBosalt();
  return parcalar;
}

/** Satır bir liste öğesi mi (`- ` veya `* ` ile başlıyor mu). */
function listeOgesiMi(satir: string): boolean {
  return /^\s*[-*]\s+\S/.test(satir);
}

function listeIcerigi(satir: string): string {
  return satir.replace(/^\s*[-*]\s+/, "");
}

/**
 * Tam metni bloklara ayırır.
 *
 * Kurallar:
 *  - Ardışık `- ` satırları tek bir listeye toplanır.
 *  - Boş satır paragrafı böler.
 *  - Paragraf içindeki tek satır sonu KORUNUR (sunucu şablonları anlamlı satır
 *    sonu üretiyor; eski arayüz `white-space: pre-wrap` ile bunu koruyordu ve
 *    o davranış kaybedilmemeli).
 */
export function markdownAyristir(metin: string): Blok[] {
  const bloklar: Blok[] = [];
  const satirlar = metin.replace(/\r\n?/g, "\n").split("\n");

  let paragraf: Inline[][] = [];
  let liste: Inline[][] = [];

  function paragrafiKapat() {
    if (paragraf.length) {
      bloklar.push({ tur: "p", satirlar: paragraf });
      paragraf = [];
    }
  }
  function listeyiKapat() {
    if (liste.length) {
      bloklar.push({ tur: "ul", ogeler: liste });
      liste = [];
    }
  }

  for (const satir of satirlar) {
    if (listeOgesiMi(satir)) {
      paragrafiKapat();
      liste.push(satirAyristir(listeIcerigi(satir)));
      continue;
    }
    listeyiKapat();
    if (satir.trim() === "") {
      paragrafiKapat();
      continue;
    }
    paragraf.push(satirAyristir(satir));
  }

  listeyiKapat();
  paragrafiKapat();
  return bloklar;
}
