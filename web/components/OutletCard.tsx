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

const BIAS_DOT: Record<string, string> = {
  left:           '#2f5fd0',
  'center-left':  '#5b8def',
  center:         '#8a8a8a',
  'center-right': '#e08a3c',
  right:          '#d24b3e',
};

interface OutletCardProps {
  outlet: string;
  sources: Source[];
}

export default function OutletCard({ outlet, sources }: OutletCardProps) {
  const [articlesOpen, setArticlesOpen] = useState(false);

  const rep   = sources[0];
  const dot   = BIAS_DOT[rep.bias_rating]   ?? '#8a8a8a';
  const label = BIAS_LABEL[rep.bias_rating]  ?? rep.bias_rating;
  const articleLabel =
    sources.length === 1
      ? '1 article in this synthesis'
      : `${sources.length} articles in this synthesis`;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 12,
      padding: '18px 18px 16px',
      background: '#fffdf8',
      border: '1px solid #e7ddca',
      borderRadius: 8,
    }}>

      {/* Outlet name · bias dot · label */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 9 }}>
        <span style={{
          width: 9, height: 9, borderRadius: '50%',
          background: dot, flexShrink: 0,
          transform: 'translateY(1px)', display: 'inline-block',
        }} />
        <span style={{
          fontFamily: 'var(--font-spectral), serif',
          fontWeight: 600, fontSize: 17, lineHeight: 1.2,
          color: '#1c1812', flex: 1, minWidth: 0,
        }}>
          {outlet}
        </span>
        <span style={{
          font: '600 9.5px/1 var(--font-archivo), system-ui',
          letterSpacing: '.07em', textTransform: 'uppercase',
          color: dot, whiteSpace: 'nowrap',
        }}>
          {label}
        </span>
      </div>

      {/* Rated by */}
      <div style={{
        font: '400 11px/1 var(--font-archivo), system-ui',
        letterSpacing: '.04em', color: '#a3957f',
      }}>
        Bias rated by {rep.bias_rating_source}
      </div>

      {/* Ownership */}
      {rep.ownership && (
        <div style={{
          fontFamily: 'var(--font-spectral), serif',
          fontSize: 13.5, lineHeight: 1.5, color: '#6a6052',
        }}>
          {rep.ownership}
        </div>
      )}

      {/* Articles — collapsed by default */}
      <div style={{ marginTop: 2, paddingTop: 12, borderTop: '1px solid #ece5d9' }}>
        <button
          onClick={() => setArticlesOpen(v => !v)}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            background: 'none', border: 'none', cursor: 'pointer', padding: 0,
          }}
        >
          <span style={{
            font: '600 9.5px/1 var(--font-archivo), system-ui',
            letterSpacing: '.13em', textTransform: 'uppercase', color: '#b6a68f',
          }}>
            {articleLabel}
          </span>
          <span style={{ fontSize: 10, color: '#b6a68f' }}>
            {articlesOpen ? '▲' : '▼'}
          </span>
        </button>

        {articlesOpen && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 7, marginTop: 10 }}>
            {sources.map((src, i) => (
              <a
                key={src.source_id}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 5,
                  padding: '5px 10px',
                  background: '#f4efe4', border: '1px solid #e2d7c2', borderRadius: 5,
                  font: '500 11px/1 var(--font-archivo), system-ui',
                  color: '#5b5249', textDecoration: 'none',
                }}
              >
                Report {i + 1}
                <span style={{ fontSize: 10, color: '#a3957f' }}>↗</span>
              </a>
            ))}
          </div>
        )}
      </div>

    </div>
  );
}
