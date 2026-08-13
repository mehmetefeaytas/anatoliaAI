/**
 * Kampanya türü süzgecinin alana göre budanmasının testleri.
 *
 * Koşum: `npm run test` (web/) — Node'un YERLEŞİK test koşucusu ve tip
 * sıyırması. Yeni bağımlılık YOKTUR (offline kısıtı + lisans denetimi).
 *
 * Bu testlerin ağırlığı dört yerde:
 *
 *  1. **DÜŞEN TÜR LİSTESİ DOĞRU OLMALI.** Budama sessiz değil: süzgecin altında
 *     düşen türler ADIYLA sayılıyor. O satır yanlışsa arayüz kullanıcıya
 *     ölçmediği bir yokluğu bildirmiş olur — budamanın kendisinden daha kötü.
 *  2. **KANONİK SIRA KORUNMALI.** Liste `campaignTypes` sırasından süzülür,
 *     `/compare` yanıtından yeniden üretilmez. Yanıt sıralama ölçütüne göre
 *     gelir; kümeyi oradan kursak süzgecin seçenek sırası her alan/sıralama
 *     değişiminde oynardı.
 *  3. **SEÇİLİ TÜR DÜŞERSE «TÜMÜ»YE DÖNÜLMELİ.** Boş ekran yerine geri alınmış
 *     bir seçim + bir cümle. Testte bileşen render edilmiyor; geri alma
 *     KOŞULU (`budandi && !liste.includes(type)`) saf hâlde ölçülüyor.
 *  4. **ÖLÇEMEDİĞİMİZDE BUDAMA YOK.** Yükleniyor ya da hata hâlinde tam liste
 *     basılır ve seçim korunur. Yanıt gelmediği için boş görünen bir küme «o
 *     tür bu alanda yok» demek DEĞİLDİR.
 *
 * Hiçbir test ağa çıkmaz: yardımcılar saf, girdileri elden yazılmış satırlar.
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";

import type { CompareRow } from "../app/lib/api.ts";
import {
  budanmisListe,
  dusenTurler,
  mevcutTurler,
  turSecenekleri,
} from "../app/lib/turBudama.ts";

/** `/stats` → `campaign_types` kanonik sırası (8 sınıf, CLAUDE.md §12). */
const KANONIK = [
  "Finansman",
  "İhtiyaç Finansmanı",
  "Konut Finansmanı",
  "Taşıt Finansmanı",
  "Kart",
  "Alışveriş Puanı",
  "Yeni Müşteri",
  "Yatırım Ürünü",
];

function satir(ek: Partial<CompareRow> = {}): CompareRow {
  return {
    bank: "ornek-katilim",
    bank_name: "Örnek Katılım",
    value: 2.05,
    comparable: true,
    note: null,
    campaign_status: null,
    source_span: null,
    campaign_id: 1,
    campaign_type: "Kart",
    source_url: null,
    raw_value: "%2,05",
    confidence: 0.9,
    confidence_source: "rule_heuristic",
    extractor: "rule",
    sort_key: 2.05,
    rank: 1,
    contradiction_count: 0,
    other_count: 0,
    span_start: null,
    span_end: null,
    span_scope: null,
    span_verified: false,
    span_ambiguous: false,
    window_start: null,
    window_end: null,
    ...ek,
  };
}

/** Türleri verilen satır kümesi. */
function turlerle(...turler: (string | null)[]): CompareRow[] {
  return turler.map((t, i) => satir({ campaign_type: t, campaign_id: i + 1 }));
}

/** `useAsync` şeklinde başarılı yanıt. */
function geldi(rows: CompareRow[]) {
  return { data: rows, loading: false, error: null };
}

