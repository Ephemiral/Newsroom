'use client';

import { useState } from 'react';
import { Report, ReportParagraph, Claim, Source } from '@/lib/types';

// ── Kind config ───────────────────────────────────────────────────────────────

const KIND = {
  agreed: {
    bar: '#86efac', barActive: '#16a34a',
    badge: 'bg-green-100 text-green-800', label: 'Agreed',
    tooltip: 'Reported consistently by outlets spanning different sides of the political spectrum.',
  },
  contested: {
    bar: '#fcd34d', barActive: '#d97706',
    badge: 'bg-amber-100 text-amber-800', label: 'Contested',
    tooltip: 'Sources conflict or frame this fact in incompatible ways across bias tiers.',
  },
  framing: {
    bar: '#a5b4fc', barActive: '#4f46e5',
    badge: 'bg-indigo-100 text-indigo-700', label: 'Framing',
    tooltip: 'The same fact is characterized differently across outlets — a difference in emphasis or language, not a factual dispute.',
  },
  one_sided: {
    bar: '#f9a8d4', barActive: '#db2777',
    badge: 'bg-pink-100 text-pink-700', label: 'One-sided',
    tooltip: 'Reported by only one part of the political spectrum. The other side\'s choice not to cover this is itself informative.',
  },
  background: {
    bar: '#cbd5e1', barActive: '#64748b',
    badge: 'bg-slate-100 text-slate-600', label: 'Background',
    tooltip: 'Contextual information — history, prior events, or legal context — that helps explain the current event.',
  },
} satisfies Record<ReportParagraph['kind'], { bar: string; barActive: string; badge: string; label: string; tooltip: string }>;

const BIAS_COLORS: Record<string, string> = {
  left:          'bg-blue-100 text-blue-700',
  'center-left': 'bg-sky-100 text-sky-700',
  center:        'bg-gray-100 text-gray-600',
  'center-right':'bg-orange-100 text-orange-700',
  right:         'bg-red-100 text-red-700',
};

// ── Kind badge with hover tooltip ─────────────────────────────────────────────

