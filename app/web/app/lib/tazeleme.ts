/**
 * Veri tazeleme ekranının SAF yardımcıları — süre, ilerleme, özet cümlesi.
 *
 * İlgili: ../components/TazelemePanel.tsx, ./api.ts, ../../tests/tazeleme.test.ts
 *
 * Neden ayrı dosya: bu mantık bir React bileşeninin içinde kalsaydı ancak
 * tarayıcıda gözle sınanabilirdi. Yeni bir test bağımlılığı (jsdom, testing
 * library) eklemek offline/lisans kısıtı yüzünden söz konusu değil; saf
 * fonksiyonlar ise Node'un yerleşik koşucusuyla sınanabiliyor.
 *
 * Buradaki her metin kullanıcıya gösterilir, dolayısıyla Türkçedir.
 */

import type { RefreshDurum, RefreshJob, RefreshPreview } from "./api";

/** Saniyeyi okunur Türkçe süreye çevirir ("2 dk 30 sn", "45 sn"). */
export function sureMetni(saniye: number): string {
  const sn = Math.max(0, Math.round(saniye));
  if (sn < 60) return `${sn} sn`;
  const dk = Math.floor(sn / 60);
  const kalan = sn % 60;
  if (dk < 60) return kalan === 0 ? `${dk} dk` : `${dk} dk ${kalan} sn`;
  const saat = Math.floor(dk / 60);
  const dkKalan = dk % 60;
  return dkKalan === 0 ? `${saat} sa` : `${saat} sa ${dkKalan} dk`;
}

/** Ön izlemedeki alt–üst süre tahminini tek aralık cümlesine indirir. */
export function tahminiSure(onizleme: RefreshPreview): string {
  const alt = sureMetni(onizleme.tahmini_sure_alt_sn);
  const ust = sureMetni(onizleme.tahmini_sure_ust_sn);
  return alt === ust ? alt : `${alt} – ${ust}`;
}

/** Ön izlemedeki alt–üst istek sayısını tek aralık cümlesine indirir. */
export function tahminiIstek(onizleme: RefreshPreview): string {
  const { tahmini_istek_alt: alt, tahmini_istek_ust: ust } = onizleme;
  return alt === ust ? `${alt} istek` : `${alt}–${ust} istek`;
}

/** Durum kodunun kullanıcıya gösterilen Türkçe adı. */
export function durumEtiketi(durum: RefreshDurum): string {
  switch (durum) {
    case "bekliyor":
      return "Sıraya alındı";
    case "kesif":
      return "Sayfalar aranıyor";
    case "cekiliyor":
      return "Belgeler çekiliyor";
    case "yaziliyor":
      return "Arşive yazılıyor";
    case "tamam":
      return "Tamamlandı";
    case "hata":
      return "Tamamlanamadı";
    case "iptal":
      return "Durduruldu";
    default:
      return durum;
  }
}

/** Durum koduna karşılık gelen bildirim sınıfı. */
export function durumBildirimSinifi(durum: RefreshDurum): string {
  if (durum === "tamam") return "notice notice-ok";
  if (durum === "hata") return "notice notice-error";
  if (durum === "iptal") return "notice notice-warn";
  return "notice notice-info";
}

/**
 * İlerleme oranı (0–1). Toplam bilinmiyorsa `null` döner — belirsiz bir
 * ilerlemeyi %0 diye göstermek, donmuş bir çubuk izlenimi verirdi.
 */
export function ilerlemeOrani(is: RefreshJob): number | null {
  if (is.bitti) return 1;
  if (!is.toplam) return null;
  return Math.min(1, Math.max(0, is.tamamlanan / is.toplam));
}

/**
 * Sonuç özeti — "kaç belge çekildi, kaçı yeni, kaçı değişti, kaçı hata verdi".
 *
 * Bitmemiş iş için `null` döner: yarım sayıları sonuç gibi basmak, koşu
 * sürerken yanlış bir tamamlanma izlenimi yaratır.
 */
export function sonucOzeti(is: RefreshJob): string | null {
  if (!is.bitti) return null;
  const parcalar = [
    `${is.cekilen} belge çekildi`,
    `${is.yeni} yeni`,
    `${is.degisen} değişti`,
    `${is.ayni} aynı kaldı`,
    `${is.hata} hata`,
  ];
  return parcalar.join(" · ");
}

/** Belge durumunun Türkçe rozet metni. */
export function belgeDurumEtiketi(durum: "yeni" | "degisen" | "ayni"): string {
  if (durum === "yeni") return "yeni";
  if (durum === "degisen") return "değişti";
  return "aynı";
}

/** Belge durumunun rozet sınıfı — değişiklik dikkat çeker, aynılık sessizdir. */
export function belgeDurumSinifi(durum: "yeni" | "degisen" | "ayni"): string {
  if (durum === "yeni") return "badge badge-ok";
  if (durum === "degisen") return "badge badge-warn";
  return "badge";
}

