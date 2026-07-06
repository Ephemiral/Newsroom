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
