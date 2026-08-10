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
 * ## Kapsam: TEK oturum, adlandırma YOK
 *
 * Birden çok adlandırılmış oturum (sol kenarda sohbet listesi, yeniden
 * adlandırma, silme) BİLEREK yapılmadı. Maliyeti bir kenar çubuğu, ad
 * düzenleme akışı ve oturum başına depolama kotası yönetimi; faydası ise
 * 4 dakikalık tek akışlı bir sunumda sıfıra yakın. Kullanıcının gerçek
 * ihtiyacı iki tanedir ve ikisi de karşılanır: sohbet yenilemede
 * KAYBOLMASIN, ve istendiğinde TEMİZLENEBİLSİN («Yeni sohbet»).
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

type Kayit = {
  v: number;
  turlar: { id: number; soru: string; cevap: ChatResp }[];
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

/** Saklanan sohbeti okur. Kayıt yoksa/bozuksa boş liste (hata değil). */
export function oku(): Tur[] {
  const d = depo();
  if (!d) return [];
  let ham: string | null;
  try {
    ham = d.getItem(KAYIT_ANAHTARI);
  } catch {
    return [];
  }
  if (!ham) return [];
  try {
    const kayit = JSON.parse(ham) as Kayit;
    if (!kayit || kayit.v !== SURUM || !Array.isArray(kayit.turlar)) return [];
    return kayit.turlar
      .filter(turGecerli)
      .slice(-AZAMI_TUR)
      .map((t) => ({ id: t.id, soru: t.soru, cevap: t.cevap, hata: null }));
  } catch {
    return [];
  }
}

/**
 * Sohbeti saklar. Yalnız CEVABI OLAN turlar yazılır.
 *
 * Bekleyen tur yazılmaz (sayfa yenilenince sonsuza dek «yükleniyor» kalırdı);
 * hatalı tur da yazılmaz (`Error` nesnesi JSON'a düzgün serileşmez ve
 * yenilemeden sonra bir hatayı yeniden göstermek bilgi taşımaz).
 *
 * Kota dolduğunda (`QuotaExceededError`) yazma BAŞARISIZ olmaz: geçmişin
 * yarısı atılıp yeniden denenir. Alternatif — kaynak metinlerini kırpmak —
 * denetlenebilirliği bozardı; eski turu tamamen unutmak, yeni turun kaynağını
 * sakatlamaktan iyidir.
 */
export function yaz(turlar: Tur[]): void {
  const d = depo();
  if (!d) return;
  let liste = turlar
    .filter((t) => t.cevap)
    .slice(-AZAMI_TUR)
    .map((t) => ({ id: t.id, soru: t.soru, cevap: t.cevap as ChatResp }));

  for (;;) {
    try {
      d.setItem(KAYIT_ANAHTARI, JSON.stringify({ v: SURUM, turlar: liste }));
      return;
    } catch {
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

/** Saklanan sohbeti siler («Yeni sohbet»). */
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

/** Kayıttan gelen turlardan sonra kullanılacak ilk tur kimliği. */
export function sonrakiKimlik(turlar: Tur[]): number {
  return turlar.reduce((en, t) => Math.max(en, t.id), 0) + 1;
}
