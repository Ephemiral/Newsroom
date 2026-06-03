'use client';

import { useState } from 'react';
import { Source } from '@/lib/types';

const BIAS_LABEL: Record<string, string> = {
  left:           'Left',
  'center-left':  'Center-left',
  center:         'Center',
  'center-right': 'Center-right',
  right:          'Right',
};

const BIAS_COLORS: Record<string, string> = {
  left:           'bg-blue-100 text-blue-800',
  'center-left':  'bg-sky-100 text-sky-800',
  center:         'bg-gray-100 text-gray-700',
  'center-right': 'bg-orange-100 text-orange-800',
  right:          'bg-red-100 text-red-800',
};

interface OutletCardProps {
  outlet: string;
  sources: Source[];
}

export default function OutletCard({ outlet, sources }: OutletCardProps) {
  const [expanded, setExpanded] = useState(false);

  // All articles from the same outlet share bias_rating, ownership, bias_rating_source
  const representative = sources[0];
  const hasArticleDetail = sources.some(s => s.author || s.author_background);

  return (
    <div className="border border-gray-200 rounded-lg p-4 text-sm space-y-2">

      {/* Outlet name + bias badge */}
      <div className="flex items-start justify-between gap-2">
        <span className="font-semibold text-gray-900 leading-tight">{outlet}</span>
        <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${BIAS_COLORS[representative.bias_rating] ?? 'bg-gray-100 text-gray-600'}`}>
          {BIAS_LABEL[representative.bias_rating] ?? representative.bias_rating}
        </span>
      </div>

      {/* Bias rating source */}
      <div className="text-xs text-gray-400">
        Bias rating: {representative.bias_rating_source}
      </div>

      {/* Ownership */}
      {representative.ownership && (
        <div className="text-gray-500 text-xs border-t border-gray-100 pt-2">
          {representative.ownership}
        </div>
      )}

      {/* Article list — collapsed by default if >1 article, always shown if only 1 */}
      {sources.length === 1 ? (
        <ArticleRow source={sources[0]} />
      ) : (
        <div className="border-t border-gray-100 pt-2">
          <button
            onClick={() => setExpanded(v => !v)}
            className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
          >
            {expanded ? '▾ Hide articles' : `▸ ${sources.length} articles`}
          </button>
          {expanded && (
            <ul className="mt-2 space-y-2">
              {sources.map(src => (
                <li key={src.source_id}>
                  <ArticleRow source={src} />
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function ArticleRow({ source }: { source: Source }) {
  const date = new Date(source.published_at).toLocaleDateString(undefined, {
    day: 'numeric', month: 'short', year: 'numeric',
  });

  return (
    <div className="text-xs text-gray-600 space-y-0.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-gray-400">{date}</span>
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-indigo-500 hover:text-indigo-700 flex-shrink-0"
          aria-label="Open article"
        >
          ↗
        </a>
      </div>
      {source.author && (
        <div className="text-gray-500">
          By {source.author}
          {source.author_background && (
            <span className="text-gray-400"> — {source.author_background}</span>
          )}
        </div>
      )}
    </div>
  );
}
