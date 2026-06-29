interface CritiqalLogoProps {
  /** Display width in px. Height scales proportionally from the 348×88 viewBox. */
  width?: number;
}

export default function CritiqalLogo({ width = 290 }: CritiqalLogoProps) {
  const height = Math.round((width / 348) * 88);
  return (
    <svg
      viewBox="0 0 348 88"
      width={width}
      height={height}
      style={{ overflow: "visible" }}
      aria-label="Critiqal"
      role="img"
    >
      <text
        x="18" y="66"
        fontFamily="var(--font-archivo), sans-serif"
        fontWeight="800"
        fontSize="58"
        letterSpacing="1.5"
        fill="#141109"
      >
        CRITI
      </text>
      <circle cx="215" cy="46" r="21" stroke="#141109" strokeWidth="7" fill="none" />
      <line x1="230" y1="61" x2="244" y2="75" stroke="#141109" strokeWidth="7" strokeLinecap="round" />
      <text
        x="244" y="66"
        fontFamily="var(--font-archivo), sans-serif"
        fontWeight="800"
        fontSize="58"
        letterSpacing="1.5"
        fill="#141109"
      >
        AL
      </text>
    </svg>
  );
}