describe("mevcutTurler", () => {
  it("yanıttaki tekrarsız türleri toplar", () => {
    const kume = mevcutTurler(turlerle("Kart", "Kart", "Konut Finansmanı"));
    assert.deepEqual([...kume].sort(), ["Kart", "Konut Finansmanı"]);
  });

  it("türü olmayan satır bir SEÇENEK üretmez", () => {
    // Tabloda «Türü belirlenemedi» bölümü olarak durur ama süzgeç kataloğun
    // 8 sınıfından seçim yapar; boş dizeyi seçenek yapmak sahte bir tür icat
    // etmek olurdu.
    const kume = mevcutTurler(turlerle("Kart", null, "", "   "));
    assert.deepEqual([...kume], ["Kart"]);
  });

  it("boş yanıt boş küme", () => {
    assert.equal(mevcutTurler([]).size, 0);
  });
});

describe("budanmisListe — kanonik sıra korunur", () => {
  it("yanıtın sırası DEĞİL, kataloğun sırası basılır", () => {
    // Yanıt sıralama ölçütüne göre geldi: Kart önce, Finansman sonra.
    const kaynak = mevcutTurler(turlerle("Kart", "Finansman", "Yeni Müşteri"));
    assert.deepEqual(budanmisListe(KANONIK, kaynak), [
      "Finansman",
      "Kart",
      "Yeni Müşteri",
    ]);
  });

  it("katalogda olmayan tür listeye SIZMAZ", () => {
    // Sunucu bir gün yeni bir sınıf döndürürse süzgeç onu uydurmaz; kaynak tek
    // doğruluk kaynağı olarak `campaignTypes` propudur.
    const kaynak = mevcutTurler(turlerle("Kart", "Sigorta"));
    assert.deepEqual(budanmisListe(KANONIK, kaynak), ["Kart"]);
  });
});

describe("dusenTurler", () => {
  it("ölçülen örnek: tahsis_ucreti — 4 tür düşer", () => {
    // Ölçüldü 2026-08-13, `data/demo.db`, 1.774 belge: `tahsis_ucreti` alanında
    // yalnız 4 tür veri taşıyor.
    const kaynak = mevcutTurler(
      turlerle("Konut Finansmanı", "Taşıt Finansmanı", "Kart", "Yatırım Ürünü"),
    );
    assert.deepEqual(dusenTurler(KANONIK, kaynak), [
      "Finansman",
      "İhtiyaç Finansmanı",
      "Alışveriş Puanı",
      "Yeni Müşteri",
    ]);
  });

  it("ölçülen örnek: alisveris_puani — hiç tür düşmez", () => {
    const kaynak = mevcutTurler(turlerle(...KANONIK));
    assert.deepEqual(dusenTurler(KANONIK, kaynak), []);
    // Satır yalnız `dusen.length > 0` iken basılır; «0 tür düştü» bilgi değil
    // gürültüdür.
    assert.equal(turSecenekleri(KANONIK, geldi(turlerle(...KANONIK))).dusen.length, 0);
  });

  it("liste ile düşenler birlikte kataloğu TAM kaplar", () => {
    // Bir tür ya listede ya düşenlerde olmalı; ikisinde de olmayan tür sessizce
    // kaybolmuş demektir.
    const kaynak = mevcutTurler(turlerle("Kart", "Finansman"));
    assert.deepEqual(
      [...budanmisListe(KANONIK, kaynak), ...dusenTurler(KANONIK, kaynak)].sort(),
      [...KANONIK].sort(),
    );
  });
});

