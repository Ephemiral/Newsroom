import Link from 'next/link';
import CritiqalLogo from '@/components/CritiqalLogo';

export const metadata = {
  title: 'About & Methodology',
  description:
    'How Critiqal works: multi-outlet ingestion, claim-level classification, provenance for every source, and receipts for every conclusion.',
};

const h2: React.CSSProperties = {
  fontFamily: 'var(--font-spectral), serif',
  fontWeight: 600, fontSize: 22, color: '#141109',
  margin: '40px 0 12px',
};

const p: React.CSSProperties = {
  fontFamily: 'var(--font-spectral), serif',
  fontSize: 17, lineHeight: 1.65, color: '#3d372e',
  margin: '0 0 14px',
};

export default function AboutPage() {
  return (
    <div style={{ background: '#f7f4ee', minHeight: '100vh' }}>
      {/* Sticky top nav (mirrors the event page) */}
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
          <Link href="/" style={{
            display: 'inline-flex', alignItems: 'center', gap: 7,
            font: '500 13px/1 var(--font-archivo), system-ui',
            color: '#6a6052', textDecoration: 'none',
          }}>
            <span style={{ fontSize: 15 }}>←</span>
            <CritiqalLogo width={58} />
          </Link>
          <div style={{
            font: '600 10px/1 var(--font-archivo), system-ui',
            letterSpacing: '.16em', textTransform: 'uppercase', color: '#b08a4a',
          }}>
            About
          </div>
        </div>
      </div>

      <main style={{ maxWidth: 720, margin: '0 auto', padding: '44px 28px 90px' }}>
        <h1 style={{
          fontFamily: 'var(--font-spectral), serif',
          fontWeight: 600, fontSize: 38, lineHeight: 1.12,
          letterSpacing: '-.022em', color: '#141109', margin: 0,
        }}>
          Transparent, not neutral.
        </h1>
        <p style={{ ...p, fontStyle: 'italic', fontSize: 19, color: '#5b5249', marginTop: 18 }}>
          Critiqal does not promise objective truth — no one honestly can. It promises to show
          you the shape of the coverage: what outlets across the political spectrum agree on,
          where they diverge, who is behind each story, and the receipts for every conclusion.
        </p>

        <h2 style={h2}>How a story is built</h2>
        <p style={p}>
          For each news event, we ingest coverage from outlets spanning the political spectrum.
          Every factual claim in that coverage is extracted, then reconciled across outlets and
          classified:
        </p>
        <ul style={{ ...p, paddingLeft: 22, margin: '0 0 14px' }}>
          <li><strong>Agreed</strong> — reported consistently by outlets from different sides of the spectrum.</li>
          <li><strong>Corroborated</strong> — reported by multiple outlets, but all from the same side.</li>
          <li><strong>Contested</strong> — outlets conflict, or the actors in the story gave contradictory
            accounts (marked &ldquo;conflicting accounts&rdquo;). We surface disputes; we don&rsquo;t adjudicate them.</li>
          <li><strong>Single source</strong> — only one outlet reported it.</li>
        </ul>
        <p style={p}>
          The synthesized report you read first is generated from — and linked to — those
          classified claims. Every paragraph carries its receipts: the claims behind it, the
          outlets behind those claims, and why each claim was classified the way it was.
          Nothing is asserted without a source you can click through to.
        </p>

        <h2 style={h2}>Where the bias ratings come from</h2>
        <p style={p}>
          Outlet bias placements are sourced from independent raters (AllSides, Media Bias/Fact
          Check) — never our own verdicts. Ownership and funding information is shown on each
          outlet&rsquo;s provenance card where disclosed. If you think a rating is wrong, take it up
          with the raters — that&rsquo;s the point of citing them.
        </p>

        <h2 style={h2}>State-aligned outlets</h2>
        <p style={p}>
          Some sources are government-controlled or government-aligned — RT (Russia),
          Global Times (China), Asharq Al-Awsat and Saudi Gazette (Saudi Arabia). We include
          them deliberately: they are often the most direct record of what a government
          itself is claiming, which matters when the actors in a story dispute the facts.
          But they are perspective, not corroboration. They are flagged with a ⚑ marker
          everywhere they appear, their alignment is named inline whenever the report conveys
          their account (&ldquo;Russian state-controlled RT reported that&hellip;&rdquo;), and they
          never count toward &ldquo;agreed across the spectrum.&rdquo;
        </p>

        <h2 style={h2}>Images</h2>
        <p style={p}>
          Story images are openly licensed file photos (Wikimedia Commons, Openverse — CC0,
          CC&nbsp;BY, CC&nbsp;BY-SA, or public domain), credited beneath each image. They depict the
          people and places in a story, not the specific event itself.
        </p>

        <h2 style={h2}>Automation, honestly</h2>
        <p style={p}>
          The pipeline runs automatically: stories are selected by hard qualification rules
          (multiple outlets, both sides of the spectrum represented, coherent coverage) and
          every generated report passes validation checks before publishing, with human
          spot-checks after. If something slips through those checks, we want to know.
        </p>

        <h2 style={h2}>Contact</h2>
        <p style={p}>
          Feedback, corrections, and challenges are welcome:{' '}
          <a href="mailto:kafri.sg@gmail.com" style={{ color: '#b08a4a' }}>kafri.sg@gmail.com</a>.
        </p>
      </main>
    </div>
  );
}
