/**
 * İstemci arama eşleştirmesinin testleri — ve SUNUCUYLA PARİTESİ.
 *
 * Koşum: `npm run test` (web/) — Node'un yerleşik test koşucusu ve tip
 * sıyırması. Yeni bağımlılık YOKTUR (`node:test` + `node:assert` standart
 * kütüphanede, `.ts` doğrudan çalışır).
 *
 * Bu testlerin ağırlığı üç yerde:
 *
 *   1. TÜRKÇE KÜÇÜLTME. `"İhtiyaç".toLowerCase()` JavaScript'te 'i' + birleşen
 *      nokta üretir; ekranda doğru görünen ama `includes("ihtiyac")` ile
 *      eşleşmeyen bir dize. Bu, aramanın sessizce hiçbir şey bulmaması
 *      demektir — hata mesajı da yoktur, sadece boş liste.
 *   2. SUNUCUYLA AYNI SONUÇ. Beklenen katlamalar burada elle yazılmaz;
 *      `tests/arama_katlama_ornekleri.json` iki testte de okunur. İki dilde
 *      ayrı ayrı yazılsaydı biri güncellenip öteki unutulduğunda sunucu
 *      bulur, istemci bulmazdı.
 *   3. VURGULAMA ÖZGÜN YAZIYI KORUR. Kullanıcıya 'kar payi' değil 'kâr payı'
 *      gösterilmeli; katlama uzunluk korumadığı için konumlar geri
 *      çevrilmek zorunda.
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { describe, it } from "node:test";
import {
  alanEtiketi,
  alanlarEslesiyorMu,
  aramaTerimleri,
  terimlerEslesiyorMu,
  trKatla,
  vurgulariBul,
} from "../app/lib/arama.ts";

/** Sunucu testiyle ORTAK fikstür — beklenen değerlerin tek kaynağı. */
const FIKSTUR = JSON.parse(
  readFileSync(
    new URL("../../tests/arama_katlama_ornekleri.json", import.meta.url),
    "utf-8",
  ),
) as {
  ornekler: Array<{ girdi: string; katli: string }>;
};

/** Metni vurgu parçalarından yeniden kurar (kayıpsızlık denetimi için). */
function yenidenKur(metin: string, terimler: string[]): string {
  return vurgulariBul(metin, terimler)
    .map((p) => metin.slice(p.bas, p.son))
    .join("");
}

describe("trKatla — sunucu paritesi", () => {
  it("fikstür boş değil (test kendini kandırmasın)", () => {
    assert.ok(FIKSTUR.ornekler.length >= 20);
  });

  for (const { girdi, katli } of FIKSTUR.ornekler) {
    it(`«${girdi}» → «${katli}»`, () => {
      assert.equal(trKatla(girdi), katli);
    });
  }
});

describe("trKatla — JavaScript'in bozuk davranışına karşı", () => {
  it("İ birleşen nokta BIRAKMAZ", () => {
    // Yerelleştirmesiz toLowerCase burada 'i' + U+0307 üretir.
    assert.equal("İhtiyaç".toLowerCase().length, 8);
    assert.equal(trKatla("İhtiyaç"), "ihtiyac");
    assert.ok(!trKatla("İhtiyaç").includes("̇"));
  });

  it("I harfi 'ı' üzerinden 'i'ye iner", () => {
    assert.equal(trKatla("IŞIK"), "isik");
  });

  it("diakritiksiz sorgu diakritikli metni bulur", () => {
    assert.ok(trKatla("İhtiyaç Finansmanı").includes(trKatla("ihtiyac")));
    assert.ok(trKatla("Kâr Payı Oranı").includes("kar payi"));
  });

  it("boş girdi boş çıktı", () => {
    assert.equal(trKatla(""), "");
  });

  it("katlama idempotenttir", () => {
    const bir = trKatla("İhtiyaç Finansmanı");
    assert.equal(trKatla(bir), bir);
  });
});

describe("aramaTerimleri", () => {
  it("boşluklara böler ve katlar", () => {
    assert.deepEqual(aramaTerimleri("  İhtiyaç   FİNANSMANI "), [
      "ihtiyac",
      "finansmani",
    ]);
  });

  it("tekrar eden terimi bir kez döndürür", () => {
    assert.deepEqual(aramaTerimleri("konut konut"), ["konut"]);
  });

  it("boş sorgu boş dizi", () => {
    assert.deepEqual(aramaTerimleri(""), []);
    assert.deepEqual(aramaTerimleri("   "), []);
  });
});

