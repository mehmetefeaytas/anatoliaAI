/**
 * Veri tazeleme ekranının saf yardımcılarının testleri.
 *
 * Koşum: `npm run test` (web/) — Node'un YERLEŞİK test koşucusu ve tip
 * sıyırması. Yeni bağımlılık YOKTUR (offline kısıtı + lisans denetimi).
 *
 * Bu testlerin ağırlığı üç yerde:
 *
 *  1. **BELİRSİZ İLERLEME %0 DİYE GÖSTERİLMEMELİ.** Keşif evresinde toplam
 *     adres sayısı henüz bilinmez; oranı 0 yazmak donmuş bir çubuk demektir
 *     ve operatör işi bitmiş sanıp durdurur.
 *  2. **YARIM SAYILAR SONUÇ GİBİ BASILMAMALI.** İş sürerken "3 belge çekildi,
 *     0 hata" cümlesi yanlış bir tamamlanma izlenimi yaratır.
 *  3. **HAM GEREKÇE KODU EKRANA ÇIKMAMALI.** `robots disallow` jüriye hiçbir
 *     şey anlatmaz; Türkçe karşılığı gerekir.
 *  4. **ÇÖZÜMÜ OLMAYAN HATA İÇİN "TEKRAR DENE" DENMEMELİ.** Kapalı bir tarama
 *     kuralı, kurulu olmayan tarayıcı bileşeni ya da dolu bir disk her
 *     denemede aynı sonucu verir; açık duran bir düğme tutulamayacak bir söz
 *     verir. Aynı ayrımın ölçülmüş hâli için bkz. `src/summarize/ozet.py`.
 *
 * Hiçbir test ağa çıkmaz: yardımcılar saf, girdileri elden yazılmış kayıtlar.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { RefreshJob, RefreshPreview } from "../app/lib/api.ts";
import {
  belgeDurumEtiketi,
  belgeDurumSinifi,
  durumBildirimSinifi,
  durumEtiketi,
  hataGerekcesi,
  hataTekrarlanabilir,
  ilerlemeOrani,
  isCikmazi,
  kaliciGerekce,
  sonucOzeti,
  sureMetni,
  tahminiIstek,
  tahminiSure,
  yoklamaBirakmaNotu,
} from "../app/lib/tazeleme.ts";

function is(ek: Partial<RefreshJob> = {}): RefreshJob {
  return {
    is_id: "abc",
    bank: "ornek-katilim",
    bank_name: "Örnek Katılım",
    durum: "cekiliyor",
    asama: "Belgeler çekiliyor",
    baslangic: "2026-08-10T09:00:00+00:00",
    bitis: null,
    tamamlanan: 0,
    toplam: 0,
    cekilen: 0,
    yeni: 0,
    degisen: 0,
    ayni: 0,
    hata: 0,
    yazilan_dosya: 0,
    iptal_istendi: false,
    hatalar: [],
    hata_tamami: 0,
    belgeler: [],
    notlar: [],
    robots_ozet: null,
    mesaj: null,
    hedef_dizin: null,
    bitti: false,
    ...ek,
  };
}

function onizleme(ek: Partial<RefreshPreview> = {}): RefreshPreview {
  return {
    bank: "ornek-katilim",
    bank_name: "Örnek Katılım",
    website_url: "https://ornek.example",
    scrape_mode: "static",
    giris_sayfasi: 2,
    azami_belge: 25,
    gecikme_sn: 3,
    tahmini_istek_alt: 4,
    tahmini_istek_ust: 28,
    tahmini_sure_alt_sn: 12,
    tahmini_sure_ust_sn: 140,
    arsivdeki_belge: 40,
    hedef_dizin: "data/raw/ornek-katilim/live",
    internet_gerekir: true,
    veri_tabani_etkilenir: false,
    robots_uyumu: true,
    user_agent: "AnatoliaAI-Research/1.0",
    ...ek,
  };
}

describe("sureMetni", () => {
  it("bir dakikanın altını saniye olarak yazar", () => {
    assert.equal(sureMetni(0), "0 sn");
    assert.equal(sureMetni(45), "45 sn");
    assert.equal(sureMetni(59.4), "59 sn");
  });

  it("dakikaya geçince kalanı da yazar", () => {
    assert.equal(sureMetni(60), "1 dk");
    assert.equal(sureMetni(150), "2 dk 30 sn");
  });

  it("bir saati aşınca saat + dakika yazar", () => {
    assert.equal(sureMetni(3600), "1 sa");
    assert.equal(sureMetni(5400), "1 sa 30 dk");
  });

  it("negatif değeri sıfıra çeker", () => {
    assert.equal(sureMetni(-10), "0 sn");
  });
});

describe("ön izleme cümleleri", () => {
  it("süre aralığını okunur biçimde birleştirir", () => {
    assert.equal(tahminiSure(onizleme()), "12 sn – 2 dk 20 sn");
  });

  it("alt ve üst aynıysa aralık yazmaz", () => {
    const p = onizleme({ tahmini_sure_alt_sn: 30, tahmini_sure_ust_sn: 30 });
    assert.equal(tahminiSure(p), "30 sn");
  });

  it("istek sayısını aralık olarak verir", () => {
    assert.equal(tahminiIstek(onizleme()), "4–28 istek");
    assert.equal(
      tahminiIstek(onizleme({ tahmini_istek_alt: 5, tahmini_istek_ust: 5 })),
      "5 istek",
    );
  });
});

describe("ilerlemeOrani", () => {
  it("toplam bilinmiyorken null döner — çubuk %0'da donmaz", () => {
    assert.equal(ilerlemeOrani(is({ toplam: 0, tamamlanan: 0 })), null);
  });

  it("oranı 0–1 aralığında verir", () => {
    assert.equal(ilerlemeOrani(is({ toplam: 4, tamamlanan: 1 })), 0.25);
    assert.equal(ilerlemeOrani(is({ toplam: 4, tamamlanan: 9 })), 1);
  });

  it("biten iş her hâlde tam gösterilir", () => {
    assert.equal(ilerlemeOrani(is({ bitti: true, toplam: 0 })), 1);
  });
});

describe("sonucOzeti", () => {
  it("iş sürerken özet BASMAZ", () => {
    assert.equal(sonucOzeti(is({ cekilen: 3 })), null);
  });

  it("bitince beş sayacı da sayar", () => {
    const ozet = sonucOzeti(
      is({ bitti: true, durum: "tamam", cekilen: 12, yeni: 3, degisen: 2, ayni: 7, hata: 1 }),
    );
    assert.equal(ozet, "12 belge çekildi · 3 yeni · 2 değişti · 7 aynı kaldı · 1 hata");
  });
});

describe("durum etiketleri", () => {
  it("her durum kodu Türkçe karşılık taşır", () => {
    const kodlar = [
      "bekliyor",
      "kesif",
      "cekiliyor",
      "yaziliyor",
      "tamam",
      "hata",
      "iptal",
    ] as const;
    for (const kod of kodlar) {
      const etiket = durumEtiketi(kod);
      assert.notEqual(etiket, kod, `${kod} için ham kod ekrana çıkıyor`);
      assert.ok(etiket.length > 0);
    }
  });

  it("bitiş durumları farklı bildirim sınıflarına düşer", () => {
    assert.equal(durumBildirimSinifi("tamam"), "notice notice-ok");
    assert.equal(durumBildirimSinifi("hata"), "notice notice-error");
    assert.equal(durumBildirimSinifi("iptal"), "notice notice-warn");
    assert.equal(durumBildirimSinifi("cekiliyor"), "notice notice-info");
  });
});

describe("belge durumu", () => {
  it("üç durumun da Türkçe etiketi ve rozeti var", () => {
    assert.equal(belgeDurumEtiketi("yeni"), "yeni");
    assert.equal(belgeDurumEtiketi("degisen"), "değişti");
    assert.equal(belgeDurumEtiketi("ayni"), "aynı");
    assert.equal(belgeDurumSinifi("yeni"), "badge badge-ok");
    assert.equal(belgeDurumSinifi("degisen"), "badge badge-warn");
    assert.equal(belgeDurumSinifi("ayni"), "badge");
  });
});

describe("hataGerekcesi", () => {
  it("tarama kuralı reddini açıklar", () => {
    assert.equal(
      hataGerekcesi("robots disallow"),
      "Sitenin tarama kuralları bu adrese izin vermiyor",
    );
  });

  it("bağlantı hatasını ayırır — 'internet yok' ile 'site engelledi' aynı şey değil", () => {
    assert.equal(hataGerekcesi("baglanti hatasi"), "Bağlantı kurulamadı");
    assert.equal(hataGerekcesi("HTTP 403"), "Site 403 yanıtı verdi");
  });

  it("tanımadığı gerekçeyi olduğu gibi geçirir — bilgi yutulmaz", () => {
    assert.equal(hataGerekcesi("bilinmeyen"), "bilinmeyen");
  });
});

// --------------------------------------------------------------------------- //
// Çıkmaz hatalar
// --------------------------------------------------------------------------- //

//: Sunucunun gerçekten ürettiği bitiş cümleleri (src/scraping/tazeleme.py).
//: Testler bu metinleri BİREBİR taşır: eşleşme metne dayandığı için, sunucu
//: cümlesi değişirse kırılması gereken yer burasıdır.
const MESAJ_TARAYICI =
  "Bu bankanın sayfaları tarayıcıyla açılmayı gerektiriyor. Tarayıcı " +
  "sürücüsü kurulu ancak tarayıcı bileşeni indirilmemiş. Kurmak için " +
  "`playwright install chromium` komutunu çalıştırın; bu komut internet " +
  "gerektirir. Bu banka atlandı; diğer bankaların toplanması ve önceden " +
  "hazırlanmış veri tabanından okuyan kıyas, sohbet ve pano ekranları " +
  "bundan etkilenmez.";
const MESAJ_YAZMA =
  "Belgeler ham arşive yazılamadı; disk dolu ya da hedef dizine yazma izni " +
  "yok olabilir. Ayrıntı sunucu günlüğüne kaydedildi.";
const MESAJ_AG_YOK =
  "Ağ bağlantısı kurulamadı. Bu eylem internet gerektirir; sistemin geri " +
  "kalanı çevrimdışı çalışmaya devam ediyor.";
const MESAJ_BELIRSIZ =
  "Toplama katmanı beklenmedik bir hata verdi ve tazeleme tamamlanamadı.";
const MESAJ_HEPSI_REDDEDILDI =
  "Hiçbir belge alınamadı: site istekleri reddetti ya da sayfalar erişime " +
  "kapalı. Ayrıntılar aşağıdaki listede.";

/** Başarısız bitmiş iş kaydı — çıkmaz sınamalarının ortak zemini. */
function dusenIs(ek: Partial<RefreshJob> = {}): RefreshJob {
  return is({ durum: "hata", bitti: true, ...ek });
}

