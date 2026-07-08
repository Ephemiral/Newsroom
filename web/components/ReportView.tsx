'use client';

import { useState } from 'react';
import { Report, ReportParagraph, Claim, Source, EventImage } from '@/lib/types';
import EventImageFigure from '@/components/EventImageFigure';

// ── Kind config — warm palette matching the Critiqal design ──────────────────

const KIND = {
  agreed: {
    bar: '#b9d4bf', barActive: '#2f7a4a',
    badgeBg: '#eaf3ec', badgeBorder: '#bcdcc4',
    accent: '#2f7a4a', label: 'Agreed',
    tooltip: 'Reported consistently by outlets spanning different sides of the political spectrum.',
  },
  contested: {
    bar: '#e8c79a', barActive: '#c2682f',
    badgeBg: '#fbf0e2', badgeBorder: '#eccfa6',
    accent: '#c2682f', label: 'Contested',
    tooltip: 'Sources conflict or frame this fact in incompatible ways across the spectrum.',
  },
  framing: {
    bar: '#c8c2e6', barActive: '#6a5fbf',
    badgeBg: '#f0eef9', badgeBorder: '#d3cdee',
    accent: '#6a5fbf', label: 'Framing',
    tooltip: 'The same fact is characterised differently across outlets — a difference in emphasis, not a factual dispute.',
  },
  one_sided: {
    bar: '#f5c6c2', barActive: '#b83c34',
    badgeBg: '#fdf0ef', badgeBorder: '#f0c0bc',
    accent: '#b83c34', label: 'One-sided',
    tooltip: "Reported by only one part of the political spectrum. The other side's choice not to cover this is itself informative.",
  },
  background: {
    bar: '#ddd5c7', barActive: '#8a7d6c',
    badgeBg: '#f2ede4', badgeBorder: '#ddd2c0',
    accent: '#8a7d6c', label: 'Background',
    tooltip: 'Contextual information that helps explain the current event.',
  },
} satisfies Record<ReportParagraph['kind'], {
  bar: string; barActive: string;
  badgeBg: string; badgeBorder: string;
  accent: string; label: string; tooltip: string;
}>;

const BIAS_DOT: Record<string, string> = {
  left:           '#2f5fd0',
  'center-left':  '#5b8def',
  center:         '#8a8a8a',
  'center-right': '#e08a3c',
  right:          '#d24b3e',
};

// ── Kind badge with hover tooltip ─────────────────────────────────────────────

function KindBadge({ kind }: { kind: ReportParagraph['kind'] }) {
  const cfg = KIND[kind] ?? KIND.background;
  return (
    <span
      className="relative group"
      style={{
        display: 'inline-block',
        padding: '3px 8px',
        borderRadius: 4,
        background: cfg.badgeBg,
        border: `1px solid ${cfg.badgeBorder}`,
        font: '600 10px/1 var(--font-archivo), system-ui',
        letterSpacing: '.07em',
        textTransform: 'uppercase',
        color: cfg.accent,
        cursor: 'help',
      }}
    >
      {cfg.label}
      <span className="
        pointer-events-none absolute bottom-full left-0 mb-2 w-56
        bg-gray-800 text-white text-xs rounded-md px-2.5 py-2 leading-snug
        opacity-0 group-hover:opacity-100 transition-opacity duration-150 z-20
      ">
        {cfg.tooltip}
      </span>
    </span>
  );
}

// ── Source chip ───────────────────────────────────────────────────────────────

function SourceChip({ src }: { src: Source }) {
  const dot = BIAS_DOT[src.bias_rating] ?? '#8a8a8a';
  return (
    <span
      title={src.state_alignment ?? undefined}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        padding: '3px 8px',
        background: '#f2ede4', border: '1px solid #e2d7c2',
        borderRadius: 20,
        font: '500 11px/1 var(--font-archivo), system-ui',
        color: '#5b5249',
      }}
    >
      <span style={{ width: 7, height: 7, borderRadius: '50%', background: dot, flexShrink: 0, display: 'inline-block' }} />
      {src.state_alignment ? `⚑ ${src.outlet}` : src.outlet}
    </span>
  );
}

// ── Receipt ───────────────────────────────────────────────────────────────────

