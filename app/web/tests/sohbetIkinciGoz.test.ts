/**
 * Sohbet deposunun İKİNCİ GÖZÜ — «Yeni sohbet» ile kenara alınan sohbet.
 *
 * Koşum: `npm run test` (web/) — Node'un YERLEŞİK test koşucusu ve tip
 * sıyırması. Yeni bağımlılık YOKTUR (offline kısıtı + lisans denetimi).
 *
 * Ağırlık noktaları:
 *
 *  1. **YENİ SOHBET SİLME DEĞİLDİR.** Kullanıcının isteği açıktı: yeni sohbet
 *     açılınca eski sohbet, temizlenene kadar durmalı. Kenara alınan sohbetin
 *     kaybolduğu bir hata, kullanıcı için «temizle» ile «yeni sohbet»
 *     arasındaki farkı yok eder.
 *  2. **SIRADAN YAZMA İKİNCİ GÖZE DOKUNMAZ.** Her cevaptan sonra koşan
 *     kayıt, kenara alınmış sohbeti sessizce silseydi kusur ancak birkaç tur
 *     sonra, geri dönmek istendiğinde fark edilirdi.
 *  3. **KOTA DOLUNCA ÖNCE İKİNCİ GÖZ FEDA EDİLİR.** Kullanıcının baktığı
 *     sohbeti, bakmadığı sohbet için kırpmak yanlış tarafı korumak olurdu.
 *  4. **ESKİ KAYIT OKUNABİLİR KALIR.** İkinci göz isteğe bağlı bir alandır;
 *     onu bilmeyen bir kayıt yüzünden sohbetin atılması, sürüm atlamamanın
 *     tüm amacını boşa çıkarırdı.
 */

import assert from "node:assert/strict";
import { beforeEach, describe, it } from "node:test";

const ANAHTAR = "anatolia.sohbet";

/** Kotası ayarlanabilir, en sade `Storage` taklidi. */
class SahteDepo {
  private veri = new Map<string, string>();
  /** Bu boyutun üstündeki yazma `QuotaExceededError` gibi atar. */
  limit = Number.POSITIVE_INFINITY;

  getItem(k: string): string | null {
    return this.veri.has(k) ? (this.veri.get(k) as string) : null;
  }

  setItem(k: string, v: string): void {
    if (v.length > this.limit) throw new Error("QuotaExceededError");
    this.veri.set(k, v);
  }

  removeItem(k: string): void {
    this.veri.delete(k);
  }
}

let depo: SahteDepo;

// Modül `window.localStorage`'ı ÇAĞRI ANINDA okur, import anında değil;
// bu yüzden global'i test başına değiştirmek yeterlidir.
function depoyuKur(): void {
  depo = new SahteDepo();
  (globalThis as Record<string, unknown>).window = { localStorage: depo };
}

depoyuKur();

const { oku, okuOnceki, yaz, temizle, sonrakiKimlik } = await import(
  "../app/lib/sohbetOturumu.ts"
);

/** Testlerde kullanılan en küçük geçerli tur. */
function tur(id: number, soru: string) {
  return {
    id,
    soru,
    cevap: {
      answer: `cevap ${id}`,
      handler: "structured",
      field: "kar_payi_orani",
      sources: [],
      context: null,
    },
    hata: null,
  } as never;
}

