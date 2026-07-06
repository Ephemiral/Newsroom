import { MetadataRoute } from 'next';
import { getEventIds, getEvent } from '@/lib/data';

const SITE_URL = process.env.NEXT_PUBLIC_SITE_URL ?? 'https://newsroom-sand-seven.vercel.app';

export const dynamic = 'force-dynamic';

export default function sitemap(): MetadataRoute.Sitemap {
  const events = getEventIds().map((id) => {
    const event = getEvent(id);
    return {
      url: `${SITE_URL}/event/${id}`,
      lastModified: event?.event.generated_at ? new Date(event.event.generated_at) : new Date(),
    };
  });
  return [
    { url: SITE_URL, lastModified: new Date() },
    { url: `${SITE_URL}/about`, lastModified: new Date() },
    ...events,
  ];
}
