"use client";

/**
 * Sohbet oturumu — tarayıcıda yaşayan sohbet hafızası.
 *
 * İlgili: ../components/ChatPanel.tsx, ./api.ts, ./juryMode.tsx (aynı
 *         hidrasyon deseni), src/chatbot/router.py (bağlamın izin listesi)
 *
 * ## Neden istemcide
 *
 * Sunucu bilerek DURUMSUZ bırakıldı. İki somut sebep:
 *
 *  1. Demo tek kullanıcılı değil. Sunucuda oturum tutmak, jüri üyesinin
 *     ikinci sekmesinin (ya da yan masadaki ikinci tarayıcının) birinin
 *     bağlamını devralması demektir.
 *  2. Sunucu yeniden başlatıldığında sunucudaki oturum kaybolur. Yerel LLM'li
 *     bir demoda yeniden başlatma sık olur. İstemcideki hafıza ise sayfa
 *     yenilemesine bile dayanır — kullanıcının asıl şikâyeti buydu.
 *
 * ## Kapsam: İKİ göz, adlandırma YOK
 *
 * Depo iki sohbet tutar: yürüyen sohbet ve ondan bir önceki. Sınırsız,
 * adlandırılmış oturum listesi (sol kenarda sohbet dizini, yeniden adlandırma,
 * tek tek silme) BİLEREK yapılmadı; maliyeti bir kenar çubuğu, ad düzenleme
 * akışı ve oturum başına kota yönetimi, faydası ise tek akışlı kısa bir
 * sunumda sıfıra yakın.
 *
 * İki göz ise üç ihtiyacın üçünü birden karşılıyor:
 *
 *  1. Sohbet sayfa yenilemesinde KAYBOLMASIN.
 *  2. «Yeni sohbet» temiz bir sayfa açsın — bağlam devralması da sıfırlansın.
 *  3. Yeni sohbet açmak, eskisini YOK ETMESİN. Eski sohbet, kullanıcı onu
 *     açıkça temizleyene kadar ikinci gözde bekler ve geri alınabilir.
 *
 * Üçüncü madde, «Yeni sohbet»i geri alınamaz bir silme olmaktan çıkarır.
 * Geri alınamaz olan tek işlem `temizle()`'dir ve arayüz onu onaya bağlar.
 *
 * ## Kayıt biçimi neden sürüm ATLAMADI
 *
 * İkinci göz kayda İSTEĞE BAĞLI bir alan olarak eklendi (`onceki`), yani eski
 * kayıt yeni kodda eksiksiz okunur ve ikinci gözü boş olan yeni kayıt eski
 * kodda da okunur. Şekil hem geriye hem ileriye uyumlu olduğu için sürüm
 * numarasını artırmak, hiçbir uyumsuzluğu engellemeden herkesin sohbetini
 * silmek olurdu.
 *
 * ## Hidrasyon
 *
 * Sunucu ve ilk istemci render'ı AYNI olmak zorundadır (Next.js sunucuda
 * render ediyor). Bu yüzden `oku()` render sırasında DEĞİL, `useEffect`
 * içinde çağrılır ve başlangıç değeri her zaman boş listedir — `juryMode.tsx`
 * ile birebir aynı desen.
 */

import type { ChatContext, ChatResp } from "./api";

const KAYIT_ANAHTARI = "anatolia.sohbet";

/** Kayıt biçimi sürümü. Değişirse eski kayıt sessizce atılır, çökmez. */
const SURUM = 1;

/**
 * Saklanan AZAMİ tur sayısı.
 *
 * Sınır depolama kotası için var: RAG kaynakları belgenin TAM metnini taşır
 * (korpusta ortalama 4.744 karakter, en uzunu 178.825) ve sınırsız bir
 * geçmiş `localStorage`'ın 5 MB'lık kotasını doldurur.
 */
export const AZAMI_TUR = 12;

/**
 * Sunucuya gönderilen AZAMİ bağlam kaydı.
 *
 * Sunucu da kendi sınırını uygular (`router.BAGLAM_TUR_SINIRI`); buradaki
 * sınır ağ yükü içindir. Üç tur, ölçülen takip sorusu kalıplarının tamamını
 * ("peki vade?", "peki ya X bankası?", "ya konut için?") karşılıyor.
 */
