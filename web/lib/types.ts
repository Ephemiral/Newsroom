// Types matching the per-event JSON schema v0.2

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
