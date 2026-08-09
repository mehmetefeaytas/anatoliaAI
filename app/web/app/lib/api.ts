/**
 * API istemcisi — tipler + hata yönetimi.
 *
 * İlgili: src/api/main.py, next.config.js (/api/* -> FastAPI proxy)
 *
 * Kural: API çökerse veya boş dönerse arayüz SESSİZCE boş tablo göstermez.
 * Her çağrı ya veriyi ya da Türkçe, aksiyon alınabilir bir hata mesajı döndürür
 * (bkz. `ApiError`). Eski `page.tsx` `.catch(() => setRows([]))` ile hatayı
 * yutuyordu; jüri "veri yok" ile "API kapalı"yı ayırt edemiyordu.
 */

/** Bir çıkarımın kaynak metindeki yerini tarif eden alanlar. */
export type SpanInfo = {
  span_start: number | null;
  span_end: number | null;
  /** 'value' = tam ham değer vurgulandı, 'window' = yalnız çevresi. */
  span_scope: "value" | "window" | null;
  /** text[span_start:span_end] hedefe birebir eşit mi. */
  span_verified: boolean;
  /** Pencere metni belgede birden çok kez geçiyor mu. */
  span_ambiguous: boolean;
  window_start: number | null;
  window_end: number | null;
};

export type Extractor = "rule" | "ner" | "llm";

export type CompareRow = SpanInfo & {
  bank: string;
  bank_name: string | null;
  value: unknown;
  comparable: boolean;
  note: string | null;
  source_span: string | null;
  campaign_id: number;
  campaign_type: string | null;
  source_url: string | null;
  raw_value: string | null;
  confidence: number | null;
  confidence_source: string | null;
  extractor: Extractor | null;
  sort_key: number | null;
  rank: number | null;
  contradiction_count: number;
  /**
   * Bu bankanın AYNI ürün ailesinde kaç kampanyası daha var. `per_bank=best`
   * (varsayılan) iken elenen satırların sayısıdır; `all` iken 0.
   * Bilgi gizlenmiyor, özetleniyor — tamamı `per_bank=all` ile alınabilir.
   */
  other_count: number;
};

/** `/compare?per_bank=` — banka başına tek satır mı, her kayıt ayrı mı. */
export type PerBank = "best" | "all";

export type Bank = {
  slug: string;
  name: string;
  website_url: string | null;
  bddk_active: boolean;
};

/**
 * Delta durumu. `eksik_urun` ile `eksik_veri` BİLEREK ayrıdır: biri bankanın o
 * ürünü sunmadığını, diğeri çıkarımın alanı bulamadığını söyler.
 */
export type DeltaKind =
  | "eksik_urun"
  | "eksik_veri"
  | "daha_iyi"
  | "daha_kotu"
  | "esit"
  | "kiyaslanamaz"
  | "rakip_yok";

/** Deltanın bir tarafı — değer + KANITI. */
export type DeltaSide = {
  bank: string;
  bank_name: string | null;
  value: unknown;
  raw_value: string | null;
  sort_key: number | null;
  comparable: boolean;
  note: string | null;
  campaign_id: number;
  campaign_type: string | null;
  source_url: string | null;
  confidence: number | null;
  confidence_source: string | null;
  extractor: Extractor | null;
  contradiction_count: number;
};

export type DeltaField = {
  field: string;
  label: string;
  direction: FieldMeta["direction"];
  direction_label: string;
  kind: DeltaKind;
  /** Mutlak fark — yalnız iki taraf da kıyaslanabilirse. */
  abs_diff: number | null;
  /** Göreli fark (%) — rakibin değeri 0 ise hesaplanmaz. */
  rel_pct: number | null;
  /** Bankanın bu alandaki sıralama konumu ("7 bankadan 3."). */
  position: number | null;
  bank_count: number;
  mine: DeltaSide | null;
  rival: DeltaSide | null;
};