export const BAGLAM_PENCERESI = 3;

/** Ekranda duran tek bir soru-cevap turu. */
export type Tur = {
  id: number;
  soru: string;
  cevap: ChatResp | null;
  hata: unknown;
};

/** Kayda yazılan tur — bekleyen/hatalı turlar buraya hiç girmez. */
type KayitliTur = { id: number; soru: string; cevap: ChatResp };

type Kayit = {
  v: number;
  /** Yürüyen sohbet. */
  turlar: KayitliTur[];
  /** Bir önceki sohbet. Yoksa alan hiç yazılmaz (bkz. dosya başlığı). */
  onceki?: KayitliTur[];
};

function depo(): Storage | null {
  try {
    // Sunucuda (SSR) `window` yoktur; gizli sekmede erişim atabilir.
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

/**
 * Kayıttan gelen turu doğrular.
 *
 * `localStorage` kullanıcının (ve aynı kaynaktaki her betiğin) yazabildiği
 * bir alandır; buradan gelen veri GÜVENİLMEZ kabul edilir. Şekli bozuk kayıt
 * atılır — ama bu sadece arayüzün çökmemesi içindir: bağlamın asıl güvenlik
 * denetimi sunucuda, izin listesiyle yapılır (src/chatbot/router.py).
 */
function turGecerli(x: unknown): x is { id: number; soru: string; cevap: ChatResp } {
  if (!x || typeof x !== "object") return false;
  const t = x as Record<string, unknown>;
  if (typeof t.soru !== "string" || !t.soru) return false;
  if (typeof t.id !== "number" || !Number.isFinite(t.id)) return false;
  const c = t.cevap as Record<string, unknown> | undefined;
  if (!c || typeof c !== "object") return false;
  if (typeof c.answer !== "string") return false;
  return Array.isArray(c.sources);
}

/** Ham kaydı çözer. Kayıt yoksa/bozuksa/tanınmayan sürümdeyse `null`. */
function kaydiCoz(): Kayit | null {
  const d = depo();
  if (!d) return null;
  let ham: string | null;
  try {
    ham = d.getItem(KAYIT_ANAHTARI);
  } catch {
    return null;
  }
  if (!ham) return null;
  try {
    const kayit = JSON.parse(ham) as Kayit;
    if (!kayit || kayit.v !== SURUM || !Array.isArray(kayit.turlar)) return null;
    return kayit;
  } catch {
    return null;
  }
}

/** Kayıttan gelen ham listeyi ekranda kullanılabilir turlara çevirir. */
function turleriCoz(ham: unknown): Tur[] {
  if (!Array.isArray(ham)) return [];
  return ham
    .filter(turGecerli)
    .slice(-AZAMI_TUR)
    .map((t) => ({ id: t.id, soru: t.soru, cevap: t.cevap, hata: null }));
}

/** Yürüyen sohbeti okur. Kayıt yoksa/bozuksa boş liste (hata değil). */
export function oku(): Tur[] {
  return turleriCoz(kaydiCoz()?.turlar);
}

/**
 * Bir önceki sohbeti okur — «Yeni sohbet» ile kenara alınan turlar.
 *
 * Eski kayıtlarda bu alan hiç yoktur ve bu bir hata değildir: o kayıt, ikinci
 * gözün eklenmesinden önce yazılmıştır ve boş bir önceki sohbetle okunur.
 */
export function okuOnceki(): Tur[] {
  return turleriCoz(kaydiCoz()?.onceki);
}

/** Ekran turlarını kayıt turlarına indirger (cevabı olmayanlar düşer). */
function saklanabilir(turlar: Tur[]): KayitliTur[] {
  return turlar
    .filter((t) => t.cevap)
    .slice(-AZAMI_TUR)
    .map((t) => ({ id: t.id, soru: t.soru, cevap: t.cevap as ChatResp }));
}

/**
 * Sohbeti saklar. Yalnız CEVABI OLAN turlar yazılır.
 *
 * Bekleyen tur yazılmaz (sayfa yenilenince sonsuza dek «yükleniyor» kalırdı);
 * hatalı tur da yazılmaz (`Error` nesnesi JSON'a düzgün serileşmez ve
 * yenilemeden sonra bir hatayı yeniden göstermek bilgi taşımaz).
 *
 * `onceki` VERİLMEZSE kayıttaki ikinci göze dokunulmaz. Bu, her tur sonrası
 * koşan sıradan yazmanın kenara alınmış sohbeti sessizce silmesini önler;
 * ikinci göz yalnız onu açıkça değiştiren işlemlerde (yeni sohbet, geri dönme,
 * temizleme) yazılır.
 *
 * Kota dolduğunda (`QuotaExceededError`) yazma BAŞARISIZ olmaz. Feda sırası
 * bilinçlidir: ÖNCE ikinci göz atılır, sonra yürüyen sohbetin yarısı. Kenara
 * alınmış sohbet kullanıcının bakmadığı sohbettir; yürüyen sohbeti onun için
 * kırpmak yanlış tarafı korumak olurdu. Kaynak metinlerini kırpmak ise hiç
 * seçenek değil — denetlenebilirlik kotaya feda edilmez.
 */
export function yaz(turlar: Tur[], onceki?: Tur[]): void {
  const d = depo();
  if (!d) return;
  let liste = saklanabilir(turlar);
  let arsiv =
    onceki === undefined ? (kaydiCoz()?.onceki ?? []) : saklanabilir(onceki);

  for (;;) {
    const kayit: Kayit = { v: SURUM, turlar: liste };
    if (arsiv.length) kayit.onceki = arsiv;
    try {
      d.setItem(KAYIT_ANAHTARI, JSON.stringify(kayit));
      return;
    } catch {
      if (arsiv.length) {
        arsiv = [];
        continue;
      }
      if (liste.length <= 1) {
        try {
          d.removeItem(KAYIT_ANAHTARI);
        } catch {
          /* depo tümüyle yazılamıyor — sohbet yalnız bu sekmede yaşar */
        }
        return;
      }
      liste = liste.slice(Math.ceil(liste.length / 2));
    }
  }
}

/**
 * HER İKİ sohbeti de siler («Sohbeti temizle»).
 *
 * Geri alınamaz olan tek işlem budur; arayüz bu yüzden onay ister. «Yeni
 * sohbet» buraya uğramaz — o yalnız yürüyen sohbeti ikinci göze taşır.
 */
export function temizle(): void {
  const d = depo();
  if (!d) return;
  try {
    d.removeItem(KAYIT_ANAHTARI);
  } catch {
    /* silinemedi — bellekteki liste yine de sıfırlandı */
  }
}

/**
 * Sunucuya gönderilecek bağlam listesi — YENİDEN ESKİYE sıralı.
 *
 * Yalnız gerçekten durum taşıyan turlar girer: bağlamı boş bir tur (ör.
 * güvenlik kapısının durdurduğu bir soru) listeye eklenirse sunucu tarafında
 * hiçbir işe yaramaz, sadece istek gövdesini şişirir.
 */
export function baglamListesi(
  turlar: Tur[],
  pencere: number = BAGLAM_PENCERESI,
): ChatContext[] {
  const out: ChatContext[] = [];
  for (let i = turlar.length - 1; i >= 0 && out.length < pencere; i -= 1) {
    const c = turlar[i].cevap?.context;
    if (!c) continue;
    const dolu =
      c.field ||
      c.intent ||
      (c.subject_banks && c.subject_banks.length) ||
      (c.filters && Object.keys(c.filters).length);
    if (dolu) out.push(c);
  }
  return out;
}

/**
 * Kayıttan gelen turlardan sonra kullanılacak ilk tur kimliği.
 *
 * Çağıran HER İKİ gözü birleştirip verir: kullanıcı önceki sohbete geri
 * döndüğünde o turlar yeniden ekrana gelir ve kimlikleri React listesinde
 * anahtar olarak kullanılır; yalnız yürüyen sohbete bakan bir sayaç, geri
 * dönüşten sonra çakışan kimlik üretirdi.
 */
export function sonrakiKimlik(turlar: Tur[]): number {
  return turlar.reduce((en, t) => Math.max(en, t.id), 0) + 1;
}
