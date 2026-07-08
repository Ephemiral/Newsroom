import fs from 'fs';
import path from 'path';
import { AnalyzedEvent, EntityRecord, Thread } from './types';

const DATA_DIR = path.join(process.cwd(), '..', 'data', 'events');
const ENTITIES_DIR = path.join(process.cwd(), '..', 'data', 'entities');
const THREADS_DIR = path.join(process.cwd(), '..', 'data', 'threads');

/** One record from the persistent entity store, or null if absent/unreadable. */
export function getEntity(entityId: string): EntityRecord | null {
  // Entity ids are pipeline-minted slugs; guard against path traversal anyway.
  if (!/^ent_[a-z0-9_]+$/.test(entityId)) return null;
  const filePath = path.join(ENTITIES_DIR, `${entityId}.json`);
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as EntityRecord;
  } catch {
    return null;
  }
}

/** Map of entity_id -> record for the ids that exist in the store. */
export function getEntityMap(entityIds: string[]): Record<string, EntityRecord> {
  const map: Record<string, EntityRecord> = {};
  for (const id of entityIds) {
    const rec = getEntity(id);
    if (rec) map[id] = rec;
  }
  return map;
}

/** One thread (developing-story arc), or null if absent/unreadable. */
export function getThread(threadId: string): Thread | null {
  if (!/^thr_[a-z0-9_]+$/.test(threadId)) return null;
  try {
    return JSON.parse(fs.readFileSync(path.join(THREADS_DIR, `${threadId}.json`), 'utf-8')) as Thread;
  } catch {
    return null;
  }
}

/** All threads, most recently active first (developing above dormant). */
export function getThreads(): Thread[] {
  let files: string[] = [];
  try {
    files = fs.readdirSync(THREADS_DIR).filter((f) => f.startsWith('thr_') && f.endsWith('.json'));
  } catch {
    return [];
  }
  const threads = files
    .map((f) => {
      try {
        return JSON.parse(fs.readFileSync(path.join(THREADS_DIR, f), 'utf-8')) as Thread;
      } catch {
        return null;
      }
    })
    .filter((t): t is Thread => t !== null);
  const rank = (t: Thread) => (t.status === 'developing' ? 0 : 1);
  return threads.sort(
    (a, b) => rank(a) - rank(b) || b.last_updated.localeCompare(a.last_updated),
  );
}

export function getEventIds(): string[] {
  const ids: string[] = [];
  for (const beat of fs.readdirSync(DATA_DIR)) {
    const beatDir = path.join(DATA_DIR, beat);
    if (!fs.statSync(beatDir).isDirectory()) continue;
    for (const file of fs.readdirSync(beatDir)) {
      if (file.endsWith('_analyzed.json')) {
        ids.push(file.replace('_analyzed.json', ''));
      }
    }
  }
  return ids;
}

export function getEvent(clusterId: string): AnalyzedEvent | null {
  for (const beat of fs.readdirSync(DATA_DIR)) {
    const beatDir = path.join(DATA_DIR, beat);
    if (!fs.statSync(beatDir).isDirectory()) continue;
    const filePath = path.join(beatDir, `${clusterId}_analyzed.json`);
    if (fs.existsSync(filePath)) {
      return JSON.parse(fs.readFileSync(filePath, 'utf-8')) as AnalyzedEvent;
    }
  }
  return null;
}

export interface LoadedEvent {
  id: string;
  event: AnalyzedEvent;
}

/** One story on the homepage: the most recent event as the card, with any
 *  earlier events it develops (linked via related_events) nested underneath.
 *  Collapses a multi-day story into a single card instead of N. */
export interface EventGroup {
  id: string;
  event: AnalyzedEvent;
  earlier: LoadedEvent[];
}

const eventDate = (e: AnalyzedEvent) => new Date(e.event.date).getTime();

/**
 * Group events into stories by their `related_events` edges (undirected —
 * developments point back at earlier coverage). Each connected component
 * becomes one group whose representative is the newest member; the rest are
 * returned as `earlier`, newest first. Groups are sorted newest-first.
 */
export function getEventGroups(): EventGroup[] {
  const byId = new Map<string, AnalyzedEvent>();
  for (const id of getEventIds()) {
    const ev = getEvent(id);
    if (ev) byId.set(id, ev);
  }

  // Union-find over related_events edges (ignoring dangling references).
  const parent = new Map<string, string>();
  for (const id of byId.keys()) parent.set(id, id);
  const find = (x: string): string => {
    let root = x;
    while (parent.get(root) !== root) root = parent.get(root)!;
    while (parent.get(x) !== root) {
      const next = parent.get(x)!;
      parent.set(x, root);
      x = next;
    }
    return root;
  };
  const union = (a: string, b: string) => {
    const ra = find(a), rb = find(b);
    if (ra !== rb) parent.set(ra, rb);
  };
  for (const [id, ev] of byId) {
    for (const rel of ev.event.related_events ?? []) {
      if (byId.has(rel.cluster_id)) union(id, rel.cluster_id);
    }
  }

  const components = new Map<string, LoadedEvent[]>();
  for (const [id, event] of byId) {
    const root = find(id);
    const list = components.get(root) ?? [];
    list.push({ id, event });
    components.set(root, list);
  }

  const groups: EventGroup[] = [];
  for (const members of components.values()) {
    members.sort((a, b) => eventDate(b.event) - eventDate(a.event));
    const [rep, ...earlier] = members;
    groups.push({ id: rep.id, event: rep.event, earlier });
  }
  groups.sort((a, b) => eventDate(b.event) - eventDate(a.event));
  return groups;
}