describe("turSecenekleri — ölçemediğimizde budama yok", () => {
  it("YÜKLENİYOR: tam liste, hiç düşen yok", () => {
    const s = turSecenekleri(KANONIK, { data: null, loading: true, error: null });
    assert.deepEqual(s.liste, KANONIK);
    assert.deepEqual(s.dusen, []);
    assert.equal(s.budandi, false);
  });

  it("HATA: tam liste basılır — eldeki veri budamaya kullanılmaz", () => {
    // `useAsync` hata hâlinde `data`yı boşaltır; yine de her iki hâl ölçülüyor,
    // çünkü hata bayrağı budamayı TEK BAŞINA kapatmalı.
    for (const data of [null, turlerle("Kart")]) {
      const s = turSecenekleri(KANONIK, {
        data,
        loading: false,
        error: new Error("/compare 500"),
      });
      assert.deepEqual(s.liste, KANONIK);
      assert.deepEqual(s.dusen, []);
      assert.equal(s.budandi, false);
    }
  });

  it("veri gelmedi ve hata da yok: budama YAPILMAZ", () => {
    const s = turSecenekleri(KANONIK, { data: null, loading: false, error: null });
    assert.deepEqual(s.liste, KANONIK);
    assert.equal(s.budandi, false);
  });

  it("dönen liste çağıranın dizisini DEĞİŞTİRMEZ", () => {
    const s = turSecenekleri(KANONIK, { data: null, loading: true, error: null });
    s.liste.push("Sigorta");
    assert.equal(KANONIK.length, 8);
  });

  it("BOŞ YANIT bir ölçümdür: sekiz türün sekizi düşer", () => {
    // Yükleniyor/hata ile karıştırılmaması gereken hâl. Sunucu yanıt verdi ve
    // bu alanda hiçbir tür değer taşımıyor; süzgeçte yalnız «Tümü» kalır ve
    // sekiz tür adıyla sayılır.
    const s = turSecenekleri(KANONIK, geldi([]));
    assert.deepEqual(s.liste, []);
    assert.deepEqual(s.dusen, KANONIK);
    assert.equal(s.budandi, true);
  });
});

/**
 * Bileşenin geri alma koşulu, saf hâlde.
 *
 * `ComparePanel` içindeki etki tam olarak bunu yapıyor:
 * `if (!budandi) return; if (!type || liste.includes(type)) return; setType("")`.
 * Burada React render edilmiyor — ölçülen şey KARARIN kendisi.
 */
function turGeriAlinirMi(s: { liste: string[]; budandi: boolean }, type: string) {
  if (!s.budandi) return false;
  return !!type && !s.liste.includes(type);
}

describe("seçili tür budanınca Tümü'ne dönülür", () => {
  it("veri taşımayan tür seçiliyken geri alınır", () => {
    const s = turSecenekleri(KANONIK, geldi(turlerle("Konut Finansmanı", "Kart")));
    assert.equal(turGeriAlinirMi(s, "Finansman"), true);
  });

  it("veri taşıyan tür seçiliyken DOKUNULMAZ", () => {
    const s = turSecenekleri(KANONIK, geldi(turlerle("Konut Finansmanı", "Kart")));
    assert.equal(turGeriAlinirMi(s, "Kart"), false);
  });

  it("«Tümü» seçiliyken geri alma diye bir şey yok", () => {
    const s = turSecenekleri(KANONIK, geldi(turlerle("Kart")));
    assert.equal(turGeriAlinirMi(s, ""), false);
  });

  it("HATA hâlinde seçim ASLA bozulmaz", () => {
    // Bu, budamanın en pahalı yanlışı olurdu: ölçülemeyen bir yokluk yüzünden
    // kullanıcının seçimini geri almak.
    const s = turSecenekleri(KANONIK, {
      data: null,
      loading: false,
      error: new Error("ağ yok"),
    });
    assert.equal(turGeriAlinirMi(s, "Finansman"), false);
  });

  it("YÜKLENİYOR hâlinde seçim bozulmaz (alan değişiminin ilk turu)", () => {
    const s = turSecenekleri(KANONIK, { data: null, loading: true, error: null });
    assert.equal(turGeriAlinirMi(s, "Finansman"), false);
  });

  it("geri alma bir kez olur: «Tümü» hiçbir hâlde tekrar tetiklemez", () => {
    const s = turSecenekleri(KANONIK, geldi([]));
    assert.equal(turGeriAlinirMi(s, "Kart"), true);
    // setType("") sonrası:
    assert.equal(turGeriAlinirMi(s, ""), false);
  });
});