describe("ikinci göz — yazma ve okuma", () => {
  beforeEach(depoyuKur);

  it("kayıt yokken önceki sohbet boştur", () => {
    assert.deepEqual(okuOnceki(), []);
  });

  it("iki göz birbirinden bağımsız okunur", () => {
    yaz([tur(3, "yürüyen")], [tur(1, "kenara alınan")]);
    assert.deepEqual(
      oku().map((t) => t.soru),
      ["yürüyen"],
    );
    assert.deepEqual(
      okuOnceki().map((t) => t.soru),
      ["kenara alınan"],
    );
  });

  it("önceki VERİLMEZSE kenara alınan sohbete dokunulmaz", () => {
    yaz([tur(3, "yürüyen")], [tur(1, "kenara alınan")]);
    // Sıradan tur yazması: yalnız yürüyen sohbeti tazeler.
    yaz([tur(3, "yürüyen"), tur(4, "yeni tur")]);
    assert.deepEqual(
      okuOnceki().map((t) => t.soru),
      ["kenara alınan"],
    );
    assert.equal(oku().length, 2);
  });

  it("boş liste verilirse ikinci göz BOŞALTILIR", () => {
    yaz([tur(3, "yürüyen")], [tur(1, "kenara alınan")]);
    yaz([tur(3, "yürüyen")], []);
    assert.deepEqual(okuOnceki(), []);
  });

  it("yeni sohbet deseni: yürüyen sohbet ikinci göze taşınır", () => {
    const eski = [tur(1, "eski soru")];
    yaz(eski);
    // «Yeni sohbet»: ekran boşalır, eski sohbet kenara alınır.
    yaz([], eski);
    assert.deepEqual(oku(), []);
    assert.deepEqual(
      okuOnceki().map((t) => t.soru),
      ["eski soru"],
    );
  });

  it("takas deseni: iki göz yer değiştirir, hiçbiri kaybolmaz", () => {
    yaz([tur(2, "bu")], [tur(1, "önceki")]);
    const simdi = oku();
    const kenar = okuOnceki();
    yaz(kenar, simdi);
    assert.deepEqual(
      oku().map((t) => t.soru),
      ["önceki"],
    );
    assert.deepEqual(
      okuOnceki().map((t) => t.soru),
      ["bu"],
    );
  });

  it("bozuk ikinci göz yürüyen sohbeti çökertmez", () => {
    depo.setItem(
      ANAHTAR,
      JSON.stringify({ v: 1, turlar: [tur(1, "sağlam")], onceki: "metin" }),
    );
    assert.equal(oku().length, 1);
    assert.deepEqual(okuOnceki(), []);
  });

  it("ikinci gözü hiç bilmeyen eski kayıt aynen okunur", () => {
    depo.setItem(ANAHTAR, JSON.stringify({ v: 1, turlar: [tur(1, "eski")] }));
    assert.deepEqual(
      oku().map((t) => t.soru),
      ["eski"],
    );
    assert.deepEqual(okuOnceki(), []);
  });

  it("ikinci göz boşken kayda hiç yazılmaz", () => {
    yaz([tur(1, "tek")], []);
    const ham = JSON.parse(depo.getItem(ANAHTAR) as string);
    assert.equal("onceki" in ham, false);
  });
});

describe("temizle", () => {
  beforeEach(depoyuKur);

  it("HER İKİ gözü de siler", () => {
    yaz([tur(2, "bu")], [tur(1, "önceki")]);
    temizle();
    assert.deepEqual(oku(), []);
    assert.deepEqual(okuOnceki(), []);
  });
});

describe("kota", () => {
  beforeEach(depoyuKur);

  it("kota dolunca ÖNCE ikinci göz atılır, yürüyen sohbet korunur", () => {
    // Yürüyen sohbetin iki turu tam sığacak kadar bir kota ölç.
    yaz([tur(1, "bir"), tur(2, "iki")], []);
    const yalnizYuruyen = (depo.getItem(ANAHTAR) as string).length;

    depoyuKur();
    depo.limit = yalnizYuruyen;
    yaz([tur(1, "bir"), tur(2, "iki")], [tur(9, "kenara alınan")]);

    assert.deepEqual(
      oku().map((t) => t.soru),
      ["bir", "iki"],
      "yürüyen sohbet ikinci göz için kırpılmamalıydı",
    );
    assert.deepEqual(okuOnceki(), []);
  });
});

describe("sonrakiKimlik — iki göz birlikte", () => {
  it("iki gözün en büyük kimliğinin bir fazlasını verir", () => {
    const yuruyen = [tur(2, "a")];
    const kenar = [tur(7, "b")];
    assert.equal(sonrakiKimlik([...yuruyen, ...kenar]), 8);
  });
});