export type DeltaFamily = {
  campaign_type: string | null;
  /** Bankanın bu ailede kaç belgesi var — "ürün yok" ile "veri yok" ayrımı. */
  own_campaigns: number;
  fields: DeltaField[];
};

export type BankDelta = {
  bank: string;
  rival: string | null;
  fairness_note: string;
  families: DeltaFamily[];
};

export type FieldMeta = {
  field: string;
  label: string;
  direction: "lower_is_better" | "higher_is_better" | "unranked";
  direction_label: string;
  comparable_field: boolean;
};

export type CampaignFieldDetail = SpanInfo & {
  field: string;
  label: string;
  raw_value: string | null;
  canonical_value: unknown;
  confidence: number | null;
  confidence_source: string | null;
  extractor: Extractor | null;
  source_span: string | null;
};

export type Contradiction = {
  kind: string;
  detail: string;
  fields: string[];
};

/**
 * Ham metnin bir parçası ve gösterilip gösterilmeyeceği.
 *
 * Bloklar ham metni **bitişik ve eksiksiz** kaplar (ilk blok 0'dan başlar, son
 * bloğun `end`'i metin uzunluğudur). Offsetler HAM metne göredir; katlama
 * yalnız neyin ekrana basıldığını değiştirir, numaralandırmayı değil
 * (bkz. ../components/SourceText.tsx).
 */
export type TextBlock = {
  start: number;
  end: number;
  /** Çerçeve/gürültü olduğu için varsayılan olarak katlanır mı. */
  gizle: boolean;
  /** Katlama gerekçesi (ör. "cerez", "kvkk", "alan_disi"). */
  gerekce: string | null;
};

export type CampaignText = {
  campaign_id: number;
  bank: string;
  bank_name: string | null;
  campaign_type: string | null;
  source_url: string | null;
  scraped_at: string | null;
  text: string;
  text_length: number;
  fields: CampaignFieldDetail[];
  contradictions: Contradiction[];
  /**
   * OPSİYONEL — API henüz göndermiyor olabilir (eski sürüm). Yoksa arayüz
   * katlama yapmadan düz metne düşer.
   */
  bloklar?: TextBlock[] | null;
  /** OPSİYONEL — üretilmiş özet. `null` ise özet bölümü hiç basılmaz. */
  ozet?: string | null;
  /** OPSİYONEL — özeti hangi katman üretti ("llm" vb.). */
  ozet_kaynak?: string | null;
};

export type CampaignSummary = {
  id: number;
  bank: string;
  bank_name: string | null;
  campaign_type: string | null;
  raw_text: string;
  source_url: string | null;
  scraped_at?: string | null;
  /**
   * Üretilmiş özet. API bu alanı ZATEN döndürüyordu (`repository.py` SELECT'i
   * `c.ozet` içeriyor) ama bu tip onu tanımlamıyordu, dolayısıyla liste ekranı
   * veriyi göremiyordu. Kapsam sayacı buradan hesaplanır — ek uç gerekmez.
   */
  ozet?: string | null;
};

/** Bileşik skorun tek bir ölçüt bileşeni (`GET /advantageous`). */
export type ScoreComponent = {
  field_name: string;
  value: unknown;
  normalized: number | null;
  weight: number;
  contribution: number | null;
  note: string | null;
};

export type CompositeScore = {
  bank: string | null;
  bank_name: string | null;
  campaign_id: number | null;
  /** 0..1; kapsanan ölçütler üzerinden ortalama. Kıyas dışıysa null. */
  score: number | null;
  /** Ağırlıkça kapsama oranı (0..1). */
  coverage: number;
  comparable: boolean;
  note: string | null;
  components: ScoreComponent[];
};

export type AdvantageousGroup = {
  count: number;
  /** Grup küçükse (MIN_GROUP_SIZE altı) sıralama YAPILMAZ; gerekçe burada. */
  note: string | null;
  ranked: CompositeScore[];
};

