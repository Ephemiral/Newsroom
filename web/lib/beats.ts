/** Theatre display labels — order defines tab order on the homepage.
 *  Keys match beat names in config/beats/ (internal names never change;
 *  labels are presentation-only). */
export const BEAT_LABELS: Record<string, string> = {
  israel_middle_east: 'Middle East',
  europe: 'Europe',
  americas: 'Americas',
  asia: 'Asia',
};

export function beatLabel(beat: string): string {
  return BEAT_LABELS[beat] ?? beat.replace(/_/g, ' ');
}
