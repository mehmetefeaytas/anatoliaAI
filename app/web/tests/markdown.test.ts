/**
 * Markdown alt kümesi ayrıştırıcısının testleri.
 *
 * Koşum: `npm run test` (web/) — Node'un YERLEŞİK test koşucusu ve tip
 * sıyırması kullanılır. Yeni bağımlılık YOKTUR: `node:test` ve `node:assert`
 * standart kütüphanededir, `.ts` dosyası Node 22.6+ tarafından doğrudan
 * çalıştırılır (offline kısıtı + lisans denetimi, CLAUDE.md §1/§20).
 *
 * Bu testlerin ağırlığı iki yerde:
 *   1. ALAN ADI BOZULMAMALI — `kar_payi_orani` içindeki alt çizgiler italik
 *      sanılırsa chatbot cevabındaki alan adı görünür biçimde bozulur.
 *   2. TANINMAYAN İŞARET YUTULMAMALI — kapanmamış bir `**`, sunucunun gerçekte
 *      ne gönderdiğini gizlememelidir.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  markdownAyristir,
  satirAyristir,
  type Inline,
} from "../app/lib/markdown.ts";

/** Test okunurluğu için kısa kurucular. */
const t = (icerik: string): Inline => ({ tur: "text", icerik });
const b = (icerik: string): Inline => ({ tur: "strong", icerik });
const i = (icerik: string): Inline => ({ tur: "em", icerik });
const c = (icerik: string): Inline => ({ tur: "code", icerik });

describe("satirAyristir — kalın", () => {
  it("sunucunun ürettiği gerçek cevabı çözer", () => {
    // src/chatbot/structured.py:125 bu biçimi üretiyor.
    assert.deepEqual(
      satirAyristir("en düşük kâr payı oranı: **Kuveyt Türk** (%1,79)."),
      [t("en düşük kâr payı oranı: "), b("Kuveyt Türk"), t(" (%1,79).")],
    );
  });

  it("aynı satırda birden çok kalın", () => {
    assert.deepEqual(satirAyristir("**a** ve **b**"), [
      b("a"),
      t(" ve "),
      b("b"),
    ]);
  });

  it("kapanmamış yıldızlar BİREBİR basılır", () => {
    assert.deepEqual(satirAyristir("**yarım kalmış"), [t("**yarım kalmış")]);
  });

  it("boş işaretçi düz metindir", () => {
    assert.deepEqual(satirAyristir("****"), [t("****")]);
  });

  it("kenarında boşluk olan işaretçi markdown DEĞİLDİR", () => {
    assert.deepEqual(satirAyristir("** x **"), [t("** x **")]);
  });

  it("çarpma işareti kalın sanılmaz", () => {
    // safety.py'nin türev oran metinlerinde `* 0,05` geçebiliyor.
    assert.deepEqual(satirAyristir("oran * 0,05 kadar"), [
      t("oran * 0,05 kadar"),
    ]);
  });
});

describe("satirAyristir — italik ve alan adları", () => {
  it("sunucunun not biçimini çözer", () => {
    // structured.py:136 → `_(not: …)_`
    assert.deepEqual(satirAyristir("_(not: aralık)_"), [i("(not: aralık)")]);
  });

  it("ALAN ADINI BOZMAZ — alt çizgiler sözcük içinde", () => {
    assert.deepEqual(satirAyristir("kar_payi_orani alanı"), [
      t("kar_payi_orani alanı"),
    ]);
  });

  it("iki alan adı yan yana da bozulmaz", () => {
    assert.deepEqual(satirAyristir("vade_ay ve taksit_sayisi"), [
      t("vade_ay ve taksit_sayisi"),
    ]);
  });

  it("kapanmamış alt çizgi birebir basılır", () => {
    assert.deepEqual(satirAyristir("_yarım"), [t("_yarım")]);
  });
});

describe("satirAyristir — kod", () => {
  it("ters tırnak arası kod olur", () => {
    assert.deepEqual(satirAyristir("alan `vade_ay` sayıdır"), [
      t("alan "),
      c("vade_ay"),
      t(" sayıdır"),
    ]);
  });

  it("kod içindeki alt çizgi ve yıldız YORUMLANMAZ", () => {
    assert.deepEqual(satirAyristir("`a_b_c **d**`"), [c("a_b_c **d**")]);
  });

  it("boş ters tırnak çifti düz metindir", () => {
    assert.deepEqual(satirAyristir("``"), [t("``")]);
  });
});

describe("markdownAyristir — bloklar", () => {
  it("ardışık tire satırları TEK listeye toplanır", () => {
    const bloklar = markdownAyristir("Başlık:\n- Kuveyt Türk: %1,79\n- Vakıf: %2,10");
    assert.equal(bloklar.length, 2);
    assert.deepEqual(bloklar[0], { tur: "p", satirlar: [[t("Başlık:")]] });
    assert.equal(bloklar[1].tur, "ul");
    assert.equal(bloklar[1].tur === "ul" ? bloklar[1].ogeler.length : 0, 2);
  });

  it("liste öğesi içinde kalın çalışır", () => {
    const bloklar = markdownAyristir("- **Kuveyt Türk**: %1,79");
    assert.deepEqual(bloklar, [
      { tur: "ul", ogeler: [[b("Kuveyt Türk"), t(": %1,79")]] },
    ]);
  });

  it("boş satır paragrafı böler", () => {
    const bloklar = markdownAyristir("bir\n\niki");
    assert.equal(bloklar.length, 2);
  });

  it("paragraf içindeki tek satır sonu KORUNUR", () => {
    // Eski arayüz `white-space: pre-wrap` ile bunu koruyordu; kaybedilmemeli.
    assert.deepEqual(markdownAyristir("bir\niki"), [
      { tur: "p", satirlar: [[t("bir")], [t("iki")]] },
    ]);
  });

  it("liste bitince paragraf yeniden açılır", () => {
    const bloklar = markdownAyristir("- a\nson söz");
    assert.deepEqual(
      bloklar.map((x) => x.tur),
      ["ul", "p"],
    );
  });

  it("boş metin blok üretmez", () => {
    assert.deepEqual(markdownAyristir(""), []);
    assert.deepEqual(markdownAyristir("   \n  \n"), []);
  });

  it("CRLF satır sonu da çözülür", () => {
    assert.deepEqual(
      markdownAyristir("bir\r\n\r\niki").map((x) => x.tur),
      ["p", "p"],
    );
  });
});

describe("kayıp yok garantisi", () => {
  /** Parçaların metnini birleştirince ham satır geri gelmeli. */
  function geriBirlestir(parcalar: Inline[]): string {
    return parcalar
      .map((p) => {
        if (p.tur === "strong") return `**${p.icerik}**`;
        if (p.tur === "em") return `_${p.icerik}_`;
        if (p.tur === "code") return `\`${p.icerik}\``;
        return p.icerik;
      })
      .join("");
  }

  it("ayrıştırma HİÇBİR karakteri düşürmez", () => {
    const ornekler = [
      "en düşük kâr payı oranı: **Kuveyt Türk** (%1,79).",
      "_(not: aralık)_ ve kar_payi_orani",
      "**a**_b_`c`",
      "** bozuk ** _bozuk_ok",
      "hiç işaret yok",
    ];
    for (const ham of ornekler) {
      assert.equal(geriBirlestir(satirAyristir(ham)), ham, `kayıp: ${ham}`);
    }
  });
});
