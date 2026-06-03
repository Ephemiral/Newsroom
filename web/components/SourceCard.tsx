import { Source } from '@/lib/types';

const BIAS_LABEL: Record<string, string> = {
  left: 'Left',
  'center-left': 'Center-left',
  center: 'Center',
  'center-right': 'Center-right',
  right: 'Right',
};

const BIAS_COLORS: Record<string, string> = {
  left: 'bg-blue-100 text-blue-800',
  'center-left': 'bg-sky-100 text-sky-800',
  center: 'bg-gray-100 text-gray-700',
  'center-right': 'bg-orange-100 text-orange-800',
  right: 'bg-red-100 text-red-800',
};

export default function SourceCard({ source }: { source: Source }) {
  return (
    <div className="border border-gray-200 rounded-lg p-4 text-sm space-y-2">
      {/* Outlet + bias */}
      <div className="flex items-start justify-between gap-2">
        <a
          href={source.url}
          target="_blank"
          rel="noopener noreferrer"
          className="font-semibold text-gray-900 hover:underline leading-tight"
        >
          {source.outlet}
        </a>
        <span className={`flex-shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${BIAS_COLORS[source.bias_rating]}`}>
          {BIAS_LABEL[source.bias_rating]}
        </span>
      </div>

      {/* Bias rating source */}
      <div className="text-xs text-gray-400">
        Bias rating: {source.bias_rating_source}
      </div>

      {/* Author */}
      {source.author && (
        <div className="text-gray-600">
          <span className="text-gray-400">By </span>{source.author}
          {source.author_background && (
            <span className="text-gray-500"> — {source.author_background}</span>
          )}
        </div>
      )}

      {/* Ownership */}
      {source.ownership && (
        <div className="text-gray-500 text-xs border-t border-gray-100 pt-2">
          {source.ownership}
        </div>
      )}
    </div>
  );
}
