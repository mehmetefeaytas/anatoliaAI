/**
 * `GET /api/urun-tablosu` istemcisi ve tipleri — şartname Senaryo-1 tablosu.
 *
 * İlgili: src/api/main.py `/urun-tablosu`
 *         src/comparison/compare.py «Şartname Senaryo-1 tablosu» bloğu
 *         ./UrunTablosuPanel.tsx (tek tüketici)
 *         raw/teknofest/…-sartname-2-senaryo.pdf s.11–12 (tablonun kendisi)
 *
 * ## Neden `lib/api.ts` DEĞİL
 *
 * Doğal yeri `lib/api.ts`tir: `compare` ve `bankDelta` orada duruyor ve bu uç
 * onların kardeşi. Bu dosya yalnızca **çalışma bölüşümü** yüzünden burada —
 * `lib/api.ts` bu değişikliğin sahiplik sınırının dışındaydı. `api.ts` sahibi
 * bunu `api.urunTablosu` olarak oraya taşıdığında bu dosya SİLİNMELİ; iki
 * istemci katmanı kalıcı olursa hata biçimleri zamanla ayrışır.
 *
 * Taşınana kadar tekrar en aza indirildi: hata sınıfı (`ApiError`) ve yol
 * öneki (`/api`) `lib/api.ts` ile aynı; yeniden tanımlanmıyor.
 */

import { ApiError } from "../lib/api";

/**
 * Tablonun tek bir hücresi — değer + KANITI.
 *
 * Avantaj parçaları da aynı şekli kullanır (`parcalar`). Sunucu bunu bilerek
 * böyle yapıyor: bir hücre ile onu oluşturan parçanın farklı şekilleri
 * olsaydı, kaynak rozeti iki ayrı biçimde yazılmak zorunda kalırdı.
 */
export type TabloHucresi = {
  sutun: string;
  /** Hangi çıkarım alanından geldi; türetilmiş kolonlarda `null`. */
  field_name: string | null;
  value: unknown;
  raw_value: string | null;
  confidence: number | null;
  extractor: string | null;
  source_span: string | null;
  span_start: number | null;
  span_end: number | null;
  /**
   * SUNUCUNUN hesabı. İstemcide `value === null` diye yeniden hesaplanmaz:
   * birleşik kolonda değer yoktur ama parçalar olabilir ve iki taraf bu
   * kuralı ayrı ayrı yazarsa er ya da geç ayrışır.
   */
  bos: boolean;
  parcalar: TabloHucresi[];
};

export type TabloSatiri = {
  bank: string | null;
  bank_name: string | null;
  /** Kapsam satırlarında `null` — bankanın bu ailede ölçülmüş alanı yok. */
  campaign_id: number | null;
  campaign_type: string | null;
  campaign_status: string | null;
  /** Bu bankanın aynı ailede GÖSTERİLMEYEN kampanya sayısı. */
  other_count: number;
  cells: Record<string, TabloHucresi>;
};

export type TabloSutunu = {
  key: string;
  /** Şartname s.12'deki başlık, birebir. */
  label: string;
  field_name: string | null;
  /** Doluluk sayacına giriyor mu (türetilmiş kolonlar girmez). */
  olculur: boolean;
};

/** «Bu görünümde X hücrenin Y'si dolu» — sunucuda ÇALIŞMA ANINDA ölçülür. */
export type TabloDolulugu = {
  satir: number;
  olculen_sutun: number;
  hucre: number;
  dolu: number;
  oran: number;
  sutun_basina: Record<string, { dolu: number; toplam: number }>;
  /** Şartnamenin kendi 3×7 ölçüsüyle kıyaslanabilsin diye. */
  tum_sutun: number;
  tum_hucre: number;
  tum_dolu: number;
};

export type UrunTablosu = {
  type: string | null;
  bank: string | null;
  columns: TabloSutunu[];
  doluluk: TabloDolulugu;
  fairness_note: string;
  rows: TabloSatiri[];
};

export async function urunTablosuGetir(
  type?: string,
  bank?: string,
): Promise<UrunTablosu> {
  const p = new URLSearchParams();
  if (type) p.set("type", type);
  if (bank) p.set("bank", bank);
  const sorgu = p.toString();
  let res: Response;
  try {
    res = await fetch(`/api/urun-tablosu${sorgu ? `?${sorgu}` : ""}`);
  } catch {
    throw new ApiError(
      "Bağlantı kurulamadı.",
      0,
      "API'ye ulaşılamıyor. `uvicorn src.api.main:app --port 8000` çalışıyor mu? " +
        "(docker-compose up ile de gelir)",
    );
  }
  if (!res.ok) {
    throw new ApiError(
      `Sunucu ${res.status} döndü.`,
      res.status,
      "`/urun-tablosu` ucu bu sürümde var mı? (src/api/main.py)",
    );
  }
  return (await res.json()) as UrunTablosu;
}