describe("terimlerEslesiyorMu", () => {
  it("tüm terimler geçmeli", () => {
    assert.ok(terimlerEslesiyorMu("İhtiyaç Finansmanı", ["ihtiyac"]));
    assert.ok(!terimlerEslesiyorMu("İhtiyaç Finansmanı", ["ihtiyac", "konut"]));
  });

  it("terimsiz sorgu HİÇBİR ŞEYE eşleşmez", () => {
    // Boş sorgu 'her şey eşleşti' demek olsaydı, kutu açılır açılmaz
    // korpusun tamamı listelenirdi.
    assert.ok(!terimlerEslesiyorMu("Kuveyt Türk", []));
  });
});

describe("alanlarEslesiyorMu", () => {
  const alanlar = ["Kuveyt Türk", "Konut Finansmanı", null];

  it("terimler farklı alanlara dağılabilir", () => {
    assert.ok(alanlarEslesiyorMu(alanlar, ["kuveyt", "konut"]));
  });

  it("hiçbir alanda geçmeyen terim eşleşmeyi düşürür", () => {
    assert.ok(!alanlarEslesiyorMu(alanlar, ["kuveyt", "tasit"]));
  });

  it("alan sınırında OLMAYAN kelime uydurmaz", () => {
    // Alanları birleştirip aramak 'türkkonut' gibi bir dizi üretirdi.
    assert.ok(!alanlarEslesiyorMu(alanlar, ["turkkonut"]));
  });

  it("boş/eksik alanlar çökertmez", () => {
    assert.ok(!alanlarEslesiyorMu([null, undefined, ""], ["konut"]));
  });
});

describe("vurgulariBul", () => {
  it("özgün yazımı korur (katlama uzunluk korumaz)", () => {
    const metin = "Kampanyada kâr payı oranı düşüktür.";
    const vurgular = vurgulariBul(metin, ["kar payi"]);
    const vurgulu = vurgular
      .filter((p) => p.vurgulu)
      .map((p) => metin.slice(p.bas, p.son));
    assert.deepEqual(vurgulu, ["kâr payı"]);
  });

  it("büyük harfli metinde diakritiksiz terimi bulur", () => {
    const metin = "İHTİYAÇ FİNANSMANI";
    const vurgular = vurgulariBul(metin, ["ihtiyac"]);
    assert.deepEqual(
      vurgular.filter((p) => p.vurgulu).map((p) => metin.slice(p.bas, p.son)),
      ["İHTİYAÇ"],
    );
  });

  it("aynı terimin her geçişi vurgulanır", () => {
    const metin = "konut, konut ve yine konut";
    assert.equal(vurgulariBul(metin, ["konut"]).filter((p) => p.vurgulu).length, 3);
  });

  it("örtüşen terimler tek aralığa iner", () => {
    const metin = "finansmanı";
    const vurgular = vurgulariBul(metin, ["finans", "finansmani"]);
    assert.equal(vurgular.filter((p) => p.vurgulu).length, 1);
  });

  it("metin KAYIPSIZ yeniden kurulur", () => {
    for (const metin of [
      "Kampanyada kâr payı oranı %2,05.",
      "İHTİYAÇ FİNANSMANI",
      "eşleşme yok",
      "",
    ]) {
      assert.equal(yenidenKur(metin, ["kar", "ihtiyac"]), metin);
    }
  });

  it("eşleşme yoksa tek vurgusuz parça", () => {
    assert.deepEqual(vurgulariBul("Kuveyt Türk", ["tasit"]), [
      { bas: 0, son: 11, vurgulu: false },
    ]);
  });

  it("terimsizken hiçbir şey vurgulanmaz", () => {
    assert.deepEqual(vurgulariBul("Kuveyt Türk", []), [
      { bas: 0, son: 11, vurgulu: false },
    ]);
  });
});

describe("alanEtiketi", () => {
  it("sunucunun sütun adını Türkçe etikete çevirir", () => {
    assert.equal(alanEtiketi("ozet"), "özet");
    assert.equal(alanEtiketi("campaign_type"), "kampanya türü");
    assert.equal(alanEtiketi("bank_name"), "banka");
    assert.equal(alanEtiketi("source_url"), "adres");
  });

  it("bilinmeyen alan için etiket UYDURMAZ", () => {
    // Sütun adını olduğu gibi basmak, ekrana iç bir ad sızdırmak olurdu.
    assert.equal(alanEtiketi("bilinmeyen_sutun"), "");
  });
});