/** Ağırlık + GEREKÇESİ. Ağırlık bir ürün kararıdır, ölçümden türetilmiş sabit değil. */
export type WeightRow = {
  field_name: string;
  weight: number;
  rationale: string | null;
  direction: "dusuk_iyi" | "yuksek_iyi";
};

export type Advantageous = {
  min_group_size: number;
  min_coverage: number;
  weights: WeightRow[];
  fairness_note: string;
  /** Kampanya türü → grup. Sıralama TÜR İÇİNDE yapılır (CLAUDE.md §17). */
  types: Record<string, AdvantageousGroup>;
};

export type ScoringStep = { no: number; name: string; detail: string };

export type ScoringRow = {
  bank: string;
  bank_name: string | null;
  value: unknown;
  sort_key: number | null;
  comparable: boolean;
  note: string | null;
  rank: number | null;
  confidence: number | null;
  extractor: Extractor | null;
};

export type Scoring = {
  field: string;
  label: string;
  direction: FieldMeta["direction"];
  direction_label: string;
  formula_source: string;
  steps: ScoringStep[];
  composite_weights: Record<string, number> | null;
  composite_note: string;
  rows: ScoringRow[];
};

export type ContradictionRow = Contradiction & {
  bank: string;
  bank_name: string | null;
  campaign_id: number;
  campaign_type: string | null;
  source_url: string | null;
};

export type ContradictionSummary = {
  scanned_campaigns: number;
  scanned_banks: number;
  contradiction_count: number;
  affected_campaigns: number;
  by_kind: Record<string, number>;
};

export type ExtractField = SpanInfo & {
  field: string;
  label: string;
  value: unknown;
  raw_value: string | null;
  confidence: number | null;
  confidence_source: string | null;
  extractor: Extractor | null;
  source_span: string | null;
};

export type ExtractResult = {
  bank: string;
  campaign_type: string | null;
  campaign_type_confidence: number | null;
  text: string;
  text_length: number;
  llm_available: boolean;
  fields: ExtractField[];
  missing_fields: { field: string; label: string }[];
  contradictions: Contradiction[];
};

export type ChatSource = {
  bank?: string;
  value?: unknown;
  source_span?: string | null;
  /**
   * OPSİYONEL — denetlenebilir kaynak bağlantısı. Alan gelmediğinde arayüz
   * çökmez, kaynak satırı bağlantısız gösterilir (bkz. ../components/ChatPanel.tsx).
   */
  source_url?: string | null;
  /** OPSİYONEL — «belgeye git» sıçraması için kampanya kimliği. */
  campaign_id?: number | null;
  /**
   * Belgenin önceden üretilmiş özeti («AI Özeti»); üretilmemişse `null`.
   *
   * RAG yolunda kaynak, belgenin TAMAMIDIR ve ham hâliyle tabloya basılınca
   * tek satır ekranı dolduruyordu. Sunucu bu alanı her kayıtta gönderir
   * (bkz. src/api/main.py `_kaynaklari_zenginlestir`); `null` ise arayüz
   * özet UYDURMAZ, ham metnin kırpılmış olduğunu açıkça yazar.
   */
  ozet?: string | null;
  [k: string]: unknown;
};

export type ChatResp = {
  answer: string;
  handler: "structured" | "rag" | string;
  field: string | null;
  sources: ChatSource[];
};

/** Kullanıcıya gösterilebilir, Türkçe API hatası. */
export class ApiError extends Error {
  readonly status: number;
  readonly hint: string;

  constructor(message: string, status: number, hint: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.hint = hint;
  }
}

const OFFLINE_HINT =
  "API'ye ulaşılamıyor. `uvicorn src.api.main:app --port 8000` çalışıyor mu? " +
  "(docker-compose up ile de gelir)";

