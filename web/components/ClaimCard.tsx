'use client';

import { useState } from 'react';
import { Claim, Source } from '@/lib/types';

export const BIAS_COLORS: Record<string, string> = {
  left: 'bg-blue-100 text-blue-800',
  'center-left': 'bg-sky-100 text-sky-800',
  center: 'bg-gray-100 text-gray-700',
  'center-right': 'bg-orange-100 text-orange-800',
  right: 'bg-red-100 text-red-800',
};

/** "Al Jazeera · 28 May 2026" — never exposes internal IDs */
function sourceLabel(src: Source): string {
  const aligned = src.state_alignment ? ` · ${src.state_alignment}` : '';
  if (!src.published_at) return `${src.outlet}${aligned}`;
  const d = new Date(src.published_at);
  const date = d.toLocaleDateString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric',
  });
  return `${src.outlet} · ${date}${aligned}`;
}

interface Props {
  claim: Claim;
  sourceMap: Record<string, Source>;
  accentBorder: string;
}

export default function ClaimCard({ claim, sourceMap, accentBorder }: Props) {
  const [open, setOpen] = useState(false);

  const supportingSources = claim.supported_by.map((id) => sourceMap[id]).filter(Boolean);
  const contestingSources = claim.contested_by.map((id) => sourceMap[id]).filter(Boolean);

  return (
    <div className={`border rounded-lg overflow-hidden ${accentBorder}`}>

      {/* Main row — claim text */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full text-left px-4 py-3 flex items-start gap-3 hover:bg-gray-50 transition-colors"
      >
        <span className="mt-0.5 text-gray-400 flex-shrink-0 text-sm select-none">
          {open ? '▾' : '▸'}
        </span>
        <p className="text-sm text-gray-800 leading-snug">{claim.text}</p>
      </button>

      {/* Source chips */}
      <div className="px-4 pb-3 flex flex-wrap items-center gap-1.5 ml-6">
        {claim.dispute_type === 'actor' && (
          <span
            title="The actors in this story gave contradictory accounts. Each outlet listed here reported the dispute — the outlets themselves are not taking sides."
            className="text-xs px-2 py-0.5 rounded-full font-semibold bg-amber-50 text-amber-800 border border-amber-200 cursor-default"
          >
            conflicting accounts
          </span>
        )}
        {supportingSources.map((src) => (
          <span
            key={src.source_id}
            title={sourceLabel(src)}
            className={`text-xs px-2 py-0.5 rounded-full font-medium cursor-default ${BIAS_COLORS[src.bias_rating] ?? 'bg-gray-100 text-gray-600'}`}
          >
            {src.state_alignment ? `⚑ ${src.outlet}` : src.outlet}
          </span>
        ))}
        {contestingSources.length > 0 && (
          <>
            <span className="text-gray-400 text-xs font-medium px-0.5 select-none" aria-label="versus">
              ↔
            </span>
            {contestingSources.map((src) => (
              <span
                key={`contest-${src.source_id}`}
                title={sourceLabel(src)}
                className={`text-xs px-2 py-0.5 rounded-full font-medium cursor-default ${BIAS_COLORS[src.bias_rating] ?? 'bg-gray-100 text-gray-600'}`}
              >
                {src.state_alignment ? `⚑ ${src.outlet}` : src.outlet}
              </span>
            ))}
          </>
        )}
      </div>

      {/* Expanded detail */}
      {open && (
        <div className="px-4 pb-4 ml-6 border-t border-gray-100 pt-3 space-y-4">

          {/* Rationale */}
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-1">
              Why this classification
            </div>
            <p className="text-sm text-gray-600 leading-relaxed">{claim.rationale}</p>
          </div>

          {/* Framing variants */}
          {claim.framing_variants.length > 0 && (
            <div>
              <div className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-2">
                How outlets frame it
              </div>
              <div className="space-y-2">
                {claim.framing_variants.map((fv) => {
                  const src = sourceMap[fv.source_id];
                  if (!src) return null;
                  return (
                    <div key={fv.source_id} className="flex gap-2 text-sm">
                      <div className="flex flex-col gap-0.5 flex-shrink-0">
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${BIAS_COLORS[src.bias_rating] ?? 'bg-gray-100'}`}>
                          {src.outlet}
                        </span>
                        <span className="text-xs text-gray-400 pl-1">
                          {new Date(src.published_at).toLocaleDateString(undefined, {
                            day: 'numeric', month: 'short', year: 'numeric',
                          })}
                        </span>
                      </div>
                      <span className="text-gray-600 italic leading-snug">
                        &ldquo;{fv.characterization}&rdquo;
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
