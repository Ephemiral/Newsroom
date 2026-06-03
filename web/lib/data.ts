import fs from 'fs';
import path from 'path';
import { AnalyzedEvent } from './types';

const DATA_DIR = path.join(process.cwd(), '..', 'data', 'events');

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