function KindBadge({ kind }: { kind: ReportParagraph['kind'] }) {
  const cfg = KIND[kind] ?? KIND.background;
  return (
    <span className={`relative group inline-block text-xs px-1.5 py-0.5 rounded font-medium cursor-help ${cfg.badge}`}>
      {cfg.label}
      <span className="
        pointer-events-none absolute bottom-full left-0 mb-1.5 w-56
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
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${BIAS_COLORS[src.bias_rating] ?? 'bg-gray-200 text-gray-700'}`}>
      {src.outlet}
    </span>
  );
}

// ── Receipt (collapsed by default, opened per-paragraph) ─────────────────────

function Receipt({
  paragraph,
  claimsMap,
  sourceMap,
}: {
  paragraph: ReportParagraph;
  claimsMap: Record<string, Claim>;
  sourceMap: Record<string, Source>;
}) {
  const claims = paragraph.supports.claim_ids.map(id => claimsMap[id]).filter(Boolean);

  // ── Contested layout: show two sides with ↔ separator ─────────────────────
  if (paragraph.kind === 'contested') {
    // Aggregate supporting and contesting source IDs across all cited claims
    const supportingIds: string[] = [];
    const contestingIds: string[] = [];
    claims.forEach(claim => {
      claim.supported_by.forEach(id => supportingIds.push(id));
      claim.contested_by.forEach(id => contestingIds.push(id));
    });

    // Deduplicate by outlet name; if an outlet appears on both sides, keep it on supporting only
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
        seenContest.add(s.outlet);
        contesting.push(s);
      }
    });

    // Outlets that appear on both sides — flag them
    const splitOutlets = new Set<string>();
    contestingIds.forEach(id => {
      const s = sourceMap[id];
      if (s && supportingOutlets.has(s.outlet)) splitOutlets.add(s.outlet);
    });

    const hasTwoSides = supporting.length > 0 && contesting.length > 0;

    return (
      <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
        {claims.length > 0 && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Supporting claims</p>
            <ul className="space-y-2">
              {claims.map(claim => (
                <li key={claim.claim_id} className="flex gap-2 items-start">
                  <span className="mt-2 w-1.5 h-1.5 rounded-full bg-gray-300 shrink-0" />
                  <span className="text-sm text-gray-700 leading-snug">{claim.text}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Contention row */}
        {(supporting.length > 0 || contesting.length > 0) && (
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">
              {hasTwoSides ? 'Contention' : 'Sources'}
            </p>
            <div className="flex items-center gap-3 flex-wrap">
              <div className="flex flex-wrap gap-1.5">
                {supporting.map(src => <SourceChip key={src.source_id} src={src} />)}
              </div>
              {hasTwoSides && (
                <span className="text-xs text-gray-400 font-semibold">↔</span>
              )}
              <div className="flex flex-wrap gap-1.5">
                {contesting.map(src => <SourceChip key={src.source_id} src={src} />)}
              </div>
            </div>
            {splitOutlets.size > 0 && (
              <p className="text-xs text-gray-400 mt-2 italic">
                {[...splitOutlets].join(', ')} {splitOutlets.size === 1 ? 'published articles on both sides of this contention.' : 'each published articles on both sides of this contention.'}
              </p>
            )}
          </div>
        )}
      </div>
    );
  }

  // ── Default layout (agreed / framing / one_sided / background) ────────────
  const sourcesRaw = paragraph.supports.source_ids.map(id => sourceMap[id]).filter(Boolean);
  const seen = new Set<string>();
  const sources = sourcesRaw.filter(s => seen.has(s.outlet) ? false : (seen.add(s.outlet), true));

  return (
    <div className="mt-4 pt-4 border-t border-gray-200 space-y-4">
      {claims.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Supporting claims</p>
          <ul className="space-y-2">
            {claims.map(claim => (
              <li key={claim.claim_id} className="flex gap-2 items-start">
                <span className="mt-2 w-1.5 h-1.5 rounded-full bg-gray-300 shrink-0" />
                <span className="text-sm text-gray-700 leading-snug">{claim.text}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      {sources.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-gray-400 mb-2">Sources</p>
          <div className="flex flex-wrap gap-1.5">
            {sources.map(src => <SourceChip key={src.source_id} src={src} />)}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Paragraph card ────────────────────────────────────────────────────────────

function ParagraphCard({
  para,
  claimsMap,
  sourceMap,
  transparencyMode,
}: {
  para: ReportParagraph;
  claimsMap: Record<string, Claim>;
  sourceMap: Record<string, Source>;
  transparencyMode: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const hasReceipt =
    para.supports.claim_ids.length > 0 || para.supports.source_ids.length > 0;

  return (
    <div className="py-4" style={{ borderBottom: '1px solid #f3f4f6' }}>
      {/* Kind badge + Show/Hide button — only visible in transparency mode */}
      {transparencyMode && (
        <div className="flex items-center justify-between mb-2">
          <KindBadge kind={para.kind} />
          {hasReceipt && (
            <button
              onClick={() => setExpanded(v => !v)}
              className="text-xs text-gray-400 hover:text-gray-600 underline underline-offset-2"
            >
              {expanded ? 'Hide sources' : 'Show sources'}
            </button>
          )}
        </div>
      )}

      {/* Paragraph text — always visible */}
      <p className="text-gray-800 leading-relaxed">{para.text}</p>

      {/* Receipt — shown only when individually expanded AND transparency is on */}
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
}

export default function ReportView({ report, claimsMap, sourceMap }: ReportViewProps) {
  const [transparencyMode, setTransparencyMode] = useState(false);

  return (
    <section className="mb-12">

      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-xl font-bold">Analysis</h2>
        <button
          onClick={() => setTransparencyMode(v => !v)}
          className={`flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full border transition-colors ${
            transparencyMode
              ? 'bg-indigo-600 text-white border-indigo-600'
              : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
          }`}
        >
          <span>🔍</span>
          {transparencyMode ? 'Transparency on' : 'Show sources'}
        </button>
      </div>

      {/* Kind legend — visible only in transparency mode */}
      {transparencyMode && (
        <div className="flex flex-wrap gap-2 mb-5">
          {(Object.entries(KIND) as [ReportParagraph['kind'], typeof KIND[keyof typeof KIND]][]).map(([kind]) => (
            <KindBadge key={kind} kind={kind} />
          ))}
        </div>
      )}

      {/* Paragraphs — each row owns its bar segment so heights always match */}
      <div className="flex flex-col">
        {report.paragraphs.map(para => {
          const cfg = KIND[para.kind] ?? KIND.background;
          return (
            <div key={para.paragraph_id} className="flex items-stretch">
              {/* Bar segment — stretches to match this paragraph's height */}
              <div
                className="shrink-0 transition-colors duration-200"
                style={{ width: 2, marginRight: 20, backgroundColor: cfg.bar }}
              />
              {/* Content */}
              <div className="flex-1 min-w-0">
                <ParagraphCard
                  para={para}
                  claimsMap={claimsMap}
                  sourceMap={sourceMap}
                  transparencyMode={transparencyMode}
                />
              </div>
            </div>
          );
        })}
      </div>

    </section>
  );
}
