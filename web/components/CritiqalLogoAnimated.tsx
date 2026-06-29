'use client';

import { useState, useEffect } from 'react';
import CritiqalLogo from './CritiqalLogo';

const STORAGE_KEY = 'critiqal_intro_seen';
const ANIM_DURATION_MS = 4200; // slightly longer than 3.4s CSS animation

const textProps = {
  fontFamily: 'var(--font-archivo), sans-serif',
  fontWeight: 800 as const,
  fontSize: 58,
  letterSpacing: 1.5,
  fill: '#141109',
};

function AnimatedLogo() {
  const easing = 'cubic-bezier(.45,0,.3,1)';
  const duration = '3.4s';
  const timing = `${duration} ${easing} forwards`;

  return (
    <div style={{ position: 'relative', width: 348, height: 88 }}>

      {/* Layer 1 — blurry base (CRITI + AL, no Q) */}
      <svg
        viewBox="0 0 348 88" width="348" height="88"
        style={{ filter: 'blur(7px)', animation: `cr-blur-fade ${timing}` }}
      >
        <text x="18"  y="66" {...textProps}>CRITI</text>
        <text x="244" y="66" {...textProps}>AL</text>
      </svg>

      {/* Layer 2 — trailing reveal: grows rightward as lens passes */}
      <div style={{
        position: 'absolute', top: 0, left: 0, width: 348, height: 88,
        animation: `cr-trailing ${timing}`,
      }}>
        <svg viewBox="0 0 348 88" width="348" height="88">
          <text x="18"  y="66" {...textProps}>CRITI</text>
          <text x="244" y="66" {...textProps}>AL</text>
        </svg>
      </div>

      {/* Layer 3 — lens preview: shows upcoming letter sharply inside the ring */}
      <div style={{
        position: 'absolute', top: 0, left: 0, width: 348, height: 88,
        animation: `cr-lens ${timing}`,
      }}>
        <svg viewBox="0 0 348 88" width="348" height="88">
          <text x="18"  y="66" {...textProps}>CRITI</text>
          <text x="244" y="66" {...textProps}>AL</text>
        </svg>
      </div>

      {/* Layer 4 — moving magnifying glass Q */}
      <svg
        viewBox="0 0 348 88" width="348" height="88"
        style={{ position: 'absolute', top: 0, left: 0, overflow: 'visible', pointerEvents: 'none' }}
      >
        <g style={{ animation: `cr-qtravel ${timing}` }}>
          <circle cx="215" cy="46" r="21" stroke="#141109" strokeWidth="7" fill="rgba(247,244,238,0.45)" />
          <line x1="230" y1="61" x2="244" y2="75" stroke="#141109" strokeWidth="7" strokeLinecap="round" />
        </g>
      </svg>

    </div>
  );
}

/**
 * Shows the lens-sweep intro animation on first visit (gated by localStorage),
 * then falls back to the static CritiqalLogo. Safe for SSR — renders the static
 * logo during hydration and upgrades client-side.
 */
export default function CritiqalLogoAnimated() {
  // null = not yet checked (SSR / hydration), true = play, false = static
  const [mode, setMode] = useState<'static' | 'anim' | 'pending'>('pending');

  useEffect(() => {
    try {
      if (localStorage.getItem(STORAGE_KEY)) {
        setMode('static');
      } else {
        setMode('anim');
        const timer = setTimeout(() => {
          try { localStorage.setItem(STORAGE_KEY, '1'); } catch { /* quota */ }
          setMode('static');
        }, ANIM_DURATION_MS);
        return () => clearTimeout(timer);
      }
    } catch {
      setMode('static');
    }
  }, []);

  if (mode === 'anim') return <AnimatedLogo />;
  return <CritiqalLogo width={290} />;
}
