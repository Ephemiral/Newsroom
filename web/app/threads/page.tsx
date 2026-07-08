import Link from 'next/link';
import { getThreads, getEvent } from '@/lib/data';
import { beatLabel } from '@/lib/beats';
import CritiqalLogo from '@/components/CritiqalLogo';

export const dynamic = 'force-dynamic';

export const metadata = {
  title: 'Developing stories — Critiqal',
  description: 'Ongoing news stories, grouped into threads you can follow from start to latest.',
};

export default async function ThreadsPage() {
  const threads = getThreads();

  return (
    <div style={{ background: '#f7f4ee', minHeight: '100vh' }}>
      {/* Top nav */}
      <div style={{ borderBottom: '1px solid #e1d8c8', background: '#f7f4ee' }}>
        <div style={{
          maxWidth: 960, margin: '0 auto', padding: '0 48px',
          height: 52, display: 'flex', alignItems: 'center',
        }}>
          <Link href="/" style={{
            display: 'inline-flex', alignItems: 'center', gap: 7,
            font: '500 13px/1 var(--font-archivo), system-ui', color: '#6a6052', textDecoration: 'none',
          }}>
            <span style={{ fontSize: 15 }}>←</span>
            <CritiqalLogo width={58} />
          </Link>
        </div>
      </div>

      <main style={{ maxWidth: 960, margin: '0 auto', padding: '32px 48px 80px' }}>
        <header style={{ marginBottom: 8 }}>
          <div style={{
            font: '600 10px/1 var(--font-archivo), system-ui',
            letterSpacing: '.34em', textTransform: 'uppercase', color: '#b08a4a', marginBottom: 10,
          }}>
            Developing stories
          </div>
          <h1 style={{
            fontFamily: 'var(--font-spectral), serif', fontWeight: 600, fontSize: 34,
            lineHeight: 1.15, letterSpacing: '-.02em', color: '#141109', margin: 0,
          }}>
            Follow a story from start to latest
          </h1>
          <p style={{
            fontFamily: 'var(--font-spectral), serif', fontStyle: 'italic', fontSize: 17,
            lineHeight: 1.5, color: '#7a6e5c', margin: '10px 0 0',
          }}>
            News is always developing. These are the ongoing stories, each grouped into one thread you can follow across every update.
          </p>
        </header>

        {threads.length === 0 ? (
          <p style={{ color: '#a3957f', paddingTop: 40, fontFamily: 'var(--font-spectral), serif' }}>
            No developing stories yet — a thread appears here once a story has more than one report.
          </p>
        ) : (
          <div style={{ marginTop: 24 }}>
            {threads.map((t) => {
              const latest = t.events[t.events.length - 1];
              const latestEvent = latest ? getEvent(latest.cluster_id) : null;
              const image = latestEvent?.event.image;
              return (
                <Link
                  key={t.thread_id}
                  href={`/thread/${t.thread_id}`}
                  style={{ display: 'block', padding: '26px 0', borderBottom: '1px solid #e7e0d4', textDecoration: 'none' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 12 }}>
                    <span style={{
                      font: '600 10px/1 var(--font-archivo), system-ui',
                      letterSpacing: '.14em', textTransform: 'uppercase',
                      color: t.status === 'developing' ? '#b08a4a' : '#a3957f',
                    }}>
                      {t.status === 'developing' ? 'Developing' : 'Past story'} · {t.events.length} developments
                    </span>
                    <span style={{ font: '500 11px/1 var(--font-archivo), system-ui', color: '#a3957f' }}>
                      {t.beats.map(beatLabel).join(' · ')}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start' }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <h2 style={{
                        fontFamily: 'var(--font-spectral), serif', fontWeight: 600, fontSize: 26,
                        lineHeight: 1.2, letterSpacing: '-.018em', color: '#141109', margin: 0,
                      }}>
                        {t.title}
                      </h2>
                      <p style={{
                        fontFamily: 'var(--font-spectral), serif', fontSize: 16, lineHeight: 1.6,
                        color: '#5b5249', margin: '10px 0 0',
                      }}>
                        {t.summary}
                      </p>
                      {latest && (
                        <p style={{
                          font: '500 12px/1.4 var(--font-archivo), system-ui', color: '#8a7d6c', margin: '12px 0 0',
                        }}>
                          Latest · {new Date(latest.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
                        </p>
                      )}
                    </div>
                    {image && (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={image.url}
                        alt={image.caption}
                        loading="lazy"
                        style={{
                          width: 150, height: 104, objectFit: 'cover', borderRadius: 3,
                          flexShrink: 0, marginTop: 2, border: '1px solid #e1d8c8', background: '#ece6da',
                        }}
                      />
                    )}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