/**
 * Alınamayan bir adresin gerekçesini Türkçeleştirir.
 *
 * Sunucu bu alanı toplama katmanının kendi diliyle üretiyor; ham kodu
 * ekrana basmak jüriye hiçbir şey anlatmaz.
 */
export function hataGerekcesi(reason: string): string {
  if (reason === "robots disallow")
    return "Sitenin tarama kuralları bu adrese izin vermiyor";
  if (reason === "baglanti hatasi") return "Bağlantı kurulamadı";
  if (reason.startsWith("HTTP ")) return `Site ${reason.slice(5)} yanıtı verdi`;
  return reason;
}

// --------------------------------------------------------------------------- //
// ÇIKMAZ HATALAR — "şimdi tazele" düğmesinin yalan söylediği durumlar
// --------------------------------------------------------------------------- //
//
// Aynı akıl yürütme bu depoda bir kez daha yazıldı: `src/summarize/ozet.py`
// sıcaklık 0,0'da aynı girdinin aynı çıktıyı BİREBİR ürettiğini ölçtü ve
// sonucu şöyle özetledi — «"tekrar dene" düğmesi o 12 belge için sonsuza
// kadar kısır döngüydü; kullanıcı bekler, sonuç hep 0 çıkardı». Oradaki
// çözüm `KALICI_SEBEPLER` + `kalici_sebep()` idi: belgenin KENDİSİNE ait
// sebeplerle KOŞUYA ait sebepleri ayırmak. Buradaki ayrım da aynı eksende,
// yalnız özne değişiyor: tazelemenin bazı sonuçları toplama ortamının
// değişmez bir gerçeğidir (site politikası, eksik tarayıcı bileşeni, dolu
// disk, çevrimdışı makine) ve düğmeye ikinci kez basmak kelimesi kelimesine
// aynı sonucu verir.
//
// Ayrımın bedeli asimetriktir, bu yüzden BİLİNMEYEN HER ŞEY TEKRARLANABİLİR
// sayılır: yanlışlıkla "tekrarlanabilir" demenin bedeli bir boşa deneme,
// yanlışlıkla "çıkmaz" demenin bedeli ise operatörün gerçekten işe yarayacak
// bir eylemden alıkonmasıdır. `hataGerekcesi`'nin "tanımadığı gerekçeyi
// olduğu gibi geçirir" garantisinin buradaki karşılığı budur.

/**
 * Tekrar denemekle DEĞİŞMEYECEK HTTP yanıtları.
 *
 * 429 ve 5xx bilerek dışarıda: ilki "yavaşla", ikincisi "sunucu şu an bozuk"
 * demektir ve ikisi de geçicidir. 403/404/410 ise sitenin verdiği kalıcı
 * karardır — adres değişmeden yanıt da değişmez.
 */
const KALICI_HTTP: ReadonlySet<number> = new Set([403, 404, 410]);

/** Bu adres gerekçesi tekrar denemekle değişir mi (yani çıkmaz mı). */
export function kaliciGerekce(reason: string): boolean {
  // Tarama kuralı bir politika kararıdır: aynı robots.txt, aynı adres, aynı
  // cevap. Ağ dalgalanmasıyla ilgisi yoktur.
  if (reason === "robots disallow") return true;
  if (reason.startsWith("HTTP ")) {
    const kod = Number.parseInt(reason.slice(5), 10);
    return Number.isFinite(kod) && KALICI_HTTP.has(kod);
  }
  // "baglanti hatasi" dahil geri kalan her şey: tekrarlanabilir sayılır.
  return false;
}

/** Bir çıkmazın operatöre dönük iki cümlesi: ne oldu, ne yapılabilir. */
export type TazelemeCikmazi = {
  neOldu: string;
  neYapilabilir: string;
};

//: Sunucunun ürettiği bitiş cümlesinden çıkmazı tanımak için kullanılan
//: parçalar. Eşleşme metne dayanıyor çünkü iş kaydında makine-okur bir hata
//: kodu YOK; parçalar cümlenin değişmeyen çekirdeğinden seçildi ve eşleşme
//: tutmazsa sonuç "tekrarlanabilir" olur — yani kayma, düğmeyi haksız yere
//: kilitlemez, yalnız uyarıyı susturur.
const IZ_TARAYICI = "tarayıcıyla açılmayı gerektiriyor";
const IZ_YAZMA = "ham arşive yazılamadı";
const IZ_AG_YOK = "Ağ bağlantısı kurulamadı";

/**
 * Biten bir tazeleme işi çıkmaz mı — yani "şimdi tazele" düğmesi bu banka
 * için bir söz veremez mi.
 *
 * `null` = düğme açık kalır. Çıkmaz olmayan başarısızlıklar gerçekten tekrar
 * denenebilir: site 5xx döndürmüş, istek sınırına takılmış ya da toplama
 * katmanı beklenmedik bir hata vermiş olabilir — bunların hiçbiri bir
 * sonraki koşuda aynı sonucu vermek zorunda değildir.
 */