async function readError(res: Response): Promise<string> {
  try {
    const body: unknown = await res.json();
    if (body && typeof body === "object" && "detail" in body) {
      const d = (body as { detail: unknown }).detail;
      if (typeof d === "string") return d;
      return JSON.stringify(d);
    }
  } catch {
    /* gövde JSON değil — aşağıdaki genel mesaj kullanılır */
  }
  return `Sunucu ${res.status} döndü.`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError("Bağlantı kurulamadı.", 0, OFFLINE_HINT);
  }
  if (!res.ok) {
    // 502/504 ve çoğu 500: Next proxy'si FastAPI'ye ulaşamıyor (en sık demo
    // arızası). Gerçek bir sunucu hatası da aynı koda düşebildiği için iki
    // olasılık da söylenir — sessizce boş tablo göstermekten iyidir.
    throw new ApiError(await readError(res), res.status,
      res.status >= 500
        ? `API'ye ulaşılamıyor ya da sunucu hata verdi. ${OFFLINE_HINT}`
        : "İstek reddedildi (geçersiz parametre olabilir).");
  }
  try {
    return (await res.json()) as T;
  } catch {
    throw new ApiError("Yanıt JSON olarak ayrıştırılamadı.", res.status,
      "Proxy doğru uca bağlı mı? (next.config.js /api/* yönlendirmesi)");
  }
}

export const api = {
  fields: () => request<FieldMeta[]>("/api/fields"),
  campaigns: () => request<CampaignSummary[]>("/api/campaigns"),
  /**
   * Banka kataloğu. Delta paneli bunu kullanır — `/campaigns`'ten türetmek,
   * hiç kampanyası toplanmamış bankayı listeden düşürüyordu; oysa "bende hiç
   * ürün yok" tam da o panelin cevaplaması gereken soru.
   */
  banks: () => request<Bank[]>("/api/banks"),
  /** Banka içi delta — tek istekte, ürün ailesi içinde (bkz. `/bank-delta`). */
  bankDelta: (bank: string, type?: string, rival?: string) => {
    const p = new URLSearchParams({ bank });
    if (type) p.set("type", type);
    if (rival) p.set("rival", rival);
    return request<BankDelta>(`/api/bank-delta?${p.toString()}`);
  },
  campaignText: (id: number) => request<CampaignText>(`/api/campaigns/${id}/text`),
  compare: (field: string, intent?: string, type?: string, perBank?: PerBank) => {
    const p = new URLSearchParams({ field });
    if (intent) p.set("intent", intent);
    if (type) p.set("type", type);
    if (perBank) p.set("per_bank", perBank);
    return request<CompareRow[]>(`/api/compare?${p.toString()}`);
  },
  /**
   * Çok alanlı, ağırlıklı bileşik skor — sıralama TÜR İÇİNDE yapılır.
   * Uç 2026-08-08'de eklendi ama arayüzden hiç çağrılmıyordu; tür içinde adil
   * sıralama yapan tek kod yolu budur.
   */
  advantageous: (type?: string) => {
    const p = new URLSearchParams();
    if (type) p.set("type", type);
    const q = p.toString();
    return request<Advantageous>(`/api/advantageous${q ? `?${q}` : ""}`);
  },
  scoring: (field: string, type?: string) => {
    const p = new URLSearchParams({ field });
    if (type) p.set("type", type);
    return request<Scoring>(`/api/scoring?${p.toString()}`);
  },
  contradictions: () => request<ContradictionRow[]>("/api/contradictions"),
  contradictionSummary: () =>
    request<ContradictionSummary>("/api/contradictions/summary"),
  extract: (text: string, bank: string) =>
    request<ExtractResult>("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, bank }),
    }),
  chat: (question: string) =>
    request<ChatResp>("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    }),
};

/** ApiError olmayan hataları da kullanıcıya gösterilebilir hale getirir. */
export function toDisplayError(e: unknown): { message: string; hint: string } {
  if (e instanceof ApiError) return { message: e.message, hint: e.hint };
  if (e instanceof Error) return { message: e.message, hint: "" };
  return { message: "Bilinmeyen hata.", hint: "" };
}
