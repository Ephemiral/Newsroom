// Types matching the per-event JSON schema (v0.5) and the entity store (v0.1)

export type BiasRating = 'left' | 'center-left' | 'center' | 'center-right' | 'right';
/**
 * agreed       — supported by sources from at least two distinct bias tiers spanning
 *                the spectrum (e.g. left + center, or center + center-right).
 * corroborated — supported by multiple sources, but all from the same side of the spectrum.
 * contested    — sources explicitly conflict or frame the fact incompatibly across bias tiers.
 * single_source — only one source in the cluster reported this.
 */
export type Classification = 'agreed' | 'corroborated' | 'contested' | 'single_source';

export interface Source {
  source_id: string;
  outlet: string;
  url: string;
  author: string | null;
  published_at: string;
  bias_rating: BiasRating;
  bias_rating_source: string;
  /** Set for government-controlled/aligned outlets, e.g. "Russian state-controlled".
   *  A separate axis from left/right bias; always surfaced to the reader (B-17). */
  state_alignment?: string | null;
  ownership: string | null;
  author_background: string | null;
  amplification_signal: null;
}

export interface FramingVariant {
  source_id: string;
  characterization: string;
}

export interface Claim {
  claim_id: string;
  text: string;
  classification: Classification;
  /** "actor" when the contradiction is between the actors named in the claim
   *  (e.g. two governments giving conflicting accounts) rather than between
   *  outlets. For these, contested_by is usually empty by design — every
   *  outlet in supported_by corroborates that the dispute exists. (v0.4) */
  dispute_type?: 'actor' | null;
  /** Thematic group in snake_case, e.g. "territorial_control". Null/absent if ungrouped. */
  claim_group?: string | null;
  supported_by: string[];
  contested_by: string[];
  rationale: string;
  framing_variants: FramingVariant[];
}

export interface BackgroundPoint {
  point: string;
  sources: string[];
}

/** Openly-licensed file photo (schema v0.3). Attribution fields must be
 *  rendered wherever the image is shown — this is a license requirement. */
export interface EventImage {
  url: string;
  full_url: string;
  source_page: string;
  width: number;
  height: number;
  caption: string;
  credit: string;
  license: string;
  license_url: string | null;
  provider: string;
  file_title: string;
  query: string;
  fetched_at: string;
}

export interface EventMeta {
  cluster_id: string;
  beat: string;
  title: string;
  summary: string;
  date: string;
  generated_at: string;
  /** Present from schema v0.3; null when no suitable image was found. */
  image?: EventImage | null;
  image_attempted_at?: string;
  /** Earlier events this one develops (shared articles) — "Earlier coverage". */
  related_events?: { cluster_id: string; title: string }[];
  /** Entity references for this event (schema v0.5); absent on older events. */
  entities?: EventEntity[];
}

export interface ReportParagraph {
  paragraph_id: string;
  text: string;
  supports: {
    claim_ids: string[];
    source_ids: string[];
  };
  kind: 'agreed' | 'contested' | 'framing' | 'one_sided' | 'background';
}

export interface Report {
  schema_version: string;
  generated_at: string;
  paragraphs: ReportParagraph[];
}

export interface AnalyzedEvent {
  schema_version: string;
  event: EventMeta;
  sources: Source[];
  claims: Claim[];
  background: BackgroundPoint[];
  report: Report | null;
}

// ── Entity cards (schema v0.5 event block + entity store v0.1, STAGE_7) ──────

export type EntityType =
  | 'person' | 'organization' | 'political_party' | 'technology' | 'location' | 'other';

export type ConfidenceTier = 'verified' | 'reported' | 'disputed' | 'allegation';

/** Per-event entity reference (event.entities[]). `surfaces` are the exact
 *  strings in this event's report text — the frontend makes them clickable by
 *  string matching (no character offsets; robust to report regeneration). */
export interface EventEntity {
  entity_id: string;
  surfaces: string[];
  relevance_to_event: string | null;
  relevance_supports: { claim_ids: string[]; source_ids: string[] };
  /** "claims" when receipts link to claims; "sources_fallback" per B-10 clause. */
  relevance_grounding: 'claims' | 'sources_fallback';
}

/** Openly-licensed entity image (Wikidata P18 → Commons). Attribution fields
 *  must be rendered wherever the image is shown — license requirement. */
export interface EntityImage {
  url: string;
  source_page: string;
  credit: string;
  license: string;
  license_url: string | null;
  provider: string;
  file_title: string;
  fetched_at: string;
}

export interface EntityFact {
  fact_id: string;
  text: string;
  source_url: string;
  source_type: string;
  /** Outlet/source name for allegations ("Alleged by X →"); required on person allegations. */
  attributed_to?: string | null;
  first_reported: string;
  last_updated: string;
  confidence_tier: ConfidenceTier;
  supersedes: string | null;
  contradicted_by: string | null;
}

export interface EntityRole {
  role: string;
  org_entity_id: string | null;
  start: string | null;
  end: string | null;
  source_url: string;
  source_type: string;
}

export interface EntityConnection {
  type: string;
  entity_id: string;
  note: string | null;
  source_url: string;
}

export interface EntityChange {
  date: string;
  summary_of_change: string;
  source: string | null;
}

/** One record in the persistent entity store (data/entities/{entity_id}.json). */
export interface EntityRecord {
  entity_schema_version: string;
  entity_id: string;
  type: EntityType;
  canonical_name: string;
  aliases: string[];
  wikidata_qid: string | null;
  summary: string | null;
  summary_sources: string[];
  image: EntityImage | null;
  roles_affiliations: EntityRole[];
  connections: EntityConnection[];
  facts: EntityFact[];
  review_status: 'auto' | 'pending_review' | 'approved';
  first_seen_event: string;
  appears_in_events: string[];
  created_at: string;
  last_updated: string;
  change_log: EntityChange[];
}
