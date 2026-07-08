import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getThread, getEvent } from '@/lib/data';
import { beatLabel } from '@/lib/beats';
import CritiqalLogo from '@/components/CritiqalLogo';

export const dynamic = 'force-dynamic';

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props) {
  const { id } = await params;
  const thread = getThread(id);
  if (!thread) return {};
  return { title: `${thread.title} — Critiqal`, description: thread.summary };
}

export default async function ThreadPage({ params }: Props) {
  const { id } = await params;
  const thread = getThread(id);
  if (!thread) notFound();

  // Newest chapter first — readers come for the latest, then scroll back.
  const chapters = [...thread.events].reverse();

  return (
    <div style={{ background: '#f7f4ee', minHeight: '100vh' }}>
      {/* Top nav */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 30,
        background: 'rgba(247,244,238,.92)', backdropFilter: 'blur(8px)',
        borderBottom: '1px solid #e1d8c8',
      }}>
        <div style={{
          maxWidth: 820, margin: '0 auto', padding: '0 28px',
          height: 52, display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <Link href="/threads" style={{
            display: 'inline-flex', alignItems: 'center', gap: 7,
            font: '500 13px/1 var(--font-archivo), system-ui', color: '#6a6052', textDecoration: 'none',
          }}>
            <span style={{ fontSize: 15 }}>←</span>
            <CritiqalLogo width={58} />
          </Link>
          <div style={{
            font: '600 10px/1 var(--font-archivo), system-ui',
            letterSpacing: '.16em', textTransform: 'uppercase',
            color: thread.status === 'developing' ? '#b08a4a' : '#a3957f',
          }}>
            {thread.status === 'developing' ? 'Developing story' : 'Past story'}
          </div>
        </div>
      </div>

      <main style={{ maxWidth: 820, margin: '0 auto', padding: '28px 28px 90px' }}>
        {/* Header */}
        <header style={{ marginBottom: 28 }}>
          <h1 style={{
            fontFamily: 'var(--font-spectral), serif', fontWeight: 600, fontSize: 36,
            lineHeight: 1.12, letterSpacing: '-.022em', color: '#141109', margin: 0,
            textWrap: 'balance',
          } as React.CSSProperties}>
            {thread.title}
          </h1>
          <p style={{
            fontFamily: 'var(--font-spectral), serif', fontStyle: 'italic', fontSize: 19,
            lineHeight: 1.5, color: '#5b5249', margin: '16px 0 0',
          }}>
            {thread.summary}
          </p>
          <div style={{
            font: '500 11px/1 var(--font-archivo), system-ui',
            letterSpacing: '.1em', textTransform: 'uppercase', color: '#a3957f', marginTop: 16,
          }}>
            {thread.events.length} developments · {thread.beats.map(beatLabel).join(' · ')}
          </div>
        </header>

        {/* Timeline — newest first, each chapter a link to the full event */}
        <div style={{ borderLeft: '2px solid #e7e0d4', paddingLeft: 0 }}>
          {chapters.map((ch, i) => {
            const event = getEvent(ch.cluster_id);
            const isLatest = i === 0;
            return (
              <div key={ch.cluster_id} style={{ position: 'relative', paddingLeft: 26, paddingBottom: i === chapters.length - 1 ? 0 : 30 }}>
                {/* node */}
                <span style={{
                  position: 'absolute', left: -6, top: 4, width: 10, height: 10, borderRadius: '50%',
                  background: isLatest ? '#b08a4a' : '#cdc3b2', border: '2px solid #f7f4ee',
                }} />
                <div style={{
                  font: '600 11px/1 var(--font-archivo), system-ui',
                  letterSpacing: '.08em', textTransform: 'uppercase',
                  color: isLatest ? '#b08a4a' : '#a3957f', marginBottom: 8,
                }}>
                  {new Date(ch.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
                  {isLatest && ' · Latest'}
                </div>
                <Link href={`/event/${ch.cluster_id}`} style={{ textDecoration: 'none' }}>
                  <h2 style={{
                    fontFamily: 'var(--font-spectral), serif', fontWeight: 600, fontSize: 21,
                    lineHeight: 1.25, color: '#141109', margin: 0,
                  }}>
                    {event?.event.title ?? ch.cluster_id}
                  </h2>
                </Link>
                {ch.chapter_summary && (
                  <p style={{
                    fontFamily: 'var(--font-spectral), serif', fontSize: 16, lineHeight: 1.6,
                    color: '#5b5249', margin: '8px 0 0',
                  }}>
                    {ch.chapter_summary}
                  </p>
                )}
                <Link href={`/event/${ch.cluster_id}`} style={{
                  display: 'inline-block', marginTop: 8,
                  font: '500 12px/1 var(--font-archivo), system-ui', color: '#b08a4a', textDecoration: 'none',
                }}>
                  Read the full report →
                </Link>
              </div>
            );
          })}
        </div>
      </main>
    </div>
  );
}
