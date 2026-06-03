'use client';

import { useState } from 'react';
import { Claim, Source } from '@/lib/types';
import ClaimCard from './ClaimCard';

const ACCENT = {
  green: {
    badge: 'bg-emerald-100 text-emerald-800',
    border: 'border-emerald-200',
    dot: 'bg-emerald-500',
    headerBg: 'hover:bg-emerald-50',
    groupHeading: 'text-emerald-700',
  },
  teal: {
    badge: 'bg-teal-100 text-teal-800',
    border: 'border-teal-200',
    dot: 'bg-teal-400',
    headerBg: 'hover:bg-teal-50',
    groupHeading: 'text-teal-700',
  },
  amber: {
    badge: 'bg-amber-100 text-amber-800',
    border: 'border-amber-200',
    dot: 'bg-amber-500',
    headerBg: 'hover:bg-amber-50',
    groupHeading: 'text-amber-700',
  },
  gray: {
    badge: 'bg-gray-100 text-gray-600',
    border: 'border-gray-200',
    dot: 'bg-gray-400',
    headerBg: 'hover:bg-gray-50',
    groupHeading: 'text-gray-500',
  },
} as const;

/** Convert snake_case group names to readable titles. */
function groupLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

interface Props {
  label: string;
  description: string;
  claims: Claim[];
  sourceMap: Record<string, Source>;
  accent: keyof typeof ACCENT;
  defaultOpen?: boolean;
}

export default function ClaimSection({
  label, description, claims, sourceMap, accent, defaultOpen = false,
}: Props) {
  const [open, setOpen] = useState(defaultOpen);
  if (claims.length === 0) return null;
  const a = ACCENT[accent];

  // Group claims by claim_group. Ungrouped (null) claims collect under a null key.
  const grouped = new Map<string | null, Claim[]>();
  for (const claim of claims) {
    const key = claim.claim_group ?? null;
    if (!grouped.has(key)) grouped.set(key, []);
    grouped.get(key)!.push(claim);
  }

  // Render order: named groups first (alphabetical), ungrouped last.
  const namedGroups = [...grouped.keys()]
    .filter((k): k is string => k !== null)
    .sort();
  const renderOrder: (string | null)[] = [...namedGroups];
  if (grouped.has(null)) renderOrder.push(null);

  const hasGroups = namedGroups.length > 0;

  return (
    <div className="mb-6">
      {/* Section header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className={`w-full text-left flex items-center gap-3 py-2 px-1 rounded-md transition-colors ${a.headerBg}`}
      >
        <span className={`text-xs px-2 py-0.5 rounded-full font-medium flex-shrink-0 ${a.badge}`}>
          {claims.length}
        </span>
        <span className="font-semibold text-gray-800">{label}</span>
        <span className="ml-auto text-gray-400 text-sm select-none">
          {open ? '▾' : '▸'}
        </span>
      </button>

      {open && (
        <>
          <p className="text-sm text-gray-500 ml-5 mt-1 mb-3">{description}</p>

          {hasGroups ? (
            /* Grouped rendering */
            <div className="ml-5 space-y-5">
              {renderOrder.map((key) => {
                const groupClaims = grouped.get(key)!;
                return (
                  <div key={key ?? '__ungrouped'}>
                    {key !== null && (
                      <div className={`text-xs font-semibold uppercase tracking-wide mb-2 ${a.groupHeading}`}>
                        {groupLabel(key)}
                      </div>
                    )}
                    <div className="space-y-3">
                      {groupClaims.map((claim) => (
                        <ClaimCard
                          key={claim.claim_id}
                          claim={claim}
                          sourceMap={sourceMap}
                          accentBorder={a.border}
                        />
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Flat rendering (no groups) */
            <div className="space-y-3 ml-5">
              {claims.map((claim) => (
                <ClaimCard
                  key={claim.claim_id}
                  claim={claim}
                  sourceMap={sourceMap}
                  accentBorder={a.border}
                />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
