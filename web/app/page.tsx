import Link from 'next/link';
import { getEventGroups } from '@/lib/data';
import { BEAT_LABELS, beatLabel } from '@/lib/beats';
import CritiqalLogoAnimated from '@/components/CritiqalLogoAnimated';

// Render on demand so new events appear without restarting the dev server
export const dynamic = 'force-dynamic';

interface HomeProps {
  searchParams: Promise<{ beat?: string }>;
}

export default async function Home({ searchParams }: HomeProps) {
  const { beat } = await searchParams;
  const activeBeat = beat && BEAT_LABELS[beat] ? beat : null;

  // One card per story: developments are grouped under their earliest coverage
  // (getEventGroups collapses related_events chains), so a multi-day story shows
  // once instead of as N cards. Filter by the representative event's beat.
  const events = getEventGroups()
    .filter(({ event }) => !activeBeat || event.event.beat === activeBeat);

  return (
    <main style={{ background: '#f7f4ee', minHeight: '100vh' }}>

      {/* ── Masthead ─────────────────────────────────────────────────────── */}
      <header style={{ borderBottom: '1px solid #d9cfbd', background: '#f7f4ee' }}>
        <div style={{ maxWidth: 760, margin: '0 auto', padding: '30px 28px 22px', textAlign: 'center' }}>
          <div style={{
            font: '600 10px/1 var(--font-archivo), system-ui',
            letterSpacing: '.34em', textTransform: 'uppercase', color: '#b08a4a',
          }}>
            Transparent synthesis · Multi-source
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
            What outlets agree on, what they contest, and who is behind each story.{' '}
            <Link href="/about" style={{ color: '#b08a4a', textDecoration: 'underline' }}>
              How it works
            </Link>
          </p>
        </div>
      </header>

      {/* ── Theatre tabs ─────────────────────────────────────────────────── */}
      <nav style={{ borderBottom: '1px solid #e7e0d4', background: '#f7f4ee' }}>
        <div style={{
          maxWidth: 760, margin: '0 auto', padding: '0 28px',
          display: 'flex', gap: 22, overflowX: 'auto',
        }}>
          {[['', 'All'], ...Object.entries(BEAT_LABELS)].map(([key, label]) => {
            const active = (key === '' && !activeBeat) || key === activeBeat;
            return (
              <Link
                key={key || 'all'}
                href={key ? `/?beat=${key}` : '/'}
                style={{
                  font: `600 12px/1 var(--font-archivo), system-ui`,
                  letterSpacing: '.08em', textTransform: 'uppercase',
                  color: active ? '#141109' : '#a3957f',
                  textDecoration: 'none', padding: '14px 0 12px',
                  borderBottom: active ? '2px solid #b08a4a' : '2px solid transparent',
                  whiteSpace: 'nowrap',
                }}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* ── Feed ─────────────────────────────────────────────────────────── */}
      <div style={{ maxWidth: 760, margin: '0 auto', padding: '8px 28px 80px' }}>
        {events.length === 0 ? (
          <p style={{ color: '#a3957f', paddingTop: 32 }}>
            No analyzed events in this theatre yet — the pipeline publishes automatically as qualifying coverage appears.
          </p>
        ) : (
          <div>
            {events.map(({ id, event, earlier }) => {
              const agreedCount = event.claims.filter(c => c.classification === 'agreed').length;
              const contestedCount = event.claims.filter(c => c.classification === 'contested').length;
              return (
                <div key={id} style={{ borderBottom: '1px solid #e7e0d4' }}>
                <Link
                  href={`/event/${id}`}
                  style={{ display: 'block', padding: '30px 0 18px', textDecoration: 'none' }}
                >
                  <div style={{
                    font: '600 11px/1 var(--font-archivo), system-ui',
                    letterSpacing: '.16em', textTransform: 'uppercase',
                    color: '#b08a4a', marginBottom: 14,
                  }}>
                    {beatLabel(event.event.beat)}
                  </div>
                  <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
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
                    </div>
                    {event.event.image && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={event.event.image.url}
                        alt={event.event.image.caption}
                        loading="lazy"
                        style={{
                          width: 168, height: 118, objectFit: 'cover',
                          borderRadius: 3, flexShrink: 0, marginTop: 4,
                          border: '1px solid #e1d8c8', background: '#ece6da',
                        }}
                      />
                    )}
                  </div>
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

                {/* Developing story — earlier coverage folded under this card */}
                {earlier.length > 0 && (
                  <div style={{ padding: '0 0 20px' }}>
                    <div style={{
                      font: '600 10px/1 var(--font-archivo), system-ui',
                      letterSpacing: '.14em', textTransform: 'uppercase', color: '#a3957f',
                      marginBottom: 8,
                    }}>
                      Developing story · {earlier.length} earlier {earlier.length === 1 ? 'report' : 'reports'}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 6, borderLeft: '2px solid #e2d7c2', paddingLeft: 14 }}>
                      {earlier.map((e) => (
                        <Link
                          key={e.id}
                          href={`/event/${e.id}`}
                          style={{
                            fontFamily: 'var(--font-spectral), serif', fontSize: 15,
                            lineHeight: 1.4, color: '#7a6e5c', textDecoration: 'none',
                          }}
                        >
                          <span style={{ color: '#a3957f' }}>
                            {new Date(e.event.event.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}
                            {' — '}
                          </span>
                          {e.event.event.title}
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
                </div>
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
