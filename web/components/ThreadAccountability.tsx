'use client';

import { useState } from 'react';
import { AccountabilityFlag } from '@/lib/types';

/* ── "How the reporting changed" (STAGE_9) ────────────────────────────────────
 * Where an outlet's OWN reporting reversed across the thread. Both instances are
 * shown with EQUAL weight in parallel language — no side gets a warning colour or
 * a credibility label; the reader judges. Only approved flags reach this
 * component (the thread page filters review_status === "approved").
 */

const TYPE_LABEL: Record<AccountabilityFlag['type'], string> = {
  contradiction: 'Contradiction',
  correction: 'Correction',
  retraction: 'Retraction',
};

function Instance({ label, date, text, url }: { label: string; date: string; text: string; url: string }) {
  return (
    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{
        font: '600 10px/1 var(--font-archivo), system-ui',
        letterSpacing: '.1em', textTransform: 'uppercase', color: '#a3957f', marginBottom: 6,
      }}>
        {label} · {new Date(date).toLocaleDateString('en-GB', { day: 'numeric', month: 'long', year: 'numeric' })}
      </div>
      <p style={{
        fontFamily: 'var(--font-spectral), serif', fontSize: 15, lineHeight: 1.55, color: '#2a2319', margin: 0,
      }}>
        “{text}”
      </p>
      <a href={url} target="_blank" rel="noreferrer" style={{
        display: 'inline-block', marginTop: 6,
        font: '500 11px/1 var(--font-archivo), system-ui', color: '#b08a4a', textDecoration: 'none',
      }}>
        Read the article →
      </a>
    </div>
  );
}

export default function ThreadAccountability({ flags }: { flags: AccountabilityFlag[] }) {
  const [open, setOpen] = useState(false);
  if (flags.length === 0) return null;

  return (
    <section style={{ margin: '0 0 28px', border: '1px solid #e2d7c2', borderRadius: 6, background: '#f2ede4' }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          background: 'none', border: 'none', cursor: 'pointer', padding: '14px 18px', textAlign: 'left',
        }}
      >
        <span style={{
          font: '600 12px/1 var(--font-archivo), system-ui',
          letterSpacing: '.04em', color: '#3a332a',
        }}>
          How the reporting changed · {flags.length}
        </span>
        <span style={{ font: '500 12px/1 var(--font-archivo), system-ui', color: '#8a7d6c' }}>
          {open ? 'Hide' : 'Show'}
        </span>
      </button>

      {open && (
        <div style={{ padding: '0 18px 18px' }}>
          <p style={{
            fontFamily: 'var(--font-spectral), serif', fontStyle: 'italic', fontSize: 13, lineHeight: 1.5,
            color: '#8a7d6c', margin: '0 0 16px',
          }}>
            This shows an outlet&apos;s own reporting at two points in the story. A developing story changes;
            this section flags only where an outlet&apos;s account of the same fact changed.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {flags.map((f) => (
              <div key={f.id} style={{
                background: '#f7f4ee', border: '1px solid #e7e0d4', borderRadius: 5, padding: '14px 16px',
              }}>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 4 }}>
                  <span style={{
                    font: '600 10px/1 var(--font-archivo), system-ui',
                    letterSpacing: '.08em', textTransform: 'uppercase', color: '#6a6052',
                  }}>
                    {TYPE_LABEL[f.type]}
                  </span>
                  <span style={{ font: '600 13px/1 var(--font-archivo), system-ui', color: '#141109' }}>
                    {f.outlet}
                  </span>
                </div>
                {f.note && (
                  <p style={{
                    fontFamily: 'var(--font-spectral), serif', fontSize: 14, lineHeight: 1.5, color: '#5b5249',
                    margin: '0 0 14px',
                  }}>
                    {f.note}
                  </p>
                )}
                <div style={{ display: 'flex', gap: 18, flexWrap: 'wrap' }}>
                  <Instance label="Earlier" date={f.earlier.date} text={f.earlier.text} url={f.earlier.url} />
                  <span style={{ alignSelf: 'center', font: '600 14px/1 var(--font-archivo), system-ui', color: '#a3957f' }}>→</span>
                  <Instance label="Later" date={f.later.date} text={f.later.text} url={f.later.url} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
