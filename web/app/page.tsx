import Link from 'next/link';
import { getEventIds, getEvent } from '@/lib/data';
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

  const ids = getEventIds();
  const events = ids
    .map((id) => ({ id, event: getEvent(id)! }))
    .filter(({ event }) => !activeBeat || event.event.beat === activeBeat)
    .sort((a, b) => new Date(b.event.event.date).getTime() - new Date(a.event.event.date).getTime());

  return (
    <main style={{ background: '#f7f4ee', minHeight: '100vh' }}>

      {/* ── Masthead ─────────────────────────────────────────────────────── */}
      <header style={{ borderBottom: '1px solid #d9cfbd', background: '#f7f4ee' }}>
        <div style={{ maxWidth: 960, margin: '0 auto', padding: '30px 48px 22px', textAlign: 'center' }}>
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
            fontStyle: 'italic', fontSize: 18, fontWeight: 600, lineHeight: 1.5, color: '#7a6e5c',
            margin: 0,
          }}>
            Think critically. Read Critiqal.
          </p>
        </div>
      </header>

      {/* ── Theatre tabs ─────────────────────────────────────────────────── */}
      <nav style={{ borderBottom: '1px solid #e7e0d4', background: '#f7f4ee' }}>
        <div style={{
          maxWidth: 960, margin: '0 auto', padding: '0 48px',
          display: 'flex', gap: 22, overflowX: 'auto',
          justifyContent: 'space-between',
        }}>
          {[['', 'All'], ...Object.entries(BEAT_LABELS), ['about', 'About']].map(([key, label]) => {
            const isAbout = key === 'about';
            const active = !isAbout && ((key === '' && !activeBeat) || key === activeBeat);
            const href = isAbout ? '/about' : key ? `/?beat=${key}` : '/';
            return (
              <Link
                key={key || 'all'}
                href={href}
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
      <div style={{ maxWidth: 960, margin: '0 auto', padding: '8px 48px 80px' }}>
        {events.length === 0 ? (
          <p style={{ color: '#a3957f', paddingTop: 32 }}>
            No analyzed events in this theatre yet — the pipeline publishes automatically as qualifying coverage appears.
          </p>
        ) : (
          <div>
            {events.map(({ id, event }) => {
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
