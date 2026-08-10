/**
 * Sohbet oturumu deposunun testleri.
 *
 * Koşum: `npm run test` (web/) — Node'un YERLEŞİK test koşucusu ve tip
 * sıyırması. Yeni bağımlılık YOKTUR (offline kısıtı + lisans denetimi).
 *
 * Bu testlerin ağırlığı üç yerde:
 *
 *  1. **BOZUK KAYIT SOHBETİ ÇÖKERTMEMELİ.** `localStorage` kullanıcının ve
 *     aynı kaynaktaki her betiğin yazabildiği bir alandır; oradan gelen veri
 *     güvenilmezdir. Bozuk bir kayıt yüzünden chatbot sekmesinin hiç
 *     açılmaması, sunumda en pahalı arıza olurdu.
 *  2. **KOTA DOLDUĞUNDA YAZMA BAŞARISIZ OLMAMALI.** RAG kaynakları belgenin
 *     tam metnini taşır; geçmiş büyüdükçe 5 MB'lık kota dolar. Beklenen
 *     davranış: eski turları unut, yeni turu SAKLA.
 *  3. **BAĞLAM PENCERESİ YENİDEN ESKİYE OLMALI.** Sunucu listeyi bu sırayla
 *     birleştirir (ilk dolu değer kazanır); sıra ters olursa hafıza en eski
 *     turda donar.
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

const { oku, yaz, temizle, baglamListesi, sonrakiKimlik, AZAMI_TUR } =
  await import("../app/lib/sohbetOturumu.ts");

/** Testlerde kullanılan en küçük geçerli tur. */
function tur(id: number, soru: string, context: unknown = null) {
  return {
    id,
    soru,
    cevap: {
      answer: `cevap ${id}`,
      handler: "structured",
      field: "kar_payi_orani",
      sources: [],
      context,
    },
    hata: null,
  } as never;
}

describe("oku / yaz", () => {
  beforeEach(depoyuKur);

  it("yazılan sohbet aynen geri okunur", () => {
    yaz([tur(1, "soru bir"), tur(2, "soru iki")]);
    const geri = oku();
    assert.equal(geri.length, 2);
    assert.deepEqual(
      geri.map((t) => t.soru),
      ["soru bir", "soru iki"],
    );
  });

  it("kayıt yokken boş liste döner", () => {
    assert.deepEqual(oku(), []);
  });

  it("bozuk JSON çökertmez", () => {
    depo.setItem(ANAHTAR, "{bu json değil");
    assert.deepEqual(oku(), []);
  });

  it("tanınmayan sürüm atılır", () => {
    depo.setItem(ANAHTAR, JSON.stringify({ v: 99, turlar: [tur(1, "x")] }));
    assert.deepEqual(oku(), []);
  });

  it("şekli bozuk turlar ayıklanır, sağlamlar korunur", () => {
    depo.setItem(
      ANAHTAR,
      JSON.stringify({
        v: 1,
        turlar: [
          { id: 1, soru: "sağlam", cevap: { answer: "a", sources: [] } },
          { soru: "kimliksiz", cevap: { answer: "a", sources: [] } },
          { id: 3, soru: "cevapsız" },
          { id: 4, soru: "kaynaksız", cevap: { answer: "a" } },
          null,
          "metin",
        ],
      }),
    );
    const geri = oku();
    assert.equal(geri.length, 1);
    assert.equal(geri[0].soru, "sağlam");
  });

  it("bekleyen ve hatalı turlar SAKLANMAZ", () => {
    yaz([
      tur(1, "tamam"),
      { id: 2, soru: "bekliyor", cevap: null, hata: null } as never,
      { id: 3, soru: "hatalı", cevap: null, hata: new Error("x") } as never,
    ]);
    assert.deepEqual(
      oku().map((t) => t.soru),
      ["tamam"],
    );
  });

  it("geçmiş azami tur sayısıyla sınırlıdır", () => {
    const cok = Array.from({ length: AZAMI_TUR + 5 }, (_, i) =>
      tur(i + 1, `soru ${i + 1}`),
    );
    yaz(cok);
    const geri = oku();
    assert.equal(geri.length, AZAMI_TUR);
    // En YENİLER korunur.
    assert.equal(geri[geri.length - 1].soru, `soru ${AZAMI_TUR + 5}`);
  });

  it("kota dolduğunda eski turlar atılır, yazma başarılı olur", () => {
    // İki tur sığacak kadar dar bir kota: tek turluk kayıt sığar.
    yaz([tur(1, "eski"), tur(2, "yeni")]);
    const tekTurluk = (depo.getItem(ANAHTAR) as string).length;
    depoyuKur();
    depo.limit = tekTurluk;

    yaz([tur(1, "eski"), tur(2, "orta"), tur(3, "yeni")]);
    const geri = oku();
    assert.ok(geri.length >= 1, "en az bir tur saklanmalıydı");
    assert.equal(geri[geri.length - 1].soru, "yeni");
  });

  it("temizle kaydı siler", () => {
    yaz([tur(1, "soru")]);
    temizle();
    assert.deepEqual(oku(), []);
  });
});

describe("baglamListesi", () => {
  beforeEach(depoyuKur);

  const ctx = (field: string) => ({
    field,
    intent: "lowest",
    filters: {},
    subject_banks: [],
  });

  it("YENİDEN ESKİYE sıralar", () => {
    const liste = baglamListesi([
      tur(1, "a", ctx("kar_payi_orani")),
      tur(2, "b", ctx("vade_ay")),
    ]);
    assert.deepEqual(
      liste.map((c) => c.field),
      ["vade_ay", "kar_payi_orani"],
    );
  });

  it("pencere boyutunu aşmaz", () => {
    const turlar = Array.from({ length: 8 }, (_, i) =>
      tur(i + 1, `s${i}`, ctx("vade_ay")),
    );
    assert.equal(baglamListesi(turlar).length, 3);
    assert.equal(baglamListesi(turlar, 1).length, 1);
  });

  it("boş bağlamlı turlar (ör. güvenlik kapısı) listeye girmez", () => {
    const bos = { field: null, intent: null, filters: {}, subject_banks: [] };
    const liste = baglamListesi([
      tur(1, "a", ctx("kar_payi_orani")),
      tur(2, "engellendi", bos),
      tur(3, "bağlamsız", null),
    ]);
    assert.equal(liste.length, 1);
    assert.equal(liste[0].field, "kar_payi_orani");
  });

  it("yalnız süzgeç taşıyan bağlam da girer", () => {
    const liste = baglamListesi([
      tur(1, "a", {
        field: null,
        intent: null,
        filters: { banks: ["albaraka"] },
        subject_banks: [],
      }),
    ]);
    assert.equal(liste.length, 1);
  });
});

describe("sonrakiKimlik", () => {
  it("boş sohbette 1'den başlar", () => {
    assert.equal(sonrakiKimlik([]), 1);
  });

  it("en büyük kimliğin bir fazlasını verir", () => {
    assert.equal(sonrakiKimlik([tur(3, "a"), tur(7, "b"), tur(5, "c")]), 8);
  });
});
