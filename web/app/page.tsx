import Link from 'next/link';
import { getEventIds, getEvent } from '@/lib/data';

// Render on demand so new events appear without restarting the dev server
export const dynamic = 'force-dynamic';

export default function Home() {
  const ids = getEventIds();
  const events = ids.map((id) => ({ id, event: getEvent(id)! }));

  return (
    <main className="max-w-3xl mx-auto px-4 py-12 font-sans">
      <h1 className="text-3xl font-bold mb-2">Newsroom</h1>
      <p className="text-gray-500 mb-10">
        Multi-source news analysis — what outlets agree on, what they contest, and who&apos;s behind each story.
      </p>

      {events.length === 0 ? (
        <p className="text-gray-400">No analyzed events yet.</p>
      ) : (
        <div className="space-y-4">
          {events.map(({ id, event }) => (
            <Link
              key={id}
              href={`/event/${id}`}
              className="block border border-gray-200 rounded-lg p-5 hover:border-gray-400 hover:shadow-sm transition-all"
            >
              <div className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-1">
                {event.event.beat.replace(/_/g, ' ')}
              </div>
              <h2 className="font-semibold text-gray-900 mb-2">{event.event.title}</h2>
              <p className="text-sm text-gray-500 mb-3 line-clamp-2">{event.event.summary}</p>
              <div className="flex gap-4 text-xs text-gray-400">
                <span>{new Date(event.event.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}</span>
                <span>{event.sources.length} sources</span>
                <span>
                  {event.claims.filter(c => c.classification === 'agreed').length} agreed
                  {' · '}
                  {event.claims.filter(c => c.classification === 'contested').length} contested
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  );
}