describe("kaliciGerekce", () => {
  it("tarama kuralı reddi kalıcıdır — aynı robots.txt aynı cevabı verir", () => {
    assert.equal(kaliciGerekce("robots disallow"), true);
  });

  it("403/404/410 kalıcı, 429 ve 5xx değil", () => {
    assert.equal(kaliciGerekce("HTTP 403"), true);
    assert.equal(kaliciGerekce("HTTP 404"), true);
    assert.equal(kaliciGerekce("HTTP 410"), true);
    assert.equal(kaliciGerekce("HTTP 429"), false);
    assert.equal(kaliciGerekce("HTTP 500"), false);
    assert.equal(kaliciGerekce("HTTP 503"), false);
  });

  it("bağlantı hatası ve tanınmayan gerekçe TEKRARLANABİLİR sayılır", () => {
    // Asimetri bilinçli: yanlış "tekrarlanabilir" bir boşa denemeye,
    // yanlış "çıkmaz" ise işe yarayacak bir eylemin engellenmesine mal olur.
    assert.equal(kaliciGerekce("baglanti hatasi"), false);
    assert.equal(kaliciGerekce("PDF metni cikarilamadi"), false);
    assert.equal(kaliciGerekce("bilinmeyen"), false);
  });
});

describe("isCikmazi", () => {
  it("başarısız olmayan iş çıkmaz değildir", () => {
    assert.equal(isCikmazi(is({ durum: "cekiliyor" })), null);
    assert.equal(isCikmazi(is({ durum: "tamam", bitti: true })), null);
    assert.equal(isCikmazi(is({ durum: "iptal", bitti: true })), null);
  });

  it("tarayıcı bileşeni eksikken düğme söz veremez", () => {
    const c = isCikmazi(dusenIs({ mesaj: MESAJ_TARAYICI }));
    assert.ok(c, "tarayıcı eksikliği çıkmaz sayılmalı");
    assert.match(c.neOldu, /tarayıcı/);
    assert.ok(c.neYapilabilir.length > 0);
  });

  it("yazma hatası çıkmazdır — toplamayı tekrarlamak diski boşaltmaz", () => {
    const c = isCikmazi(dusenIs({ mesaj: MESAJ_YAZMA }));
    assert.ok(c);
    assert.match(c.neOldu, /yazılamadı/);
  });

  it("ağ yokluğu çıkmazdır — sistem çevrimdışı çalışmak üzere kurulu", () => {
    const c = isCikmazi(dusenIs({ mesaj: MESAJ_AG_YOK }));
    assert.ok(c);
    assert.match(c.neOldu, /Ağ bağlantısı/);
  });

  it("belirsiz toplama hatası düğmeyi KİLİTLEMEZ", () => {
    assert.equal(isCikmazi(dusenIs({ mesaj: MESAJ_BELIRSIZ })), null);
    assert.equal(isCikmazi(dusenIs({ mesaj: null })), null);
  });

  it("adreslerin tümü tarama kuralıyla kapalıysa çıkmazdır", () => {
    const c = isCikmazi(
      dusenIs({
        mesaj: MESAJ_HEPSI_REDDEDILDI,
        hatalar: [
          { url: "https://ornek.example/a", reason: "robots disallow" },
          { url: "https://ornek.example/b", reason: "robots disallow" },
        ],
        hata_tamami: 2,
        hata: 2,
      }),
    );
    assert.ok(c);
    assert.match(c.neOldu, /tarama kuralları/);
  });

  it("tümü kalıcı ama karışıksa ayrı bir çıkış yolu anlatılır", () => {
    const c = isCikmazi(
      dusenIs({
        mesaj: MESAJ_HEPSI_REDDEDILDI,
        hatalar: [
          { url: "https://ornek.example/a", reason: "robots disallow" },
          { url: "https://ornek.example/b", reason: "HTTP 404" },
        ],
        hata_tamami: 2,
        hata: 2,
      }),
    );
    assert.ok(c);
    assert.match(c.neYapilabilir, /adresler/);
  });

  it("tek bir tekrarlanabilir adres bile düğmeyi AÇIK bırakır", () => {
    assert.equal(
      isCikmazi(
        dusenIs({
          mesaj: MESAJ_HEPSI_REDDEDILDI,
          hatalar: [
            { url: "https://ornek.example/a", reason: "robots disallow" },
            { url: "https://ornek.example/b", reason: "HTTP 503" },
          ],
          hata_tamami: 2,
          hata: 2,
        }),
      ),
      null,
    );
  });

  it("liste KIRPILMIŞSA yargı verilmez — görülmeyen kayıt geçici olabilir", () => {
    assert.equal(
      isCikmazi(
        dusenIs({
          mesaj: MESAJ_HEPSI_REDDEDILDI,
          hatalar: [{ url: "https://ornek.example/a", reason: "robots disallow" }],
          hata_tamami: 40, // liste kırpıldı
          hata: 40,
        }),
      ),
      null,
    );
  });

  it("belge çekilmişse kısmi başarıdır, çıkmaz değildir", () => {
    assert.equal(
      isCikmazi(
        dusenIs({
          cekilen: 3,
          hatalar: [{ url: "https://ornek.example/a", reason: "HTTP 403" }],
          hata_tamami: 1,
          hata: 1,
        }),
      ),
      null,
    );
  });
});

