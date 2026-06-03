import { notFound } from 'next/navigation';
import { getEvent } from '@/lib/data';
import OutletCard from '@/components/OutletCard';
import ClaimSection from '@/components/ClaimSection';
import BiasLegend from '@/components/BiasLegend';
import ReportView from '@/components/ReportView';

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
    <main className="max-w-4xl mx-auto px-4 py-10 font-sans text-gray-900">

      {/* Header */}
      <header className="mb-8">
        <div className="text-xs font-semibold uppercase tracking-widest text-gray-400 mb-2">
          {event.event.beat.replace(/_/g, ' ')}
        </div>
        <h1 className="text-3xl font-bold leading-tight mb-4">{event.event.title}</h1>
        <p className="text-lg text-gray-600 leading-relaxed">{event.event.summary}</p>
        <div className="mt-3 text-sm text-gray-500">
          {new Date(event.event.date).toLocaleDateString(undefined, {
            day: 'numeric', month: 'long', year: 'numeric',
          })}
          <span className="text-gray-400">
            {' · '}{event.sources.length} sources · {event.claims.length} claims extracted
          </span>
        </div>
      </header>

      {/* Report (M8) — shown when report field is populated */}
      {event.report && (
        <ReportView
          report={event.report}
          claimsMap={claimsMap}
          sourceMap={sourceMap}
        />
      )}

      {/* Claims */}
      <section className="mb-12">
        <h2 className="text-xl font-bold mb-4">What the coverage shows</h2>
        <ClaimSection
          label="Agreed across the spectrum"
          description="Reported consistently by outlets spanning different sides of the political spectrum."
          claims={agreed}
          sourceMap={sourceMap}
          accent="green"
        />
        <ClaimSection
          label="Corroborated"
          description="Reported by multiple outlets, but all from the same part of the spectrum."
          claims={corroborated}
          sourceMap={sourceMap}
          accent="teal"
        />
        <ClaimSection
          label="Contested"
          description="Sources conflict or frame this fact in genuinely incompatible ways."
          claims={contested}
          sourceMap={sourceMap}
          accent="amber"
        />
        <ClaimSection
          label="Single source"
          description="Only one outlet in this cluster reported this."
          claims={singleSource}
          sourceMap={sourceMap}
          accent="gray"
        />
        {/* Bias spectrum legend — nested within claims section */}
        <BiasLegend sources={event.sources} />
      </section>

      {/* Background */}
      {event.background.length > 0 && (
        <section className="mb-12">
          <h2 className="text-xl font-bold mb-4">Background</h2>
          <ul className="space-y-3">
            {event.background.map((b, i) => (
              <li key={i} className="flex gap-3">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-gray-400 flex-shrink-0" />
                <span className="text-gray-700">{b.point}</span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Sources — grouped by outlet */}
      <section>
        {(() => {
          const grouped = event.sources.reduce<Record<string, typeof event.sources>>((acc, src) => {
            (acc[src.outlet] ??= []).push(src);
            return acc;
          }, {});
          const outlets = Object.entries(grouped);
          return (
            <>
              <h2 className="text-xl font-bold mb-6">
                Sources ({outlets.length} outlet{outlets.length !== 1 ? 's' : ''}, {event.sources.length} article{event.sources.length !== 1 ? 's' : ''})
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {outlets.map(([outlet, sources]) => (
                  <OutletCard key={outlet} outlet={outlet} sources={sources} />
                ))}
              </div>
            </>
          );
        })()}
      </section>

    </main>
  );
}
