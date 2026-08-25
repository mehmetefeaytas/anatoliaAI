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

/**
 * Kampanyanın geçerlilik damgası (`campaigns.campaign_status`).
 *
 * `null` "geçerli" DEMEK DEĞİLDİR, "damgasız" demektir — korpusun büyük kısmı
 * bu durumdadır. Yalnız `"expired"` bir iddia taşır ve sıralamadan çıkarır.
 */
export type CampaignStatus = "expired" | "active";

export type CompareRow = SpanInfo & {
  bank: string;
  bank_name: string | null;
  value: unknown;
  comparable: boolean;
  note: string | null;
  /**
   * Süresi dolmuş kampanya rozeti. `note`'tan AYRI taşınır: bir satır aynı
   * anda hem aralık hem süresi dolmuş olabilir ve `note` tek bir dizedir.
   */
  campaign_status: CampaignStatus | null;
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

/**
 * Belgenin NE OLDUĞU: kampanya sayfası mı, akit/tarife metni mi.
 *
 * `campaign_type` ile KARIŞTIRMA — o, 8 kampanya TÜRÜ sınıflandırmasıdır
 * (Konut Finansmanı, Kart…). `null` "bilinmiyor" demektir; sınıflandırılamayan
 * belgeye tür uydurulmaz.
 */
export type BelgeTuru = "kampanya" | "sozlesme";

/**
 * `GET /campaigns` yanıtının bir satırı — **ÜSTVERİ, ham gövde değil**.
 *
 * `raw_text` bu tipten KALDIRILDI ve uç onu artık varsayılan olarak
 * göndermiyor. Ölçüm (2026-08-11): yanıt 10.339.015 bayttı ve neredeyse
 * tamamı o alandı; `web/app` içinde tek geçtiği yer de tam olarak burasıydı —
 * yani hiç okunmayan 10 MB her sayfa açılışında indiriliyordu. Ham metin
 * gerçekten gerektiğinde `campaignText(id)` çağrılır: tek belge, offsetleri
 * ve blokları ile birlikte.
 */
export type CampaignSummary = {
  id: number;
  bank: string;
  bank_name: string | null;
  campaign_type: string | null;
  source_url: string | null;
  scraped_at?: string | null;
  /**
   * Üç alan da tel üzerinde ZATEN vardı; bu tip onları tanımlamadığı için
   * liste ekranı veriyi göremiyordu (`ozet` ile aynı hikâye).
   */
  belge_turu?: BelgeTuru | null;
  /** `null` = damgasız. "Geçerli" DEMEK DEĞİLDİR — bkz. `CampaignStatus`. */
  campaign_status?: CampaignStatus | null;
  /**
   * Üretilmiş özet. API bu alanı ZATEN döndürüyordu (`repository.py` SELECT'i
   * `c.ozet` içeriyor) ama bu tip onu tanımlamıyordu, dolayısıyla liste ekranı
   * veriyi göremiyordu. Kapsam sayacı buradan hesaplanır — ek uç gerekmez.
   */
  ozet?: string | null;
  /**
   * Özetin NEDEN yok olduğu (`icerik_yok`, `llm_kapali` …). Boş `ozet` tek
   * başına "denendi ve çıkmadı" ile "hiç denenmedi"yi ayırt edemez.
   */
  ozet_sebep?: string | null;
};

/**
 * Bankanın KENDİ yayımladığı finansman oranı (kampanya korpusundan DEĞİL).
 *
 * Ayrı bir tip, `RankRow`un yanına eklenen bir alan değil: bu satırların
 * kanıt zinciri farklı. Kampanya alanı bir belgenin span'ine dayanır; bu
 * satır bankanın hesaplama aracına. İkisini tek tipte toplamak, ekranda
 * "aynı güvenle ölçüldü" izlenimi verirdi.
 */
export type FinansmanOrani = {
  bank_slug: string | null;
  product_name: string | null;
  product_code: string | null;
  urun_ailesi: string;
  /** Aylık kâr payı oranı (%). DÜŞÜK olan avantajlı. */
  monthly_rate: number | null;
  /** Yıllık toplam maliyet oranı (%). Banka yayımlamıyorsa `null` — uydurulmaz. */
  annual_cost_rate: number | null;
  term_months: number | null;
  amount: number | null;
  amount_max: number | null;
  total_payment: number | null;
  fees: Record<string, number> | null;
  currency: string;
  source_url: string | null;
  collected_at: string | null;
  method: string | null;
  note: string | null;
};

export type FinansmanOranlari = {
  /** `"dusuk_iyi"` — katılma hesabının TERSİ. Arayüz bunu varsaymaz, okur. */
  yon: string;
  yon_etiketi: string;
  urun_ailesi: string | null;
  term_months: number | null;
  veri_yok: boolean;
  rows: FinansmanOrani[];
  urun_aileleri: string[];
  vadeler: number[];
  kapsam: { kayit: number; banka: number; banka_basina: Record<string, number> };
  kaynak_notu: string;
};

/** Tek bankanın yayımladığı oranların özeti — banka sayfası için. */
export type BankaFinansmanOzeti = {
  bank_slug: string;
  veri_yok: boolean;
  gerekce?: string;
  kayit?: number;
  urun?: number;
  en_dusuk_oran?: number;
  en_yuksek_oran?: number;
  kaynak?: string[];
  turler?: Record<string, {
    kayit: number;
    en_dusuk_oran: number;
    urunler: string[];
  }>;
};

/** `GET /campaigns` süzgeçleri. Hepsi opsiyonel; hiçbiri verilmezse tam liste. */
export type CampaignParams = {
  /** Serbest metin — banka, tür, özet ve adreste arar (ham gövdede DEĞİL). */
  q?: string;
  bank?: string;
  type?: string;
  belge_turu?: BelgeTuru;
  /** `"damgasiz"` üçüncü kovadır: `campaign_status IS NULL`. */
  status?: CampaignStatus | "damgasiz";
  limit?: number;
  offset?: number;
  /**
   * Ham metni de iste. Arayüz bunu KULLANMAZ — 10 MB'lık yükün sebebi buydu.
   * Sözleşmede duruyor ki uç geri açılabilir kalsın.
   */
  govde?: boolean;
};

/**
 * `GET /search` — bir sonucun NEDEN eşleştiği.
 *
 * `alan` sunucudaki sütun adıdır (bir sınıf etiketi, kullanıcıya dönük metin
 * değil); ekranda okunacak karşılığı `lib/arama.ts` içindeki `alanEtiketi()`
 * ile üretilir. `parca` eşleşmenin ÖZGÜN yazımıyla, bağlamı içinde kesilmiş
 * hâlidir — kırpılan uçlarda '…' bulunur.
 */
export type AramaEslesmesi = {
  alan: string;
  parca: string;
};

export type AramaBankasi = {
  slug: string;
  name: string;
  /**
   * Bu bankanın KORPUSTAKİ TOPLAM belge sayısı — eşleşen belge sayısı DEĞİL.
   * Grup bir gezinme hedefidir ("bu bankaya git"), bir sonuç sayacı değil.
   */
  campaign_count: number;
};

export type AramaBelgesi = {
  id: number;
  bank: string;
  bank_name: string | null;
  campaign_type: string | null;
  belge_turu: BelgeTuru | null;
  campaign_status: CampaignStatus | null;
  eslesme: AramaEslesmesi;
};

/**
 * Gruplu arama sonucu.
 *
 * `toplam` süzgeç sonrası GERÇEK sayıları taşır; listeler `limit` ile
 * kırpılmıştır. İkisini karıştırmak "başka sonuç yok" izlenimi verirdi.
 */
export type AramaSonucu = {
  sorgu: string;
  banks: AramaBankasi[];
  campaigns: AramaBelgesi[];
  types: string[];
  toplam: { banks: number; campaigns: number; types: number };
};

/** Bir bankanın veri kapsamı: kaç belge, kaç ÇEŞİT alan. */
export type BankaKapsami = {
  belge: number;
  /** FARKLI alan adı sayısı (satır değil) — üst sınırı `/fields` uzunluğudur. */
  alan: number;
};

/**
 * `GET /stats` — korpusun sayısal özeti, TEK istekte.
 *
 * Bu sayılar eskiden `/campaigns` yanıtından istemcide sayılıyordu ve bunun
 * bedeli 10 MB'lık bir istekti. Üstelik istemcide sayılabilen tek şey "kaç
 * satır var"dı: alan kapsamı, katman dağılımı ve banka başına alan çeşidi
 * `extracted_fields` tablosunu gerektiriyor.
 *
 * Anahtar kümeleri SABİTTİR: sıfır değerler de yazılır, böylece `0` ile
 * "ölçülmedi" karışmaz.
 */
export type Stats = {
  korpus: {
    /** KORPUS KAYNAĞI sayısı — `/banks`'ten farklı olabilir (o, otorite
     *  kaynaklarını süzer). İki sayı farklı soruların cevabıdır. */
    banks: number;
    banks_with_campaigns: number;
    campaigns: number;
    fields: number;
    campaigns_with_fields: number;
  };
  /** `kampanya` / `sozlesme` / `bilinmeyen`. */
  belge_turu: Record<string, number>;
  /** `active` / `expired` / `damgasiz` — damgasız AKTİF DEĞİLDİR. */
  campaign_status: Record<string, number>;
  /** Banka slug → kampanya sayısı. */
  banka_basina: Record<string, number>;
  /** Banka slug → "3 belge / 12 alan" etiketinin verisi. */
  banka_kapsami: Record<string, BankaKapsami>;
  /** Korpusta geçen kampanya türleri, alfabetik ve tekrarsız. */
  campaign_types: string[];
  /** Kampanya türü (ürün ailesi) → belge sayısı. Yalnız `belge_turu=kampanya`
   *  (sözleşme hariç); tür boş olan belgeler `"Belirtilmemiş"` kovasında. */
  campaign_type_counts: Record<string, number>;
  /** Alan adı → o alanın çıkarıldığı belge sayısı. */
  alan_kapsami: Record<string, number>;
  /** Çıkarıcı katman (`rule` / `ner` / `llm`) → üretilen alan sayısı. */
  katman: Record<string, number>;
  llm: { acik: boolean };
  /** `"sqlite"` | `"postgres"` — hangi veri tabanına bağlıyız. */
  backend: string;
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
  /**
   * ÖLÇÜLDÜ (2026-08-12): bu alan `Record<string, number>` DEĞİL.
   *
   * `src/api/main.py:1624` onu `weight_manifest()` ile dolduruyor ve o fonksiyon
   * (`src/comparison/compare.py:1106`) `list[dict]` döndürüyor — her satırda
   * `field_name`, `weight`, `rationale`, `direction`. Yani şekli `WeightRow[]`,
   * `Advantageous.weights` ile aynı.
   *
   * Yanlış tip sessiz değildi: `ScoringExplainer` bir nesneyi React çocuğu
   * olarak basmaya çalışıyor ve «Objects are not valid as a React child» ile
   * BANKA SAYFASININ TAMAMINI düşürüyordu. Tip sistemi burada koruma değil,
   * tuzaktı — derleyici doğruladığı için kimse uca bakmamıştı.
   */
  composite_weights: WeightRow[] | null;
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
  /** İstek `gold_id` taşıdıysa altın küme karşılaştırması; yoksa `null`. */
  gold: GoldKarsilastirma | null;
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

/**
 * Bir turun sonunda geriye kalan, bir SONRAKİ tura taşınabilir durum.
 *
 * Sunucu oturum saklamaz: bu kaydı üretir, istemci saklar (bkz.
 * ./sohbetOturumu.ts) ve bir sonraki istekte geri gönderir. İçeriği serbest
 * metin DEĞİLDİR — sunucu (`src/chatbot/router.py` `ChatContext.dogrula`)
 * her değeri sonlu bir izin listesinden geçirir. Bu yüzden bağlam kanalı
 * güvenlik kapıları için bir atlatma yüzeyi oluşturmaz.
 */
export type ChatContext = {
  field: string | null;
  intent: string | null;
  filters: Record<string, unknown>;
  /** Önceki CEVABIN öznesi (banka slug'ı) — varsa. */
  subject_banks: string[];
};

/** Bu turda önceki turlardan devralınan tek bir boyut. */
export type ChatInherited = {
  kind: string;
  /** Kullanıcıya gösterilecek Türkçe etiket — sunucu üretir. */
  label: string;
};

/**
 * Yapısal cevabın LLM ile sözelleştirilip sözelleştirilmediğinin denetim kaydı.
 *
 * `applied` yanlışsa ekrandaki metin ŞABLON cevaptır. `attempted` doğru ama
 * `applied` yanlışsa doğrulama kapısı LLM çıktısını REDDETMİŞTİR (uydurulmuş
 * sayı, kaybolan banka adı, zaman aşımı…) ve `reason` gerekçeyi taşır.
 */
export type ChatVerbalize = {
  attempted?: boolean;
  applied?: boolean;
  ms?: number | null;
  reason?: string | null;
};

/** Tek bir güvenlik kapısının bu cevaptaki durumu. */
export type ChatGate = {
  /** Kapı kimliği — sunucudaki sabitle aynı dize (`terminoloji`, …). */
  id: string;
  /** Kullanıcıya gösterilecek Türkçe ad. */
  label: string;
  /** Kapının ne yaptığını anlatan tek cümle. */
  aciklama: string;
  /** Bu cevapta ateşlendi mi. */
  fired: boolean;
};

/**
 * Talimat devralma işareti taşıdığı için DÜŞÜRÜLEN bir kaynak belge.
 *
 * Belgenin metni BİLEREK taşınmaz: karantinanın gerekçesi "içine talimat
 * gömülmüş bir sayfanın geri kalanına da güvenilmez"dir. Yalnız kimliği
 * (banka, kampanya, bağlantı) ve yakalanan işaret gelir; işaret sunucuda
 * kırpılıp çıktı süzgecinden geçirilmiştir.
 */
export type ChatQuarantine = {
  bank?: string | null;
  campaign_id?: number | null;
  source_url?: string | null;
  /** Belgede yakalanan talimat devralma parçası. */
  isaret?: string | null;
};

/**
 * Bir cevabın güvenlik denetim kaydı (bkz. src/api/main.py `_guvenlik_ozeti`).
 *
 * `gates` ateşlenmeyen kapıları da içerir — liste "hangi kapılar var"
 * sorusuna da cevap vermek zorunda. Gürültüyü arayüz yönetir: ayrıntı jüri
 * modunda açılır, normal modda yalnız SESSİZ gerçekleşen olaylar
 * (karantina, yeniden yazılan terim) görünür.
 */
export type ChatSafety = {
  gates: ChatGate[];
  /** Yalnız ateşlenen kapıların kimlikleri, sunucudaki sırayla. */
  fired: string[];
  /** Cevabı hazır politika yanıtıyla DURDURAN kapı — yoksa `null`. */
  blocked_gate?: string | null;
  /** Kaynak/kapsam yokluğu nedeniyle değer üretilmedi mi. */
  abstained?: boolean;
  /**
   * Çıktı süzgecinin doğru karşılığıyla değiştirdiği terim sayısı.
   *
   * Terimin KENDİSİ gelmez ve bu bilinçlidir: az önce ekrandan silinen dizeyi
   * denetim kutusunda geri basmak, kapının işini geri almak olurdu.
   */
  rewritten_terms?: number;
  quarantined: ChatQuarantine[];
};

export type ChatResp = {
  answer: string;
  handler: "structured" | "rag" | string;
  field: string | null;
  sources: ChatSource[];
  context?: ChatContext | null;
  inherited?: ChatInherited[];
  verbalize?: ChatVerbalize;
  safety?: ChatSafety;
};

/**
 * Veri tazeleme ön izlemesi — düğmeye BASILMADAN önce ne olacağını söyler.
 *
 * Bu uç ağa çıkmaz; sayılar banka tanım dosyasından türetilir. Ön izlemenin
 * kendisi internet isteseydi, "internet var mı" sorusunun bedeli yine
 * internet olurdu.
 */
export type RefreshPreview = {
  bank: string;
  bank_name: string;
  website_url: string | null;
  scrape_mode: string;
  /** Kaç liste/site haritası sayfasından başlanacak. */
  giris_sayfasi: number;
  azami_belge: number;
  /** Alan başına bekleme (saniye) — etik toplama kısıtı, 2–5 aralığında. */
  gecikme_sn: number;
  tahmini_istek_alt: number;
  tahmini_istek_ust: number;
  tahmini_sure_alt_sn: number;
  tahmini_sure_ust_sn: number;
  /** Bu bankanın ham arşivinde şu an duran belge sayısı. */
  arsivdeki_belge: number;
  hedef_dizin: string;
  internet_gerekir: boolean;
  /** Her zaman `false`: tazeleme veri tabanına yazmaz. */
  veri_tabani_etkilenir: boolean;
  robots_uyumu: boolean;
  user_agent: string;
};

/** Tazeleme işinin yaşam döngüsü. */
export type RefreshDurum =
  | "bekliyor"
  | "kesif"
  | "cekiliyor"
  | "yaziliyor"
  | "tamam"
  | "hata"
  | "iptal";

/** Tek bir belgenin diskteki hâline göre durumu. */
export type RefreshBelge = {
  source_url: string;
  title: string | null;
  durum: "yeni" | "degisen" | "ayni";
  karakter: number;
  onceki_karakter: number | null;
};

/**
 * Özet kapsamı — dört kova KESİŞMEZ ve toplamı `toplam`'a eşittir.
 *
 * `icerik_yok` ile `denenmemis` ayrımı ekrandaki cümlenin doğruluğunu taşır:
 * "özetlenecek içerik yok" yalnız denenmiş ve içeriği çıkmamış belgeler için
 * söylenebilir. Yeni toplanmış bir belge `denenmemis` kovasındadır.
 */
export type OzetKapsam = {
  toplam: number;
  ozetli: number;
  /** Denendi, belgede özetlenecek içerik çıkmadı (tekrar denemek anlamsız). */
  icerik_yok: number;
  /** Denendi, koşuya ait bir sebeple üretilemedi (tekrar denenebilir). */
  basarisiz: number;
  /** Hiç denenmedi — düğmenin asıl hedefi. */
  denenmemis: number;
  /** Düğmeye basılınca işlenecek belge sayısı (`denenmemis + basarisiz`). */
  hedef: number;
  sebepler: Record<string, number>;
  llm_acik: boolean;
  /** LLM kapalıysa neden üretilemeyeceğini anlatan cümle; açıksa null. */
  llm_notu: string | null;
  /** Koşan iş varsa kimliği. */
  calisan_is: string | null;
};

export type OzetIsiDurum =
  | "bekliyor"
  | "uretiliyor"
  | "tamam"
  | "hata"
  | "iptal";

/** Özet üretim işinin anlık durumu. */
export type OzetIsi = {
  is_id: string;
  durum: OzetIsiDurum;
  asama: string;
  baslangic: string;
  bitis: string | null;
  hedef: number;
  islenen: number;
  uretilen: number;
  yazilan: number;
  uretilemeyen: Record<string, number>;
  korpus_belge: number;
  iptal_istendi: boolean;
  mesaj: string | null;
  bitti: boolean;
};

/** Gelecek faz ucunun bir gövde alanı. */
export type AdminAlan = {
  ad: string;
  tip: string;
  zorunlu: boolean;
  aciklama: string;
};

export type AdminUc = {
  yol: string;
  yontem: string;
  baslik: string;
  ozet: string;
  alanlar: AdminAlan[];
};

/**
 * Gelecek faz sözleşmesi. `acik: false` ve uçlar 501 döner — sözleşme
 * tanımlıdır, davranış değil.
 */
export type AdminPlan = {
  acik: boolean;
  /**
   * Ekranın en üstündeki büyük başlık — uçların NE ZAMAN açılacağını söyler
   * ("Yakın dönem / iş birliği durumunda…"). Sunucudan gelir, ekranda sabit
   * yazılmaz.
   */
  baslik: string;
  /** Başlığın üstündeki küçük durum etiketi ("Bu sürümde kapalı"). */
  durum_etiketi: string;
  sebep: string;
  bugunku_yol: string;
  uclar: AdminUc[];
};

/** Alınamayan bir adres ve gerekçesi. */
export type RefreshHata = {
  url: string;
  reason: string;
  detail?: string;
};

export type RefreshJob = {
  is_id: string;
  bank: string;
  bank_name: string;
  durum: RefreshDurum;
  /** Kullanıcıya gösterilen anlık aşama cümlesi. */
  asama: string;
  baslangic: string;
  bitis: string | null;
  tamamlanan: number;
  toplam: number;
  cekilen: number;
  yeni: number;
  degisen: number;
  ayni: number;
  hata: number;
  yazilan_dosya: number;
  iptal_istendi: boolean;
  hatalar: RefreshHata[];
  hata_tamami: number;
  belgeler: RefreshBelge[];
  notlar: string[];
  robots_ozet: string | null;
  mesaj: string | null;
  hedef_dizin: string | null;
  bitti: boolean;
};

/** `RefreshSonOzet.degisen_belgeler` içindeki tek bir kayıt. */
export type RefreshDegisenBelge = {
  title: string | null;
  source_url: string | null;
};

/**
 * Bir bankanın EN SON TAMAMLANMIŞ tazelemesinin kalıcı özeti.
 *
 * `RefreshJob` tamamen bellek içidir (iş/süreç bitince kaybolur); bu tip
 * `data/son-tazeleme.json`'dan okunan `GET /refresh/last-summary` yanıtının
 * şeklidir — "en son ne zaman tazeleme yapıldı, kaç belge değişti/yeni
 * geldi" iddiasının süreç yeniden başlasa da hayatta kalan izidir.
 */
export type RefreshSonOzet = {
  bank: string;
  bank_name: string;
  is_id: string;
  bitis: string | null;
  yeni: number;
  degisen: number;
  ayni: number;
  hata: number;
  degisen_belgeler: RefreshDegisenBelge[];
};

/** `GET /refresh/last-summary` yanıtı — banka slug'ı → en son özet. */
export type RefreshSonOzetHaritasi = Record<string, RefreshSonOzet>;

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

/**
 * Süzgeç sonrası TOPLAM kayıt sayısını taşıyan yanıt başlığı.
 *
 * Sunucu `GET /campaigns` gövdesini çıplak liste olarak KORUR (zarfa sarmak
 * her çağıranı aynı anda kırardı) ve toplamı bu başlığa yazar. Belge seçici
 * "1774 belgeden 50'si" diyebilmek için tam olarak bu sayıya muhtaç: dilim
 * alındıktan sonra toplam gövdeden geri getirilemez.
 */
const TOPLAM_BASLIK = "X-Toplam-Kayit";

/** Gövde + sayfalama üstverisi. `toplam` başlık yoksa `null` (uydurulmaz). */
export type Sayfa<T> = { kayitlar: T; toplam: number | null };

/**
 * İstek İPTAL edildi mi (kullanıcı ya da zaman aşımı) — bağlantı hatası DEĞİL.
 *
 * Ayrım şart: iptal edilen bir isteği "Bağlantı kurulamadı" diye göstermek
 * kullanıcıya YANLIŞ bilgi verir ve API'yi çalışmıyor sanmasına yol açar.
 * `AbortError` tarayıcıya göre `DOMException` ya da `Error` olabilir, o
 * yüzden ada bakılıyor.
 */
export const IPTAL_HINT =
  "İstek iptal edildi. Soruyu yeniden gönderebilirsiniz.";

function iptalMi(e: unknown): boolean {
  return (
    typeof e === "object" && e !== null && "name" in e &&
    (e as { name?: string }).name === "AbortError"
  );
}

async function istek<T>(path: string, init?: RequestInit): Promise<Sayfa<T>> {
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch (e) {
    // İPTAL, bağlantı hatasından AYRI raporlanır (bkz. `iptalMi`).
    if (iptalMi(e)) throw new ApiError("İstek iptal edildi.", 0, IPTAL_HINT);
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
  let veri: T;
  try {
    veri = (await res.json()) as T;
  } catch {
    throw new ApiError("Yanıt JSON olarak ayrıştırılamadı.", res.status,
      "Proxy doğru uca bağlı mı? (next.config.js /api/* yönlendirmesi)");
  }
  const ham = res.headers.get(TOPLAM_BASLIK);
  const sayi = ham === null ? Number.NaN : Number.parseInt(ham, 10);
  return { kayitlar: veri, toplam: Number.isFinite(sayi) ? sayi : null };
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  return (await istek<T>(path, init)).kayitlar;
}

/**
 * `/health` yanıtı — sunucunun kendi hakkında söyledikleri.
 *
 * Uç en baştan beri vardı ve bu üç alanı döndürüyordu; İSTEMCİ METODU HİÇ
 * YOKTU. Sonuç: API'nin ayakta olup olmadığı, hangi veritabanına baktığı ve
 * yerel modelin açık olup olmadığı ancak bir panel çökünce ya da bir düğme
 * devre dışı kalınca anlaşılıyordu.
 */
export type Health = {
  status: string;
  /** Yerel model açık mı. Kapalıyken sistem cevap vermeye DEVAM eder. */
  llm: boolean;
  /** Hangi depo: `sqlite` | `postgres`. «Hangi veritabanındayız» hata sınıfı. */
  backend: string;
};

/**
 * İşlem günlüğü (audit log) kaydı — `GET /log` bir satırı.
 *
 * Şema `src/api/gunluk.py` modül başlığında tanımlı; burada yalnız istemci
 * görüntüsü var. İki KAYIT TÜRÜ tek listede geliyor ve tipin bunu yansıtması
 * şart:
 *
 *  - `olay: "istek"` — metot/yol/durum/süre dolu.
 *  - `olay: "gunluk_dondu"` — dosya döndürüldü; metot, yol ve durum YOKTUR,
 *    yerine hangi dosyaya taşındığı gelir. Bu kayıt `yalniz_yazanlar`
 *    süzgecinde de görünür: kısalmış bir günlüğe bakan kişinin "kayıt
 *    kayboldu mu" sorusunu cevaplayan tek satır odur.
 *
 * Bu yüzden istek alanları OPSİYONEL. Zorunlu yapıp döndürme kaydında sahte
 * bir `"GET"` uydurmak, denetim kaydına yalan yazmak olurdu.
 */
export type GunlukKaydi = {
  /** UTC ISO-8601. Panel de UTC gösterir (gerekçe: lib/gunluk.ts). */
  zaman: string;
  olay: "istek" | "gunluk_dondu" | string;
  metot?: string;
  yol?: string;
  durum?: number;
  sure_ms?: number;
  /** `POST`/`PUT`/`PATCH`/`DELETE` — panel varsayılanı bu bayrağa dayanır. */
  yazan?: boolean;
  /** İsteği atan adres. Bilinmiyorsa `null` — uydurulmaz. */
  istemci?: string | null;
  /** Tazeleme / özet işinin kimliği; ilgili değilse `null`. */
  is_id?: string | null;
  /**
   * Yazan ucun KENDİ SONUCUNDAN bildirdiği dar özet (hangi banka, kaç alan).
   * İstek gövdesinin kopyası DEĞİLDİR ve okuma uçlarında hiç bulunmaz.
   */
  eylem?: Record<string, unknown> | null;
  /** Döndürme kaydına özgü alanlar. */
  bayt?: number;
  azami_bayt?: number;
  tasinan_dosya?: string | null;
  silinen_dosya?: string | null;
};

/** `GET /log` sorgu parametreleri. Boş alanlar gönderilmez. */
export type GunlukParams = {
  yalniz_yazanlar?: boolean;
  metot?: string;
  yol?: string;
  /** ISO-8601 (`2026-08-13` ya da `2026-08-13T09:00:00Z`). */
  baslangic?: string;
  bitis?: string;
  limit?: number;
  offset?: number;
};

/**
 * Katılma hesabı oranı satırı — TKBB haftalık verisi.
 *
 * `term_months` satırın KENDİ vadesini taşır ve gösterilmek zorundadır: vade
 * süzgeci verilmediğinde her banka kendi en iyi vadesiyle listelenir, yani
 * vade gizlenirse farklı vadeler aynı kolonda kıyaslanmış olur.
 */
export type KatilmaSatiri = {
  bank_slug: string;
  bank_name: string;
  annual_rate: number;
  term_months: number;
  currency: string;
  period_date: string;
  source_url: string;
};

/**
 * `/katilma-oranlari` yanıtı.
 *
 * `buyukluk` iki değer alır ve İKİSİ AYNI LİSTEDE DÖNMEZ: `getiri`
 * gerçekleşen yıllık getiri (%42), `pay` katılımcıya düşen bölüşüm (%90).
 * Pay sayısal olarak getiriden büyüktür; tek listede "en iyi oran" yanlış
 * bankayı gösterirdi (bkz. decisions/katilma-orani-iki-ayri-buyukluk.md).
 *
 * `mevcut` gerçekten VERİSİ OLAN seçenekleri taşır — sabit bir liste basmak
 * verisi olmayan bir para birimini seçilebilir gösterirdi.
 */
export type KatilmaOranlari = {
  buyukluk: "getiri" | "pay";
  buyukluk_etiketi: string;
  currency: string;
  term_months: number | null;
  period_date: string | null;
  veri_yok: boolean;
  rows: KatilmaSatiri[];
  source_url: string;
  source_label: string;
  mevcut: { para_birimleri: string[]; vadeler: number[] };
  uyari: string;
};

export const api = {
  /**
   * Sağlık yoklaması.
   *
   * Diğer çağrılardan farklı olarak hatası YUTULMAZ ama beklenendir: bu ucun
   * başarısız olması da bir bilgidir ve arayüz onu «API kapalı» olarak
   * gösterir (bkz. lib/saglik.tsx).
   */
  health: () => request<Health>("/api/health"),
  /**
   * Katılma hesabı oranları — banka başına en iyi satır, azalan sırada.
   *
   * Sıralama SUNUCUDA yapılır: iki büyüklüğün ayrı tutulması bir veri katmanı
   * kuralıdır ve TSX'e kopyalansaydı iki yerde yaşardı (`campaigns()` ile
   * aynı gerekçe).
   */
  katilmaOranlari: (params: {
    buyukluk?: "getiri" | "pay";
    currency?: string;
    term_months?: number | null;
  } = {}) => {
    const p = new URLSearchParams();
    for (const [ad, deger] of Object.entries(params)) {
      if (deger !== undefined && deger !== null && deger !== "") {
        p.set(ad, String(deger));
      }
    }
    const q = p.toString();
    return request<KatilmaOranlari>(`/api/katilma-oranlari${q ? `?${q}` : ""}`);
  },
  fields: () => request<FieldMeta[]>("/api/fields"),
  /**
   * Belge listesi — ÜSTVERİ. Ham gövde gelmez (`govde` sözleşmede duruyor ama
   * arayüz kullanmıyor); gerekçe `CampaignSummary` tipinde.
   *
   * Süzgeçler sunucuda uygulanır, istemcide değil: `status` ve `belge_turu`
   * kovalarının anlamı (özellikle `damgasiz` = `NULL`) veri katmanının
   * kuralıdır ve TSX'e kopyalansaydı iki yerde yaşardı.
   */
  /**
   * Bankaların kendi yayımladığı finansman oranları.
   *
   * Kampanya korpusundan gelmiyor: `kar_payi_orani` belgelerin yalnız
   * %6,1'inde geçiyor ve bu bir çıkarım kusuru değil — bilgi o metinlerde YOK
   * (ölçüldü: EVREN 60 belgede 0 kabul, yerel model 30 belgede 0).
   */
  finansmanOranlari: (p: { urun_ailesi?: string; term_months?: number;
                           tum_kayitlar?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (p.urun_ailesi) q.set("urun_ailesi", p.urun_ailesi);
    if (p.term_months !== undefined) q.set("term_months", String(p.term_months));
    if (p.tum_kayitlar) q.set("tum_kayitlar", "true");
    const s = q.toString();
    return request<FinansmanOranlari>(
      `/api/finansman-oranlari${s ? `?${s}` : ""}`);
  },
  bankaFinansmanOzeti: (slug: string) =>
    request<BankaFinansmanOzeti>(
      `/api/finansman-oranlari/${encodeURIComponent(slug)}`),
  campaigns: (params: CampaignParams = {}) => {
    const p = new URLSearchParams();
    for (const [ad, deger] of Object.entries(params)) {
      if (deger !== undefined && deger !== null && deger !== "") {
        p.set(ad, String(deger));
      }
    }
    const q = p.toString();
    return request<CampaignSummary[]>(`/api/campaigns${q ? `?${q}` : ""}`);
  },
  /**
   * `campaigns()` ile AYNI uç, ama süzgeç sonrası TOPLAMI da döndürür
   * (`X-Toplam-Kayit` başlığı).
   *
   * Ayrı bir metot çünkü toplam çağıranların çoğunu ilgilendirmiyor ve
   * `campaigns()`in dönüş tipini değiştirmek her çağıranı kırardı. Belge
   * seçici bu sayıya muhtaç: "1774 belgeden 50'si gösteriliyor" cümlesi,
   * kullanıcının listeyi tam sanmasını engelleyen tek şey.
   */
  campaignsSayfa: (params: CampaignParams = {}) => {
    const p = new URLSearchParams();
    for (const [ad, deger] of Object.entries(params)) {
      if (deger !== undefined && deger !== null && deger !== "") {
        p.set(ad, String(deger));
      }
    }
    const q = p.toString();
    return istek<CampaignSummary[]>(`/api/campaigns${q ? `?${q}` : ""}`);
  },
  /**
   * Gruplu arama — bankalar, belgeler, kampanya türleri tek istekte.
   *
   * Eşleştirme SUNUCUDA yapılır: Türkçe katlama kuralı (`tr_fold_ascii`) veri
   * katmanına aittir ve TSX'e kopyalansaydı iki yerde yaşardı. İstemcideki
   * `lib/arama.ts` aynı katlamayı YALNIZCA vurgulama ve yerinde daraltma için
   * uygular; ikisinin aynı sonucu verdiği ortak bir fikstürle kanıtlanır.
   *
   * Boş sorgu boş sonuç döndürür — uç, tuş başına çağrılıyor.
   */
  search: (q: string, limit?: number) => {
    const p = new URLSearchParams({ q });
    if (limit !== undefined) p.set("limit", String(limit));
    return request<AramaSonucu>(`/api/search?${p.toString()}`);
  },
  /**
   * Korpusun sayısal özeti. Kampanya türü listesi buradan gelir — eskiden
   * `/campaigns` yanıtından türetiliyordu ve bu, sırf bir `<select>` doldurmak
   * için 10 MB indirmek demekti.
   */
  stats: () => request<Stats>("/api/stats"),
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
  /**
   * `goldId` verilirse yanıt bir `gold` bloğu kazanır: aynı belgenin altın
   * değerleri ve alan alan karşılaştırma kararı. Çıkarım yine GÖNDERİLEN
   * metin üzerinde koşar; sunucu altın kümeden yalnız referans okur.
   */
  extract: (text: string, bank: string, goldId?: string) =>
    request<ExtractResult>("/api/extract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, bank, gold_id: goldId ?? null }),
    }),
  /**
   * `context` = son turların durum kayıtları, YENİDEN ESKİYE sıralı.
   *
   * Sunucu durumsuzdur; sohbet hafızası bu dizide taşınır. Boş dizi
   * göndermek "bu yeni bir sohbet" demektir ve bugünkü (bağlamsız)
   * davranışın aynısını verir.
   */
  /**
   * `signal` İPTAL EDİLEBİLİRLİK içindir — donmuş yerel LLM kurtarılabilsin.
   *
   * ## Ölçülen risk
   *
   * Sunucu tarafındaki en kötü hâl kısa değil: `OLLAMA_TIMEOUT` varsayılanı
   * 180 sn ve duvar-saati ölçütü `LLM_DEADLINE_CARPANI = 1.5` ile çarpılıyor
   * (`extraction/llm/clients.py`), yani **270 sn**. İstemcide bundan KISA bir
   * zaman aşımı, sunucunun gerçekten teslim edeceği cevabı keserdi.
   *
   * Bu yüzden iki ayrı mekanizma var ve ikisi farklı işe yarıyor:
   *  - **İptal düğmesi**: kullanıcının kararı, anında, tahmine gerek yok.
   *  - **Zaman aşımı**: yalnız EMNİYET AĞI, sunucu bütçesinin ÜSTÜNDE
   *    (bkz. `SOHBET_ZAMAN_ASIMI_MS`). Kullanıcı ekrandan ayrılsa bile
   *    arayüz kalıcı olarak «cevap bekleniyor» hâlinde donmasın.
   */
  chat: (question: string, context: ChatContext[] = [],
         opts?: { signal?: AbortSignal }) =>
    request<ChatResp>("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, context }),
      signal: opts?.signal,
    }),

  /**
   * Veri tazeleme — sistemin ağa çıkabilen TEK yolu, ayrı bir operatör
   * eylemidir. Soru-cevap yolu (kıyas, sohbet, çelişki) buraya hiç uğramaz
   * ve önceden hazırlanmış veri tabanından okumaya devam eder.
   */
  refreshPreview: (bank: string) =>
    request<RefreshPreview>(
      `/api/refresh/preview?${new URLSearchParams({ bank }).toString()}`,
    ),
  refreshStart: (bank: string) =>
    request<RefreshJob>("/api/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bank }),
    }),
  refreshStatus: (jobId: string) =>
    request<RefreshJob>(`/api/refresh/status/${encodeURIComponent(jobId)}`),
  refreshCancel: (jobId: string) =>
    request<RefreshJob>(`/api/refresh/cancel/${encodeURIComponent(jobId)}`, {
      method: "POST",
    }),
  /**
   * Her banka için en son tazelemenin kalıcı özeti (bkz. `RefreshSonOzet`).
   * Hiç tazeleme yapılmamışsa boş bir nesne döner, hata FIRLATMAZ.
   */
  refreshLastSummary: () =>
    request<RefreshSonOzetHaritasi>("/api/refresh/last-summary"),

  /**
   * Özet kapsam sayaçları. Model ÇAĞIRMAZ, ağa çıkmaz.
   *
   * Sayaç eskiden `/campaigns` yanıtından istemcide hesaplanıyordu. Artık
   * sunucudan geliyor çünkü kovaların ayrımı ("içerik yok" / "üretilemedi" /
   * "denenmedi") `ozet_sebep` etiketlerinin sınıflandırmasına dayanıyor ve o
   * kural özet katmanına ait — TSX'e kopyalansaydı iki yerde yaşardı.
   */
  summaryCoverage: () => request<OzetKapsam>("/api/summaries/coverage"),
  summaryBuild: () =>
    request<OzetIsi>("/api/summaries/build", { method: "POST" }),
  summaryStatus: (jobId: string) =>
    request<OzetIsi>(`/api/summaries/status/${encodeURIComponent(jobId)}`),
  summaryCancel: (jobId: string) =>
    request<OzetIsi>(`/api/summaries/cancel/${encodeURIComponent(jobId)}`, {
      method: "POST",
    }),

  /** Gelecek faz uçlarının sözleşmesi — Ayarlar ekranı bunu çizer. */
  adminPlan: () => request<AdminPlan>("/api/admin/plan"),

  /**
   * İşlem günlüğü — süzülmüş, sayfalanmış denetim kaydı.
   *
   * `campaignsSayfa()` ile aynı gerekçeyle `istek()` kullanır: toplam kayıt
   * sayısı gövdede değil `X-Toplam-Kayit` başlığındadır ve panel "480
   * kayıttan 50'si" cümlesini kurabilmek için ona muhtaç. Toplamı bilmeyen
   * bir liste, kullanıcının günlüğü tam sandığı tek yerdir.
   *
   * Varsayılan süzgeç sunucudadır (`yalniz_yazanlar=true`) ve buradan da
   * tekrarlanmaz: iki yerde yaşayan bir varsayılan, bir gün ayrışır.
   */
  gunlukSayfa: (params: GunlukParams = {}) => {
    const p = new URLSearchParams();
    for (const [ad, deger] of Object.entries(params)) {
      if (deger !== undefined && deger !== null && deger !== "") {
        p.set(ad, String(deger));
      }
    }
    const q = p.toString();
    return istek<GunlukKaydi[]>(`/api/log${q ? `?${q}` : ""}`);
  },

  /**
   * Altın kümedeki ZOR belgeler. Metin listeyle birlikte gelir: seçilen
   * vakayı ikinci bir çağrıyla çekmek jüriye her tıklamada bir ağ turu daha
   * bekletirdi.
   */
  zorVakalar: () => request<ZorVakaListesi>("/api/zor-vakalar"),
};

/** ApiError olmayan hataları da kullanıcıya gösterilebilir hale getirir. */
export function toDisplayError(e: unknown): { message: string; hint: string } {
  if (e instanceof ApiError) return { message: e.message, hint: e.hint };
  if (e instanceof Error) return { message: e.message, hint: "" };
  return { message: "Bilinmeyen hata.", hint: "" };
}

/* ------------------------------------------------------------------ *
 * Zor vaka tezgâhı — altın kümedeki zor belgeler ve karşılaştırma
 * ------------------------------------------------------------------ */

/** Zor-vaka etiketi + belge sayısı. Sıra sunucudan gelir, sayımdan değil. */
export type ZorEtiket = {
  etiket: string;
  ad: string;
  aciklama: string;
  adet: number;
};

export type ZorVaka = {
  id: string;
  banka: string;
  banka_adi: string;
  kaynak_adresi: string | null;
  kampanya_turu: string | null;
  zor_etiketler: string[];
  metin: string;
  metin_uzunlugu: number;
  onizleme: string;
  altin_alan_sayisi: number;
  altinda_yok_sayisi: number;
  belirsiz_alanlar: { field: string; label: string }[];
  kanitli_alanlar: string[];
};

export type ZorVakaListesi = {
  /** Altın küme dosyası okunabildi mi — okunamadıysa ekran bunu söyler. */
  kaynak_var: boolean;
  toplam_belge: number;
  zor_belge: number;
  etiketler: ZorEtiket[];
  vakalar: ZorVaka[];
};

/**
 * Bir alanın altın küme karşısındaki durumu.
 *
 * `fabricated` ayrı tutulur: altın küme o alan için "kontrol ettim, YOK"
 * diyorsa üretilen değer yanlış bir değer değil, bir uydurmadır.
 * `out_of_scope` metrik dışıdır — referans olmayan yerde doğru/yanlış
 * denemez.
 */
export type GoldDurum =
  | "match"
  | "equivalent"
  | "mismatch"
  | "missed"
  | "fabricated"
  | "correct_absence"
  | "unclear"
  | "out_of_scope";

export type GoldAlan = {
  field: string;
  label: string;
  gold_value: unknown;
  gold_present: boolean;
  gold_absent: boolean;
  /**
   * Altın değerin belgede birebir geçen dayanağı.
   *
   * Anotatör notları burada YOKTUR: iç yazışma dilinde yazılmışlar (kılavuz
   * bölüm numaraları, ham alan adları) ve ekrana basılsalardı ürünün içinden
   * geliştirme notu sızardı.
   */
  gold_span: string | null;
  status: GoldDurum;
  reason: string;
};

export type GoldKarsilastirma = {
  id: string;
  bank: string | null;
  source_url: string | null;
  campaign_type: string | null;
  hard_tags: string[];
  /** Çıkarımın koştuğu metin altın belgeyle aynı mı (elle değiştirildi mi). */
  text_matches: boolean;
  fields: GoldAlan[];
  summary: Record<GoldDurum, number>;
};
