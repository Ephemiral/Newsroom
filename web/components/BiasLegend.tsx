import { Source, BiasRating } from '@/lib/types';

const SPECTRUM: { rating: BiasRating; label: string; bg: string; text: string; dot: string }[] = [
  { rating: 'left',         label: 'Left',         bg: 'bg-blue-100',   text: 'text-blue-800',   dot: 'bg-blue-500' },
  { rating: 'center-left',  label: 'Center-left',  bg: 'bg-sky-100',    text: 'text-sky-800',    dot: 'bg-sky-400' },
  { rating: 'center',       label: 'Center',       bg: 'bg-gray-100',   text: 'text-gray-700',   dot: 'bg-gray-400' },
  { rating: 'center-right', label: 'Center-right', bg: 'bg-orange-100', text: 'text-orange-800', dot: 'bg-orange-400' },
  { rating: 'right',        label: 'Right',        bg: 'bg-red-100',    text: 'text-red-800',    dot: 'bg-red-500' },
];

export default function BiasLegend({ sources }: { sources: Source[] }) {
  // Build a map of rating → outlets in this event
  const byRating: Partial<Record<BiasRating, string[]>> = {};
  for (const src of sources) {
    if (!byRating[src.bias_rating]) byRating[src.bias_rating] = [];
    // Deduplicate outlets (Al Jazeera appears twice)
    if (!byRating[src.bias_rating]!.includes(src.outlet)) {
      byRating[src.bias_rating]!.push(src.outlet);
    }
  }

  return (
    <div className="mb-6 pt-4 border-t border-gray-100">
      <div className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-3">
        Sources on the political spectrum
      </div>

      {/* Gradient bar */}
      <div className="h-2 rounded-full mb-4"
        style={{ background: 'linear-gradient(to right, #3b82f6, #38bdf8, #9ca3af, #fb923c, #ef4444)' }}
      />

      {/* Legend columns — left-aligned outlet names */}
      <div className="grid grid-cols-5 gap-1">
        {SPECTRUM.map(({ rating, label, bg, text, dot }) => {
          const outlets = byRating[rating] ?? [];
          return (
            <div key={rating}>
              <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium mb-2 ${bg} ${text}`}>
                {label}
              </span>
              <div className="space-y-1">
                {outlets.map((outlet) => (
                  <div key={outlet} className="flex items-start gap-1">
                    <span className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${dot}`} />
                    <span className="text-xs text-gray-600 leading-tight">{outlet}</span>
                  </div>
                ))}
                {outlets.length === 0 && (
                  <span className="text-xs text-gray-300">—</span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-400">
        Bias ratings sourced from{' '}
        {[...new Set(sources.map(s => s.bias_rating_source))].join(', ')}.
        Ratings are cited, not the product&apos;s own verdict.
      </div>
    </div>
  );
}
