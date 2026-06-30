import Link from 'next/link';
import { getEventIds, getEvent } from '@/lib/data';
import CritiqalLogoAnimated from '@/components/CritiqalLogoAnimated';

// Render on demand so new events appear without restarting the dev server
export const dynamic = 'force-dynamic';

export default function Home() {
  const ids = getEventIds();
  const events = ids
    .map((id) => ({ id, event: getEvent(id)! }))
    .sort((a, b) => new Date(b.event.event.date).getTime() - new Date(a.event.event.date).getTime());

  return (
    <main style={{ background: '#f7f4ee', minHeight: '100vh' }}>

      {/* ── Masthead ─────────────────────────────────────────────────────── */}
      <header style={{ borderBottom: '1px solid #d9cfbd', background: '#f7f4ee' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', padding: '30px 28px 22px', textAlign: 'center' }}>
          <div style={{
            font: '600 10px/1 var(--font-archivo), system-ui',
            letterSpacing: '.34em', textTransform: 'uppercase', color: '#b08a4a',
          }}>
            Neutral synthesis · Multi-source
          </div>
          <div style={{
            margin: '14px 0 12px',
            borderTop: '1px solid #d9cfbd', borderBottom: '1px solid #d9cfbd',
            padding: '16px 0', display: 'flex', justifyContent: 'center',
          }}>
            <CritiqalLogoAnimated />
          </div>
          <p style={{
            fontFamily: 'var(--font-spectral), serif',
            fontStyle: 'italic', fontSize: 15, lineHeight: 1.5, color: '#7a6e5c',
            margin: 0,
          }}>
            What outlets agree on, what they contest, and who is behind each story.
          </p>
        </div>
      </header>

      {/* ── Feed ─────────────────────────────────────────────────────────── */}
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '8px 28px 80px' }}>
        {events.length === 0 ? (
          <p style={{ color: '#a3957f', paddingTop: 32 }}>No analyzed events yet.</p>
        ) : (
          <div>
            {events.map(({ id, event }) => {
              const agreedCount = event.claims.filter(c => c.classification === 'agreed').length;
              const contestedCount = event.claims.filter(c => c.classification === 'contested').length;
              return (
                <Link
                  key={id}
                  href={`/event/${id}`}
                  style={{ display: 'block', padding: '30px 0', borderBottom: '1px solid #e7e0d4', textDecoration: 'none' }}
                >
                  <div style={{
                    font: '600 11px/1 var(--font-archivo), system-ui',
                    letterSpacing: '.16em', textTransform: 'uppercase',
                    color: '#b08a4a', marginBottom: 14,
                  }}>
                    {event.event.beat.replace(/_/g, ' ')}
                  </div>
                  <h2 style={{
                    fontFamily: 'var(--font-spectral), serif',
                    fontWeight: 600, fontSize: 28, lineHeight: 1.2,
                    letterSpacing: '-.018em', color: '#141109', margin: 0,
                  }}>
                    {event.event.title}
                  </h2>
                  <p style={{
                    fontFamily: 'var(--font-spectral), serif',
                    fontSize: 17, lineHeight: 1.6, color: '#5b5249',
                    margin: '12px 0 0',
                  }}>
                    {event.event.summary}
                  </p>
                  <div style={{
                    display: 'flex', alignItems: 'center', gap: 12, marginTop: 16,
                    font: '500 12px/1 var(--font-archivo), system-ui', color: '#8a7d6c',
                  }}>
                    <span>
                      {new Date(event.event.date).toLocaleDateString('en-GB', {
                        day: 'numeric', month: 'long', year: 'numeric',
                      })}
                    </span>
                    <Dot />
                    <span>{event.sources.length} outlets</span>
                    <Dot />
                    <span style={{ color: '#2f7a4a', fontWeight: 600 }}>{agreedCount} agreed</span>
                    {contestedCount > 0 && (
                      <>
                        <Dot />
                        <span style={{ color: '#c2682f', fontWeight: 600 }}>{contestedCount} contested</span>
                      </>
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>

    </main>
  );
}

function Dot() {
  return (
    <span style={{ width: 3, height: 3, borderRadius: '50%', background: '#cdc3b2', display: 'inline-block', flexShrink: 0 }} />
  );
}