export function isCikmazi(is: RefreshJob): TazelemeCikmazi | null {
  if (is.durum !== "hata") return null;

  const mesaj = is.mesaj ?? "";

  // 1) Tarayıcı bileşeni yok. Kurulumun kendisi internet ister; çevrimdışı
  //    bir makinede düğmeye basmak bu duvarı her seferinde aynı yerde bulur.
  if (mesaj.includes(IZ_TARAYICI)) {
    return {
      neOldu:
        "Bu bankanın sayfaları tarayıcıyla açılıyor, tarayıcı bileşeni ise " +
        "bu makinede kurulu değil.",
      neYapilabilir:
        "Düğmeye yeniden basmak aynı noktada duracaktır. Yukarıdaki iş " +
        "kaydında yazan kurulum komutu internet bağlantılı bir makinede " +
        "çalıştırılana kadar bu banka toplanamaz.",
    };
  }

  // 2) Yazma düştü. Toplama çalıştı, engel diskte: yer ya da izin.
  if (mesaj.includes(IZ_YAZMA)) {
    return {
      neOldu:
        "Belgeler toplandı ama ham arşive yazılamadı; disk dolu ya da hedef " +
        "dizine yazma izni yok.",
      neYapilabilir:
        "Yeniden toplamak yazma adımını yine aynı yerde düşürür. Önce diskte " +
        "yer açılmalı ya da yazma izni verilmeli.",
    };
  }

  // 3) Ağ yok. Sistem çevrimdışı çalışmak üzere kurulu (CLAUDE.md §1); ağa
  //    çıkan tek yol burasıdır ve o yol kapalıysa yapısal olarak kapalıdır.
  if (mesaj.includes(IZ_AG_YOK)) {
    return {
      neOldu: "Ağ bağlantısı kurulamadı.",
      neYapilabilir:
        "Bu makine internete bağlanmadan tazeleme her denemede aynı yerde " +
        "duracaktır. Kıyas, çelişki ve sohbet ekranları önceden hazırlanmış " +
        "veri tabanından okumaya devam ediyor.",
    };
  }

  // 4) Tek bir belge bile gelmedi ve listelenen adreslerin TAMAMI kalıcı
  //    gerekçeyle düştü. Liste kırpılmışsa bu yargı verilmez: görülmeyen
  //    kayıtlar arasında tekrarlanabilir bir hata olabilir.
  const listeTam = is.hata_tamami === is.hatalar.length;
  if (
    is.cekilen === 0 &&
    is.hatalar.length > 0 &&
    listeTam &&
    is.hatalar.every((h) => kaliciGerekce(h.reason))
  ) {
    const hepsiRobots = is.hatalar.every((h) => h.reason === "robots disallow");
    return hepsiRobots
      ? {
          neOldu:
            "Sitenin tarama kuralları toplanacak adreslerin tümünü kapsam " +
            "dışı bırakıyor.",
          neYapilabilir:
            "Bu bir site politikasıdır ve her denemede aynı cevabı verir. Bu " +
            "bankanın metinleri gerekiyorsa elle toplama yoluna düşülür ve " +
            "durum belgeye not edilir.",
        }
      : {
          neOldu:
            "Adreslerin tümü kalıcı bir yanıtla düştü: site erişimi reddetti " +
            "ya da sayfalar artık yok.",
          neYapilabilir:
            "Bu yanıtlar her denemede aynıdır. Banka tanım dosyasındaki " +
            "adresler güncellenmeden tazeleme sonuç vermez.",
        };
  }

  return null;
}

/**
 * Bir API hatası tekrar denemekle düzelebilir mi (HTTP durum koduna göre).
 *
 * `0` = istek hiç ulaşmadı (API kapalı ya da ayakta değil) — sunucu açılınca
 * aynı istek çalışır. `409` = koşan başka bir tazeleme var; o iş bitince
 * aynı düğme çalışır. `404` ise bu yolda bir iş kimliğinin sunucuda hiç
 * bulunmadığı anlamına gelir ve beklemekle var olmaz.
 */
export function hataTekrarlanabilir(status: number): boolean {
  if (status === 0 || status === 409 || status === 429) return true;
  return status >= 500;
}

/**
 * Yoklama bırakıldığında ekrana yazılan açıklama.
 *
 * Sessizce durmak da, sonsuza kadar sormak da kabul edilemez: ilki ilerlemeyi
 * donmuş gösterir, ikincisi kurtulunamayan bir hata bildirimi üretir.
 */
export function yoklamaBirakmaNotu(
  deneme: number,
  tekrarlanabilir: boolean,
): string {
  const bas = `Durum sorgusu ${deneme} kez üst üste düştü; ilerleme izleme durduruldu.`;
  return tekrarlanabilir
    ? `${bas} Toplama sunucuda sürüyor olabilir — durumu yeniden sormak için «Tekrar dene» düğmesini kullanın.`
    : `${bas} Bu iş kaydı sunucuda bulunamadı, dolayısıyla yeniden sormak sonuç vermez. Sonucu kapatıp yeni bir tazeleme başlatabilirsiniz.`;
}