function Receipt({
  paragraph, claimsMap, sourceMap,
}: {
  paragraph: ReportParagraph;
  claimsMap: Record<string, Claim>;
  sourceMap: Record<string, Source>;
}) {
  const claims = paragraph.supports.claim_ids.map(id => claimsMap[id]).filter(Boolean);

  if (paragraph.kind === 'contested') {
    const supportingIds: string[] = [];
    const contestingIds: string[] = [];
    claims.forEach(claim => {
      claim.supported_by.forEach(id => supportingIds.push(id));
      claim.contested_by.forEach(id => contestingIds.push(id));
    });

    const supportingOutlets = new Set<string>();
    const seenSupport = new Set<string>();
    const supporting: Source[] = [];
    supportingIds.forEach(id => {
      const s = sourceMap[id];
      if (s && !seenSupport.has(s.outlet)) { seenSupport.add(s.outlet); supportingOutlets.add(s.outlet); supporting.push(s); }
    });

    const seenContest = new Set<string>();
    const contesting: Source[] = [];
    contestingIds.forEach(id => {
      const s = sourceMap[id];
      if (s && !seenContest.has(s.outlet) && !supportingOutlets.has(s.outlet)) {
        seenContest.add(s.outlet); contesting.push(s);
      }
    });

    const splitOutlets = new Set<string>();
    contestingIds.forEach(id => {
      const s = sourceMap[id];
      if (s && supportingOutlets.has(s.outlet)) splitOutlets.add(s.outlet);
    });

    const hasTwoSides = supporting.length > 0 && contesting.length > 0;

    return (
      <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e7ddd0', display: 'flex', flexDirection: 'column', gap: 16 }}>
        {claims.length > 0 && (
          <div>
            <p style={{ font: '600 10px/1 var(--font-archivo), system-ui', letterSpacing: '.14em', textTransform: 'uppercase', color: '#a3957f', marginBottom: 10 }}>Supporting claims</p>
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {claims.map(claim => (
                <li key={claim.claim_id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                  <span style={{ marginTop: 7, width: 5, height: 5, borderRadius: '50%', background: '#c8bfae', flexShrink: 0, display: 'inline-block' }} />
                  <span style={{ fontFamily: 'var(--font-spectral), serif', fontSize: 14, lineHeight: 1.5, color: '#5b5249' }}>{claim.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
        {(supporting.length > 0 || contesting.length > 0) && (
          <div>
            <p style={{ font: '600 10px/1 var(--font-archivo), system-ui', letterSpacing: '.14em', textTransform: 'uppercase', color: '#a3957f', marginBottom: 10 }}>
              {hasTwoSides ? 'Contention' : 'Sources'}
            </p>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {supporting.map(src => <SourceChip key={src.source_id} src={src} />)}
              </div>
              {hasTwoSides && <span style={{ font: '600 12px/1 var(--font-archivo), system-ui', color: '#a3957f' }}>↔</span>}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {contesting.map(src => <SourceChip key={src.source_id} src={src} />)}
              </div>
            </div>
            {splitOutlets.size > 0 && (
              <p style={{ fontFamily: 'var(--font-spectral), serif', fontStyle: 'italic', fontSize: 13, color: '#a3957f', marginTop: 8 }}>
                {[...splitOutlets].join(', ')} {splitOutlets.size === 1 ? 'published articles on both sides.' : 'each published articles on both sides.'}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  const sourcesRaw = paragraph.supports.source_ids.map(id => sourceMap[id]).filter(Boolean);
  const seen = new Set<string>();
  const sources = sourcesRaw.filter(s => seen.has(s.outlet) ? false : (seen.add(s.outlet), true));

  return (
    <div style={{ marginTop: 16, paddingTop: 16, borderTop: '1px solid #e7ddd0', display: 'flex', flexDirection: 'column', gap: 16 }}>
      {claims.length > 0 && (
        <div>
          <p style={{ font: '600 10px/1 var(--font-archivo), system-ui', letterSpacing: '.14em', textTransform: 'uppercase', color: '#a3957f', marginBottom: 10 }}>Supporting claims</p>
          <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {claims.map(claim => (
              <li key={claim.claim_id} style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
                <span style={{ marginTop: 7, width: 5, height: 5, borderRadius: '50%', background: '#c8bfae', flexShrink: 0, display: 'inline-block' }} />
                <span style={{ fontFamily: 'var(--font-spectral), serif', fontSize: 14, lineHeight: 1.5, color: '#5b5249' }}>{claim.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {sources.length > 0 && (
        <div>
          <p style={{ font: '600 10px/1 var(--font-archivo), system-ui', letterSpacing: '.14em', textTransform: 'uppercase', color: '#a3957f', marginBottom: 10 }}>Sources</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {sources.map(src => <SourceChip key={src.source_id} src={src} />)}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Paragraph card ────────────────────────────────────────────────────────────

function ParagraphCard({
  para, claimsMap, sourceMap, transparencyMode, isLede,
}: {
  para: ReportParagraph;
  claimsMap: Record<string, Claim>;
  sourceMap: Record<string, Source>;
  transparencyMode: boolean;
  isLede?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const cfg = KIND[para.kind] ?? KIND.background;
  const hasReceipt = para.supports.claim_ids.length > 0 || para.supports.source_ids.length > 0;

  return (
    <div style={{ paddingBottom: 20, borderBottom: '1px solid #ece5d9' }}>
      {transparencyMode && (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
          <KindBadge kind={para.kind} />
          {hasReceipt && (
            <button
              onClick={() => setExpanded(v => !v)}
              style={{
                background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                font: '500 11px/1 var(--font-archivo), system-ui',
                letterSpacing: '.04em', color: '#a3957f',
              }}
            >
              {expanded ? 'Hide sources' : 'Show sources'}
            </button>
          )}
        </div>
      )}
      <p
        className={isLede ? 'report-lede' : undefined}
        style={{
          fontFamily: 'var(--font-spectral), serif',
          fontSize: 16.5, lineHeight: 1.65, color: '#2a2319', margin: 0,
        }}
      >
        {para.text}
      </p>
      {expanded && transparencyMode && (
        <Receipt paragraph={para} claimsMap={claimsMap} sourceMap={sourceMap} />
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

interface ReportViewProps {
  report: Report;
  claimsMap: Record<string, Claim>;
  sourceMap: Record<string, Source>;
  /** Event file photo, rendered inside the article body rather than as a top hero. */
  image?: EventImage | null;
}

export default function ReportView({ report, claimsMap, sourceMap, image }: ReportViewProps) {
  const [transparencyMode, setTransparencyMode] = useState(false);

  // Place the image after the first paragraph — or the second when the opener
  // is a short one-liner, so the photo doesn't interrupt a two-line lede.
  const imageAfterIndex =
    image && report.paragraphs.length > 1 && (report.paragraphs[0]?.text?.length ?? 0) < 220
      ? 1
      : 0;

  return (
    <section style={{ marginBottom: 48 }}>

      {/* Raised cap on the lede's first letter (baseline-aligned, not a floating drop cap) */}
      <style>{`
        .report-lede::first-letter {
          font-family: var(--font-spectral), serif;
          font-size: 3.6em;
          font-weight: 700;
          line-height: 1;
          vertical-align: baseline;
        }
      `}</style>

      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, gap: 16, flexWrap: 'wrap' }}>
        <h2 style={{
          font: '600 13px/1 var(--font-archivo), system-ui',
          letterSpacing: '.04em', color: '#3a332a', margin: 0,
        }}>
          The report
        </h2>
        <button
          onClick={() => setTransparencyMode(v => !v)}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 9,
            background: 'none', border: 'none', cursor: 'pointer', padding: 0,
            font: '600 11px/1 var(--font-archivo), system-ui',
            letterSpacing: '.06em', textTransform: 'uppercase',
            color: transparencyMode ? '#2f5fd0' : '#8a7d6c',
            transition: 'color .2s',
          }}
        >
          {transparencyMode ? 'Sources on' : 'Show sources'}
          <span style={{
            position: 'relative', width: 32, height: 18, borderRadius: 9,
            background: transparencyMode ? '#2f5fd0' : '#ddd5c7',
            display: 'inline-block', flexShrink: 0,
            transition: 'background .2s',
          }}>
            <span style={{
              position: 'absolute', top: 2,
              left: transparencyMode ? 16 : 2,
              width: 14, height: 14, borderRadius: '50%',
              background: '#fff',
              boxShadow: '0 1px 2px rgba(0,0,0,.2)',
              transition: 'left .2s',
              display: 'block',
            }} />
          </span>
        </button>
      </div>

      {/* Kind legend */}
      {transparencyMode && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 20 }}>
          {(Object.entries(KIND) as [ReportParagraph['kind'], typeof KIND[keyof typeof KIND]][]).map(([kind]) => (
            <KindBadge key={kind} kind={kind} />
          ))}
        </div>
      )}

      {/* Paragraphs — continuous left rail, image woven in after the lede */}
      <div style={{ borderLeft: '2px solid #e7e0d4' }}>
        {report.paragraphs.map((para, i) => {
          const cfg = KIND[para.kind] ?? KIND.background;
          return (
            <div
              key={para.paragraph_id}
              style={{
                marginLeft: -2,
                borderLeft: `2px solid ${transparencyMode ? cfg.bar : '#e7e0d4'}`,
                transition: 'border-color .2s',
              }}
            >
              <div style={{ paddingLeft: 22, paddingTop: 16 }}>
                <ParagraphCard
                  para={para}
                  claimsMap={claimsMap}
                  sourceMap={sourceMap}
                  transparencyMode={transparencyMode}
                  isLede={i === 0}
                />
                {image && i === imageAfterIndex && (
                  <EventImageFigure image={image} />
                )}
              </div>
            </div>
          );
        })}
      </div>

    </section>
  );
}
