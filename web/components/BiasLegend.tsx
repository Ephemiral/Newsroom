import { Source, BiasRating } from '@/lib/types';

const SPECTRUM: {
  rating: BiasRating;
  label: string;
  dot: string;
}[] = [
  { rating: 'left',         label: 'Left',         dot: '#2f5fd0' },
  { rating: 'center-left',  label: 'Center-left',  dot: '#5b8def' },
  { rating: 'center',       label: 'Center',       dot: '#8a8a8a' },
  { rating: 'center-right', label: 'Center-right', dot: '#e08a3c' },
  { rating: 'right',        label: 'Right',        dot: '#d24b3e' },
];

export default function BiasLegend({ sources }: { sources: Source[] }) {
  // Count unique outlets per rating tier
  const byRating: Partial<Record<BiasRating, Set<string>>> = {};
  for (const src of sources) {
    if (!byRating[src.bias_rating]) byRating[src.bias_rating] = new Set();
    byRating[src.bias_rating]!.add(src.outlet);
  }

  const ratingSource = [...new Set(sources.map(s => s.bias_rating_source))].join(', ');

  return (
    <div style={{ marginTop: 32, paddingTop: 22, borderTop: '1px solid #e1d8c8', borderBottom: '1px solid #e1d8c8', paddingBottom: 22 }}>
      <div style={{
        font: '600 10px/1 var(--font-archivo), system-ui',
        letterSpacing: '.16em', textTransform: 'uppercase',
        color: '#9a8d7c', marginBottom: 16,
      }}>
        Who covered this
      </div>

      {/* Gradient bar with dots aligned above labels */}
      <div style={{ position: 'relative' }}>
        {/* Bar */}
        <div style={{
          height: 6, borderRadius: 3,
          background: 'linear-gradient(90deg, #3a5bd0, #7e9bd8, #cfc8bd, #e3b483, #d8703f)',
        }} />

        {/* Dots — one per column, flex-aligned to match labels below */}
        <div style={{ position: 'absolute', top: -4, left: 0, right: 0, display: 'flex' }}>
          {SPECTRUM.map(({ rating, dot }) => {
            const count = byRating[rating]?.size ?? 0;
            return (
              <div key={rating} style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
                {count > 0 && (
                  <span style={{
                    width: 14, height: 14, borderRadius: '50%',
                    background: dot, border: '2.5px solid #f7f4ee',
                    display: 'inline-block',
                  }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Labels + counts */}
      <div style={{ display: 'flex', marginTop: 14 }}>
        {SPECTRUM.map(({ rating, label, dot }) => {
          const count = byRating[rating]?.size ?? 0;
          return (
            <div key={rating} style={{ flex: 1, textAlign: 'center' }}>
              <div style={{
                font: '600 11px/1 var(--font-archivo), system-ui',
                color: count > 0 ? dot : '#cdc3b2',
              }}>
                {count > 0 ? count : '—'}
              </div>
              <div style={{
                font: '500 9.5px/1.3 var(--font-archivo), system-ui',
                letterSpacing: '.06em', textTransform: 'uppercase',
                color: '#a3957f', marginTop: 5,
              }}>
                {label}
              </div>
            </div>
          );
        })}
      </div>

      <p style={{
        fontFamily: 'var(--font-spectral), serif',
        fontStyle: 'italic', fontSize: 13, lineHeight: 1.45,
        color: '#8a7d6c', marginTop: 14, marginBottom: 0,
      }}>
        Bias ratings sourced from {ratingSource}. Ratings are cited, not the product&apos;s own verdict.
      </p>
    </div>
  );
}
