import { EventImage } from '@/lib/types';

/**
 * Openly-licensed event file photo with its attribution line.
 * The credit line is a license requirement (CC BY / CC BY-SA) — never remove it.
 */
export default function EventImageFigure({ image }: { image: EventImage }) {
  return (
    <figure style={{ margin: '28px 0' }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={image.url}
        alt={image.caption}
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
        {image.caption}
        {' — '}
        {image.credit},{' '}
        <a
          href={image.source_page}
          target="_blank"
          rel="noopener noreferrer"
          style={{ color: '#9a8d7c', textDecoration: 'underline' }}
        >
          {image.provider === 'openverse' ? 'Openverse' : 'Wikimedia Commons'}
        </a>
        {' '}(
        {image.license_url ? (
          <a
            href={image.license_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: '#9a8d7c', textDecoration: 'underline' }}
          >
            {image.license}
          </a>
        ) : (
          image.license
        )}
        )
      </figcaption>
    </figure>
  );
}
