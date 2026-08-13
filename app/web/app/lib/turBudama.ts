/**
 * Kampanya türü süzgecinin ALANA GÖRE budanması — saf çekirdek.
 *
 * İlgili: `components/ComparePanel.tsx` (tek çağıran),
 *         `docs/superpowers/specs/2026-08-13-kiyas-suzgeci-ve-yildiz-kirilimi-design.md` (A)
 *
 * ## NEDEN AYRI DOSYA
 *
 * Bu üç fonksiyonun doğal yeri `ComparePanel.tsx`'ti; tasarım belgesinin
 * «dokunulacak dosyalar» tablosu da orayı yazıyor. Ayrılmalarının tek nedeni
 * ÖLÇÜLEBİLİRLİK: testler `node --test` ile koşuyor ve Node'un tip sıyırması
 * JSX'i çeviremiyor (`ERR_UNKNOWN_FILE_EXTENSION` — `.tsx` içe alınamıyor,
 * ölçüldü 2026-08-13). Budama kararının doğruluğu — hangi tür düştü, seçili tür
 * ne zaman geri alınır, ölçemediğimizde ne olur — bu ekranın en kolay sessizce
 * bozulan parçası; React render testi kurmak yerine karar saf tutuldu, bileşen
 * yalnız onu çağırıyor.
 *
 * ## NEDEN BUDAMA
 *
 * Süzgeç, `stats.campaign_types`ten gelen 8 türün tamamını her alan için
 * basıyordu; oysa tür kapsaması alandan alana değişiyor (ölçüldü 2026-08-13,
 * `data/demo.db`, 1.774 belge): `kar_payi_orani` 7 tür, `tahsis_ucreti` yalnız
 * 4. `tahsis_ucreti` + `Finansman` seçen kullanıcı boş bir ekran ve «veri mi
 * yok, sistem mi bozuk» sorusuyla kalıyordu.
 *
 * ## BUDAMA SESSİZ DEĞİL
 *
 * Bu ekranın doktrini «boşluğu gizleme, say». Reddedilen seçenek — türü görünür
 * ama pasif bırakmak — doktrine daha sadikti ama istenen sadeleşmeyi vermiyordu;
 * doktrin bunun yerine `dusen` listesiyle korunuyor: düşen türler süzgecin
 * altında ADIYLA sayılır. `dusenTurler` bu yüzden var ve bu yüzden ad döndürür,
 * sayı değil.
 *
 * ## ÖLÇEMEDİĞİMİZDE BUDAMA YOK
 *
 * `turSecenekleri` yükleniyor ya da hata hâlinde TAM listeyi döndürür ve
 * `budandi: false` der. Ölçülemeyen bir yokluğu yokluk gibi göstermek, bu
 * ekranın reddettiği hatanın ta kendisi: yanıt gelmediği için boş görünen bir
 * küme, «bu alanda o tür yok» demek DEĞİLDİR.
 *
 * Boş dizi (`data: []`) bunun tersidir — o bir ÖLÇÜMDÜR: sunucu yanıt verdi ve
 * bu alanda hiçbir tür değer taşımıyor. O hâlde budama yapılır, sekiz türün
 * sekizi düşen listesinde adıyla yazılır.
 */

import type { CompareRow } from "./api";

/**
 * Yanıt satırlarında GERÇEKTEN geçen kampanya türleri.
 *
 * `campaign_type` boş ya da `null` gelen satırlar kümeye girmez: tabloda
 * «Türü belirlenemedi» bölümü olarak durur ama bir SÜZGEÇ seçeneği değildir —
 * süzgeç `campaign_types` kataloğunun 8 sınıfından seçim yapar.
 */
export function mevcutTurler(rows: CompareRow[]): Set<string> {
  const kume = new Set<string>();
  for (const row of rows) {
    const tur = row.campaign_type?.trim();
    if (tur) kume.add(tur);
  }
  return kume;
}

/**
 * Süzgece basılacak liste: kanonik sıra KORUNARAK süzülür.
 *
 * Sıra yanıttan yeniden üretilmez. `/compare` satırları sıralama ölçütüne göre
 * gelir; kümeyi oradan kursak süzgecin seçenek sırası alan ya da sıralama
 * değiştikçe oynardı — kullanıcı iki tıklama arasında listenin yerini
 * kaybederdi. Kanonik sıra `campaignTypes` propunun sırasıdır (`/stats`).
 */
export function budanmisListe(
  kanonik: readonly string[],
  mevcut: ReadonlySet<string>,
): string[] {
  return kanonik.filter((t) => mevcut.has(t));
}

/** Kanonik listede olup bu alanda veri taşımayan türler — adıyla, sırasıyla. */
export function dusenTurler(
  kanonik: readonly string[],
  mevcut: ReadonlySet<string>,
): string[] {
  return kanonik.filter((t) => !mevcut.has(t));
}

export type TurSecenekleri = {
  /** Süzgeçte basılacak türler (kanonik sırada). */
  liste: string[];
  /** Budanan türler (kanonik sırada); boşsa satır hiç basılmaz. */
  dusen: string[];
  /**
   * Budama UYGULANDI mı. `false` iken `liste` tam kanonik listedir ve seçili
   * tür asla geri alınmaz — ölçemediğimiz bir şey yüzünden kullanıcının
   * seçimini bozmak, yokluk uydurmakla aynı şey.
   */
  budandi: boolean;
};

/**
 * Süzgeç durumunu tek yerde hesaplar.
 *
 * `kaynak` bilinçli olarak `useAsync`'in döndürdüğü şeklin ta kendisidir
 * (`{ data, loading, error }`) — bileşen bu üçlüyü parçalayıp yeniden kurmasın;
 * «hata hâlinde budama yok» kuralı çağıranın disiplinine bırakılmaz.
 */
export function turSecenekleri(
  kanonik: readonly string[],
  kaynak: { data: CompareRow[] | null; loading: boolean; error: unknown },
): TurSecenekleri {
  if (kaynak.loading || kaynak.error || !kaynak.data) {
    return { liste: [...kanonik], dusen: [], budandi: false };
  }
  const mevcut = mevcutTurler(kaynak.data);
  return {
    liste: budanmisListe(kanonik, mevcut),
    dusen: dusenTurler(kanonik, mevcut),
    budandi: true,
  };
}