describe("hataTekrarlanabilir", () => {
  it("API'ye hiç ulaşılamaması ve 409 tekrar denenebilir", () => {
    // 0 = istek hiç gitmedi (API ayakta değil), 409 = başka bir tazeleme
    // koşuyor. İkisi de bekleyip yeniden basmakla düzelir.
    assert.equal(hataTekrarlanabilir(0), true);
    assert.equal(hataTekrarlanabilir(409), true);
    assert.equal(hataTekrarlanabilir(429), true);
    assert.equal(hataTekrarlanabilir(500), true);
    assert.equal(hataTekrarlanabilir(504), true);
  });

  it("kalıcı istemci hataları tekrar denenmez", () => {
    assert.equal(hataTekrarlanabilir(400), false);
    assert.equal(hataTekrarlanabilir(403), false);
    assert.equal(hataTekrarlanabilir(404), false);
  });
});

describe("yoklamaBirakmaNotu", () => {
  it("geçici arızada yeniden sormayı önerir", () => {
    const not = yoklamaBirakmaNotu(5, true);
    assert.match(not, /5 kez/);
    assert.match(not, /Tekrar dene/);
  });

  it("kalıcı yoklukta tekrar sormayı ÖNERMEZ", () => {
    const not = yoklamaBirakmaNotu(1, false);
    assert.doesNotMatch(not, /Tekrar dene/);
    assert.match(not, /bulunamadı/);
  });
});
