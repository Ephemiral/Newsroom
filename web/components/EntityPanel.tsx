'use client';

import { useEffect, useMemo, useState } from 'react';
import { EntityRecord, EventEntity, ConfidenceTier } from '@/lib/types';

/* ── Entity card side panel (STAGE_7) ─────────────────────────────────────────
 * Renders one entity from the persistent store: image (with mandatory credit),
 * summary, roles, connections, facts grouped by confidence tier (tier label
 * always visible; person allegations always "Alleged by X →"), relevance to
 * the open story, and an "Updated" marker driven by localStorage last-visit.
 */

const TYPE_LABEL: Record<string, string> = {
  person: 'Person',
  organization: 'Organization',
  political_party: 'Political party',
  technology: 'Technology',
  location: 'Location',
  other: 'Entity',
};

const TIER: Record<ConfidenceTier, { label: string; color: string; bg: string; border: string; tooltip: string }> = {
  verified: {
    label: 'Verified', color: '#2f7a4a', bg: '#eaf3ec', border: '#bcdcc4',
    tooltip: 'Established across independent sources over time.',
  },
  reported: {
    label: 'Reported', color: '#5b7fa6', bg: '#eef3f8', border: '#c6d6e6',
    tooltip: 'Credibly reported, limited corroboration.',
  },
  disputed: {
    label: 'Disputed', color: '#c2682f', bg: '#fbf0e2', border: '#eccfa6',
    tooltip: 'The subject denies this, or credible contradicting reporting exists.',
  },
  allegation: {
    label: 'Allegation', color: '#b83c34', bg: '#fdf0ef', border: '#f0c0bc',
    tooltip: 'Explicitly unproven. Attributed to the source that made it — not established fact.',
  },
};

const TIER_ORDER: ConfidenceTier[] = ['verified', 'reported', 'disputed', 'allegation'];

const LAST_SEEN_KEY = 'critiqal_entity_last_seen';

function readLastSeen(): Record<string, string> {
  try {
    return JSON.parse(localStorage.getItem(LAST_SEEN_KEY) ?? '{}');
  } catch {
    return {};
  }
}

/** True when the entity's change_log has entries newer than the reader's last visit. */
export function entityHasUpdates(record: EntityRecord, lastSeenIso: string | undefined): boolean {
  if (!lastSeenIso) return false; // first visit: everything is "new", flag nothing
  const last = record.change_log[record.change_log.length - 1]?.date;
  return !!last && last > lastSeenIso.slice(0, 10);
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p style={{
      font: '600 10px/1 var(--font-archivo), system-ui',
      letterSpacing: '.14em', textTransform: 'uppercase', color: '#a3957f',
      margin: '0 0 8px',
    }}>
      {children}
    </p>
  );
}

function TierBadge({ tier }: { tier: ConfidenceTier }) {
  const cfg = TIER[tier];
  return (
    <span title={cfg.tooltip} style={{
      display: 'inline-block', padding: '2px 7px', borderRadius: 4,
      background: cfg.bg, border: `1px solid ${cfg.border}`,
      font: '600 9px/1.2 var(--font-archivo), system-ui',
      letterSpacing: '.06em', textTransform: 'uppercase', color: cfg.color,
      cursor: 'help', flexShrink: 0,
    }}>
      {cfg.label}
    </span>
  );
}

interface EntityPanelProps {
  record: EntityRecord;
  eventEntity?: EventEntity;
  /** Names for connection targets so edges render as readable links. */
  relatedNames?: Record<string, string>;
  onNavigate?: (entityId: string) => void;
  onClose: () => void;
}

