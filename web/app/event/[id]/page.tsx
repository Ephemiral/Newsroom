import Link from 'next/link';
import { notFound } from 'next/navigation';
import { getEvent } from '@/lib/data';
import OutletCard from '@/components/OutletCard';
import ClaimSection from '@/components/ClaimSection';
import BiasLegend from '@/components/BiasLegend';
import ReportView from '@/components/ReportView';
import CritiqalLogo from '@/components/CritiqalLogo';

// Render on demand — new event JSON files are picked up without restarting the server
export const dynamic = 'force-dynamic';

interface Props {
  params: Promise<{ id: string }>;
}

export default async function EventPage({ params }: Props) {
  const { id } = await params;
  const event = getEvent(id);
  if (!event) notFound();

  const sourceMap = Object.fromEntries(event.sources.map((s) => [s.source_id, s]));
  const claimsMap = Object.fromEntries(event.claims.map((c) => [c.claim_id, c]));
  const agreed       = event.claims.filter((c) => c.classification === 'agreed');
  const corroborated = event.claims.filter((c) => c.classification === 'corroborated');
  const contested    = event.claims.filter((c) => c.classification === 'contested');
  const singleSource = event.claims.filter((c) => c.classification === 'single_source');

  return (
    <div style={{ background: '#f7f4ee', minHeight: '100vh' }}>

      {/* ── Sticky top nav ──────────────────────────────────────────────── */}
      <div style={{
        position: 'sticky', top: 0, zIndex: 30,
        background: 'rgba(247,244,238,.92)',
        backdropFilter: 'blur(8px)',
        borderBottom: '1px solid #e1d8c8',
      }}>
        <div style={{
          maxWidth: 720, margin: '0 auto', padding: '0 28px',
          height: 52, display: 'flex', alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <Link
            href="/"
            style={{
              display: 'inline-flex', alignItems: 'center', gap: 7,
              font: '500 13px/1 var(--font-archivo), system-ui',
              color: '#6a6052', textDecoration: 'none',
            }}
          >
            <span style={{ fontSize: 15 }}>←</span>
            <CritiqalLogo width={58} />
          </Link>
          <div style={{
            font: '600 10px/1 var(--font-archivo), system-ui',
            letterSpacing: '.16em', textTransform: 'uppercase', color: '#b08a4a',
          }}>
            {event.event.beat.replace(/_/g, ' ')}
          </div>
        </div>
      </div>

      {/* ── Article body ────────────────────────────────────────────────── */}
      <main style={{ maxWidth: 720, margin: '0 auto', padding: '44px 28px 90px' }}>

        {/* Header */}
        <header style={{ marginBottom: 32 }}>
          <h1 style={{
            fontFamily: 'var(--font-spectral), serif',
            fontWeight: 600, fontSize: 38, lineHeight: 1.12,
            letterSpacing: '-.022em', color: '#141109',
            margin: 0, textWrap: 'balance',
          } as React.CSSProperties}>
            {event.event.title}
          </h1>
          <p style={{
            fontFamily: 'var(--font-spectral), serif',
            fontStyle: 'italic', fontSize: 19, lineHeight: 1.5,
            color: '#5b5249', margin: '18px 0 0',
          }}>
            {event.event.summary}
          </p>
          <div style={{
            font: '500 11px/1 var(--font-archivo), system-ui',
            letterSpacing: '.1em', textTransform: 'uppercase',
            color: '#a3957f', marginTop: 16,
          }}>
            {new Date(event.event.date).toLocaleDateString('en-GB', {
              day: 'numeric', month: 'long', year: 'numeric',
            })}
            {' · '}
            {event.sources.length} sources · {event.claims.length} claims
          </div>
        </header>

        {/* Hero image (openly licensed file photo, with required attribution) */}
        {event.event.image && (
          <figure style={{ margin: '0 0 36px' }}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={event.event.image.url}
              alt={event.event.image.caption}
              style={{
                width: '100%', maxHeight: 400, objectFit: 'cover',
                borderRadius: 4, border: '1px solid #e1d8c8', background: '#ece6da',
                display: 'block',
              }}
            />
            <figcaption style={{
              fontFamily: 'var(--font-spectral), serif',
              fontStyle: 'italic', fontSize: 13, lineHeight: 1.5,
              color: '#9a8d7c', marginTop: 8,
            }}>
              {event.event.image.caption}
              {' — '}
              {event.event.image.credit},{' '}
              <a
                href={event.event.image.source_page}
                target="_blank"
                rel="noopener noreferrer"
                style={{ color: '#9a8d7c', textDecoration: 'underline' }}
              >
                Wikimedia Commons
              </a>
              {' '}(
              {event.event.image.license_url ? (
                <a
                  href={event.event.image.license_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: '#9a8d7c', textDecoration: 'underline' }}
                >
                  {event.event.image.license}
                </a>
              ) : (
                event.event.image.license
              )}
              )
            </figcaption>
          </figure>
        )}

        {/* Spectrum — who covered this */}
        <div style={{ marginBottom: 48 }}>
          <BiasLegend sources={event.sources} />
        </div>

        {/* Report */}
        {event.report && (
          <ReportView
            report={event.report}
            claimsMap={claimsMap}
            sourceMap={sourceMap}
          />
        )}

        {/* Claims */}
        <section style={{ marginBottom: 48 }}>
          <h2 style={{
            fontFamily: 'var(--font-spectral), serif',
            fontWeight: 600, fontSize: 22, color: '#141109', marginBottom: 16,
          }}>
            What the coverage shows
          </h2>
          <ClaimSection label="Agreed across the spectrum" description="Reported consistently by outlets spanning different sides of the political spectrum." claims={agreed} sourceMap={sourceMap} accent="green" />
          <ClaimSection label="Corroborated" description="Reported by multiple outlets, but all from the same part of the spectrum." claims={corroborated} sourceMap={sourceMap} accent="teal" />
          <ClaimSection label="Contested" description="Sources conflict or frame this fact in genuinely incompatible ways." claims={contested} sourceMap={sourceMap} accent="amber" />
          <ClaimSection label="Single source" description="Only one outlet in this cluster reported this." claims={singleSource} sourceMap={sourceMap} accent="gray" />
        </section>

        {/* Background */}
        {event.background.length > 0 && (
          <section style={{ marginBottom: 48 }}>
            <h2 style={{
              fontFamily: 'var(--font-spectral), serif',
              fontWeight: 600, fontSize: 22, color: '#141109', marginBottom: 16,
            }}>
              Background
            </h2>
            <ul style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 12 }}>
              {event.background.map((b, i) => (
                <li key={i} style={{ display: 'flex', gap: 12 }}>
                  <span style={{ marginTop: 7, width: 6, height: 6, borderRadius: '50%', background: '#c8bfae', flexShrink: 0, display: 'inline-block' }} />
                  <span style={{ fontFamily: 'var(--font-spectral), serif', fontSize: 16, lineHeight: 1.6, color: '#5b5249' }}>{b.point}</span>
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Outlets */}
        <section>
          {(() => {
            const grouped = event.sources.reduce<Record<string, typeof event.sources>>((acc, src) => {
              (acc[src.outlet] ??= []).push(src);
              return acc;
            }, {});
            const outlets = Object.entries(grouped);
            return (
              <>
                <h2 style={{
                  fontFamily: 'var(--font-spectral), serif',
                  fontWeight: 600, fontSize: 22, color: '#141109', marginBottom: 20,
                }}>
                  The {outlets.length} outlet{outlets.length !== 1 ? 's' : ''} behind this story
                </h2>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 14 }}>
                  {outlets.map(([outlet, sources]) => (
                    <OutletCard key={outlet} outlet={outlet} sources={sources} />
                  ))}
                </div>
                <p style={{
                  fontFamily: 'var(--font-spectral), serif',
                  fontStyle: 'italic', fontSize: 13, lineHeight: 1.5,
                  color: '#9a8d7c', marginTop: 18,
                }}>
                  Bias ratings sourced from AllSides and Media Bias/Fact Check. Ownership shown where disclosed.
                </p>
              </>
            );
          })()}
        </section>

      </main>
    </div>
  );
}
