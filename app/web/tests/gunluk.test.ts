/**
 * İşlem günlüğü (audit log) görüntüleme yardımcılarının testleri.
 *
 * Koşum: `npm run test` (web/) — Node'un YERLEŞİK test koşucusu ve tip
 * sıyırması. Yeni bağımlılık YOKTUR (offline kısıtı + lisans denetimi).
 * Bileşen render EDİLMEZ: karar veren her şey `app/lib/gunluk.ts` içinde saf
 * fonksiyon hâlinde duruyor, `.tsx` yalnız çiziyor.
 *
 * Bu testlerin ağırlığı dört yerde:
 *
 *  1. **ZAMAN UTC KALMALI.** Panel damgayı yerel saate çevirseydi ekrandaki
 *     satır ile `data/gunluk/*.jsonl` içindeki satır birbirini tutmazdı ve
 *     denetim kaydının asıl işi ("şu saatte ne oldu") bir saat dilimi hesabına
 *     dönerdi. Test bunu sabit bir damgayla kilitler; koşan makinenin saat
 *     dilimi sonucu DEĞİŞTİRMEMELİ.
 *  2. **EKSİK DEĞER UYDURULMAZ.** Bozuk/boş damga `Invalid Date` değil çizgi
 *     basar; bilinmeyen süre `0 ms` değil çizgi basar. `null` ile `0` aynı
 *     hücreye düşmez (CLAUDE.md §21).
 *  3. **EYLEM ÖZETİ GÖVDE TAŞIMAZ ama BİLGİ DE YUTMAZ.** Bilinmeyen anahtar
 *     gizlenmez, ham adıyla basılır — gizlemek, bir ucun bildirdiği bilgiyi
 *     panelin sessizce düşürmesi olurdu.
 *  4. **BOŞ SÜZGEÇ SUNUCUYA GİTMEZ.** `metot=""` sunucuda "metodu boş olan
 *     kayıt" anlamına gelip süzgeci sessizce her şeyi eleyen bir şeye
 *     çevirebilirdi.
 *
 * Hiçbir test ağa çıkmaz: yardımcılar saf, girdiler elden yazılmış kayıtlar.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { GunlukKaydi } from "../app/lib/api.ts";
import {
  BOS_SUZGEC,
  YOK,
  dondurmeCumlesi,
  durumSinifi,
  eylemOzeti,
  sorguParametreleri,
  sureEtiketi,
  suzgecEtkin,
  zamanDamgasi,
} from "../app/lib/gunluk.ts";

describe("zamanDamgasi — UTC, uydurma yok", () => {
  it("ISO damgayı UTC olarak biçimler", () => {
    assert.equal(
      zamanDamgasi("2026-08-13T09:14:22+00:00"),
      "2026-08-13 09:14:22",
    );
  });

  it("saat dilimi taşıyan damga UTC'ye çevrilir, yerel saate DEĞİL", () => {
    // +03:00'te 12:14 olan an, UTC'de 09:14'tür. Koşan makinenin saat dilimi
    // ne olursa olsun beklenen budur.
    assert.equal(
      zamanDamgasi("2026-08-13T12:14:22+03:00"),
      "2026-08-13 09:14:22",
    );
  });

  it("Z eki de kabul edilir", () => {
    assert.equal(zamanDamgasi("2026-01-02T03:04:05Z"), "2026-01-02 03:04:05");
  });

  it("boş/bozuk damga çizgi basar, Invalid Date değil", () => {
    for (const girdi of [null, undefined, "", "   ", "dün", "13.08.2026x"]) {
      assert.equal(zamanDamgasi(girdi as string | null), YOK, String(girdi));
    }
  });
});

describe("sureEtiketi", () => {
  it("milisaniye Türkçe sayı biçiminde", () => {
    assert.equal(sureEtiketi(12.4), "12,4 ms");
    assert.equal(sureEtiketi(0), "0 ms");
  });

  it("saniyeye taşan süre saniyeye çevrilir", () => {
    assert.equal(sureEtiketi(1240), "1,24 s");
  });

  it("bilinmeyen süre 0 DEĞİL çizgidir", () => {
    assert.equal(sureEtiketi(null), YOK);
    assert.equal(sureEtiketi(undefined), YOK);
    assert.equal(sureEtiketi(Number.NaN), YOK);
  });
});

describe("durumSinifi — 4xx uyarı, 5xx hata", () => {
  it("2xx başarı rozetine düşer", () => {
    assert.equal(durumSinifi(200), "badge badge-ok");
    assert.equal(durumSinifi(202), "badge badge-ok");
  });

  it("istemci hatası uyarı, sunucu hatası hata", () => {
    assert.equal(durumSinifi(404), "badge badge-warn");
    assert.equal(durumSinifi(409), "badge badge-warn");
    assert.equal(durumSinifi(500), "badge badge-bad");
    assert.equal(durumSinifi(503), "badge badge-bad");
  });

  it("kod yoksa yalın rozet — renk iddiası uydurulmaz", () => {
    assert.equal(durumSinifi(null), "badge");
    assert.equal(durumSinifi(undefined), "badge");
  });
});

describe("eylemOzeti", () => {
  it("bilinen anahtarlar Türkçe etiketle basılır", () => {
    assert.equal(
      eylemOzeti({ banka: "albaraka", yazilan_dosya: 40 }),
      "banka: albaraka · yazılan dosya: 40",
    );
  });

  it("bilinmeyen anahtar GİZLENMEZ, ham adıyla geçer", () => {
    assert.equal(eylemOzeti({ yeni_alan: "deger" }), "yeni_alan: deger");
  });

  it("null/boş değerler atlanır, hepsi boşsa null döner", () => {
    assert.equal(
      eylemOzeti({ banka: "vakif", hedef_dizin: null, durum_adi: "" }),
      "banka: vakif",
    );
    assert.equal(eylemOzeti({ hedef_dizin: null }), null);
    assert.equal(eylemOzeti(null), null);
    assert.equal(eylemOzeti(undefined), null);
    assert.equal(eylemOzeti({}), null);
  });

  it("sayılar Türkçe biçimde", () => {
    assert.equal(eylemOzeti({ metin_uzunlugu: 12345 }), "metin uzunluğu: 12.345");
  });
});

describe("dondurmeCumlesi — döndürme sessiz kalmaz", () => {
  const dondu: GunlukKaydi = {
    zaman: "2026-08-13T09:00:00+00:00",
    olay: "gunluk_dondu",
    bayt: 5242880,
    tasinan_dosya: "islem-gunlugu.jsonl.1",
    silinen_dosya: "islem-gunlugu.jsonl.3",
  };

  it("taşınan ve silinen dosyayı söyler", () => {
    const cumle = dondurmeCumlesi(dondu);
    assert.ok(cumle);
    assert.match(cumle, /islem-gunlugu\.jsonl\.1/);
    assert.match(cumle, /islem-gunlugu\.jsonl\.3/);
    assert.match(cumle, /5\.120 KB/);
  });

  it("silinen kuşak yoksa o cümle hiç kurulmaz", () => {
    const cumle = dondurmeCumlesi({ ...dondu, silinen_dosya: null });
    assert.ok(cumle);
    assert.ok(!cumle.includes("silindi"));
  });

  it("istek kaydı için null döner (satır normal çizilsin)", () => {
    const istek: GunlukKaydi = {
      zaman: "2026-08-13T09:00:00+00:00",
      olay: "istek",
      metot: "POST",
      yol: "/refresh",
      durum: 202,
    };
    assert.equal(dondurmeCumlesi(istek), null);
  });
});

describe("süzgeç → sorgu parametreleri", () => {
  it("boş alanlar SUNUCUYA GİTMEZ", () => {
    const p = sorguParametreleri(BOS_SUZGEC, { limit: 50, offset: 0 });
    assert.deepEqual(p, { yalniz_yazanlar: true, limit: 50, offset: 0 });
  });

  it("dolu alanlar kırpılarak geçer", () => {
    const p = sorguParametreleri(
      {
        yalnizYazanlar: false,
        metot: "POST",
        yol: "  refresh  ",
        baslangic: "2026-08-13",
        bitis: "",
      },
      { limit: 50, offset: 100 },
    );
    assert.deepEqual(p, {
      yalniz_yazanlar: false,
      limit: 50,
      offset: 100,
      metot: "POST",
      yol: "refresh",
      baslangic: "2026-08-13",
    });
  });

  it("suzgecEtkin yalnız gerçek süzgeçlere True der", () => {
    assert.equal(suzgecEtkin(BOS_SUZGEC), false);
    // «yalnız yazanlar» bir SÜZGEÇ değil VARSAYILAN görünüm: boş-hâl metni
    // ona bakarak "süzgeci temizleyin" dememeli.
    assert.equal(suzgecEtkin({ ...BOS_SUZGEC, yalnizYazanlar: false }), false);
    assert.equal(suzgecEtkin({ ...BOS_SUZGEC, yol: "refresh" }), true);
    assert.equal(suzgecEtkin({ ...BOS_SUZGEC, metot: "POST" }), true);
    assert.equal(suzgecEtkin({ ...BOS_SUZGEC, bitis: "2026-08-13" }), true);
  });
});