export default function EntityPanel({ record, eventEntity, relatedNames, onNavigate, onClose }: EntityPanelProps) {
  const [hasUpdates, setHasUpdates] = useState(false);

  // Updated marker: compare change_log to this reader's stored last visit,
  // then record the visit (session-based; no accounts by design).
  useEffect(() => {
    const seen = readLastSeen();
    setHasUpdates(entityHasUpdates(record, seen[record.entity_id]));
    seen[record.entity_id] = new Date().toISOString();
    try {
      localStorage.setItem(LAST_SEEN_KEY, JSON.stringify(seen));
    } catch { /* storage unavailable — marker simply stays off */ }
  }, [record.entity_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const factsByTier = useMemo(() => {
    const groups = new Map<ConfidenceTier, typeof record.facts>();
    for (const tier of TIER_ORDER) {
      const facts = record.facts.filter(f => f.confidence_tier === tier);
      if (facts.length) groups.set(tier, facts);
    }
    return groups;
  }, [record]);

  // Roles: dedupe by label (Wikidata repeats a position once per term) and
  // collect the distinct citation URLs so we show one source link, not one
  // identical link per role.
  const roles = useMemo(() => {
    const seen = new Set<string>();
    const out: typeof record.roles_affiliations = [];
    for (const r of record.roles_affiliations) {
      const key = r.role.trim().toLowerCase();
      if (key && !seen.has(key)) { seen.add(key); out.push(r); }
    }
    return out;
  }, [record]);
  const roleSources = useMemo(
    () => [...new Set(record.roles_affiliations.map(r => r.source_url).filter(Boolean))],
    [record],
  );

  const lastChange = record.change_log[record.change_log.length - 1];

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{ position: 'fixed', inset: 0, background: 'rgba(20,17,9,.25)', zIndex: 40 }}
      />
      {/* Panel */}
      <aside style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, zIndex: 41,
        width: 'min(420px, 92vw)', overflowY: 'auto',
        background: '#f7f4ee', borderLeft: '1px solid #d9cfbd',
        boxShadow: '-8px 0 30px rgba(20,17,9,.12)',
        padding: '20px 22px 40px',
      }}>
        {/* Header row */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
          <span style={{
            font: '600 10px/1 var(--font-archivo), system-ui',
            letterSpacing: '.16em', textTransform: 'uppercase', color: '#b08a4a',
          }}>
            {TYPE_LABEL[record.type] ?? TYPE_LABEL.other}
            {hasUpdates && (
              <span style={{
                marginLeft: 8, padding: '2px 6px', borderRadius: 4,
                background: '#2f5fd0', color: '#fff', letterSpacing: '.08em',
              }}>
                Updated
              </span>
            )}
          </span>
          <button
            onClick={onClose}
            aria-label="Close entity card"
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              font: '400 20px/1 var(--font-archivo), system-ui', color: '#8a7d6c', padding: 4,
            }}
          >
            ×
          </button>
        </div>

        {/* Image — attribution is a license requirement */}
        {record.image && (
          <figure style={{ margin: '0 0 14px' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={record.image.url}
              alt={record.canonical_name}
              style={{
                // contain (not cover) so a portrait is never cropped through the
                // face; the neutral background fills any letterbox margin.
                width: '100%', height: 240, objectFit: 'contain', objectPosition: 'center',
                borderRadius: 4, border: '1px solid #e1d8c8', background: '#ece6da',
              }}
            />
            <figcaption style={{
              font: '400 10px/1.5 var(--font-archivo), system-ui', color: '#a3957f', marginTop: 6,
            }}>
              {record.image.credit} ·{' '}
              <a href={record.image.license_url ?? record.image.source_page}
                 style={{ color: '#a3957f' }} target="_blank" rel="noreferrer">
                {record.image.license}
              </a>
              {' · '}
              <a href={record.image.source_page} style={{ color: '#a3957f' }} target="_blank" rel="noreferrer">
                {record.image.provider}
              </a>
            </figcaption>
          </figure>
        )}

        {/* Name + summary */}
        <h2 style={{
          fontFamily: 'var(--font-spectral), serif', fontWeight: 600,
          fontSize: 24, lineHeight: 1.2, color: '#141109', margin: '0 0 10px',
        }}>
          {record.canonical_name}
        </h2>
        {record.summary && (
          <p style={{
            fontFamily: 'var(--font-spectral), serif', fontSize: 15, lineHeight: 1.6,
            color: '#5b5249', margin: '0 0 6px',
          }}>
            {record.summary}
            {record.summary_sources[0] && (
              <>
                {' '}
                <a href={record.summary_sources[0]} target="_blank" rel="noreferrer"
                   style={{ color: '#b08a4a', fontSize: 12 }}>
                  source →
                </a>
              </>
            )}
          </p>
        )}

        {/* Relevance to this story */}
        {eventEntity?.relevance_to_event && (
          <div style={{
            margin: '16px 0', padding: '10px 14px',
            background: '#f2ede4', border: '1px solid #e2d7c2', borderRadius: 4,
          }}>
            <SectionLabel>In this story</SectionLabel>
            <p style={{
              fontFamily: 'var(--font-spectral), serif', fontSize: 14, lineHeight: 1.6,
              color: '#5b5249', margin: 0,
            }}>
              {eventEntity.relevance_to_event}
            </p>
            {eventEntity.relevance_grounding === 'sources_fallback' && (
              <p style={{
                fontFamily: 'var(--font-spectral), serif', fontStyle: 'italic',
                fontSize: 12, color: '#a3957f', margin: '6px 0 0',
              }}>
                Relevance derived from this event&apos;s summary and sources.
              </p>
            )}
          </div>
        )}

        {/* Roles — deduped; one shared source link rather than one per row */}
        {roles.length > 0 && (
          <div style={{ margin: '18px 0' }}>
            <SectionLabel>Roles &amp; affiliations</SectionLabel>
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {roles.map((r, i) => (
                <li key={i} style={{
                  fontFamily: 'var(--font-spectral), serif', fontSize: 14, lineHeight: 1.5, color: '#5b5249',
                }}>
                  {r.role}
                  {(r.start || r.end) && (
                    <span style={{ color: '#a3957f' }}> ({r.start ?? '…'}–{r.end ?? 'present'})</span>
                  )}
                </li>
              ))}
            </ul>
            {roleSources.length > 0 && (
              <p style={{ font: '400 11px/1.5 var(--font-archivo), system-ui', color: '#a3957f', marginTop: 6 }}>
                Source:{' '}
                {roleSources.map((u, i) => (
                  <span key={u}>
                    {i > 0 && ', '}
                    <a href={u} target="_blank" rel="noreferrer" style={{ color: '#b08a4a' }}>
                      Wikidata{roleSources.length > 1 ? ` ${i + 1}` : ''} →
                    </a>
                  </span>
                ))}
              </p>
            )}
          </div>
        )}

        {/* Connections */}
        {record.connections.length > 0 && (
          <div style={{ margin: '18px 0' }}>
            <SectionLabel>Connections</SectionLabel>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
              {record.connections.map((c, i) => (
                <button
                  key={i}
                  onClick={() => onNavigate?.(c.entity_id)}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 5,
                    padding: '4px 10px', background: '#f2ede4',
                    border: '1px solid #e2d7c2', borderRadius: 20, cursor: onNavigate ? 'pointer' : 'default',
                    font: '500 11px/1.3 var(--font-archivo), system-ui', color: '#5b5249',
                  }}
                >
                  <span style={{ color: '#a3957f' }}>{c.type.replace(/_/g, ' ')}:</span>
                  {relatedNames?.[c.entity_id] ?? c.entity_id.replace(/^ent_[a-z_]*?_/, '').replace(/_/g, ' ')}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Facts by tier — tier label ALWAYS adjacent (safety gate rule 2) */}
        {factsByTier.size > 0 && (
          <div style={{ margin: '18px 0' }}>
            <SectionLabel>On the record</SectionLabel>
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 10 }}>
              {[...factsByTier.entries()].map(([tier, facts]) =>
                facts.map(f => (
                  <li key={f.fact_id} style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <TierBadge tier={tier} />
                    <span style={{
                      fontFamily: 'var(--font-spectral), serif', fontSize: 14, lineHeight: 1.55, color: '#5b5249',
                    }}>
                      {tier === 'allegation' && f.attributed_to && (
                        <em style={{ color: '#b83c34' }}>Alleged by {f.attributed_to}: </em>
                      )}
                      {f.text}
                      {' '}
                      <a href={f.source_url} target="_blank" rel="noreferrer" style={{ color: '#b08a4a', fontSize: 11 }}>→</a>
                    </span>
                  </li>
                )),
              )}
            </ul>
          </div>
        )}

        {/* Footer: change history */}
        {lastChange && (
          <p style={{
            font: '400 10px/1.6 var(--font-archivo), system-ui', color: '#a3957f',
            borderTop: '1px solid #e7e0d4', paddingTop: 12, marginTop: 22,
          }}>
            Updated {lastChange.date} — {lastChange.summary_of_change}
            <br />
            Background compiled from cited public sources; nothing on this card is asserted without a link.
          </p>
        )}
      </aside>
    </>
  );
}
