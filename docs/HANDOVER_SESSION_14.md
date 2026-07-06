# HANDOVER — Session 14
## News Synthesis & Credibility Engine
**Handover date:** 6 July 2026
**Prepared by:** Claude Code (Fable 5), Session 14
**Owner:** G (GitHub: Ephemiral)

---

## 0. Read this first

1. `docs/00_MASTER_DOCUMENT.md` — single source of truth. **New §15** documents everything added this session.
2. **The pipeline now runs by itself.** A launchd job executes `scripts/auto_run.py` every 4 hours: ingest → cluster → qualify → analyze/annotate/generate → attach image → commit + push (Vercel auto-deploys). If you are a future session, check `data/logs/autorun/` before assuming nothing has happened since the last human session.
3. Schema is now **v0.3**: per-event JSON gained an optional `event.image` object (openly-licensed Wikimedia Commons file photo with full attribution).

---

## 1. What was done this session (6 July 2026)

### 1a. Image stage (`pipeline/images/`)
- `wikimedia.py` — Commons search; only CC0 / CC BY / CC BY-SA / public-domain files accepted (NC/ND rejected); attribution metadata extracted and preserved.
- `select.py` — Haiku proposes 2–4 concrete visual queries from the event title/summary, then a disqualify-then-pick prompt chooses the best candidate or rejects all. Key guardrail learned in testing: **a photo of the right place featuring the wrong person must be disqualified** (the first prompt version picked a Situation-Room photo featuring the wrong administration for a Trump-era story).
- `run.py` — CLI: `python3 -m pipeline.images.run --event-id X [--force]` / `--all-missing`. Writes `event.image` (or `null` + `image_attempted_at` so automation doesn't retry forever).
- All existing events backfilled. Roughly 2/3 got images; the rest correctly got none ("no image" is always acceptable; a wrong image is not).

### 1b. Front end
- `web/lib/types.ts` — `EventImage` type, `EventMeta.image`.
- Homepage: thumbnail (168×118) to the right of each event card when present.
- Event page: hero image above the bias legend with a full credit line (caption — credit, Wikimedia Commons link, license link). The credit line is a **license requirement** for CC BY / CC BY-SA — never remove it.

### 1c. Autonomous runner (`scripts/auto_run.py`)
- Codifies the manual event-selection criteria as hard gates: size 4–40, ≥3 outlets, cross-spectrum (≥1 left-of-center AND ≥1 right-of-center), ≥3 usable bodies, cohesion ≥0.65, ≤40% URL overlap with published events, one-attempt-per-article-set fingerprinting.
- Publishes at most 2 events per cycle (`--max-events`), IDs `evt_YYYY_MM_DD_auto_NNN`.
- Failed events are cleaned up, not published. Lock file prevents overlap. Per-run JSON logs in `data/logs/autorun/`.
- Auto mode writes only the *selected* clusters' JSON files (the manual `--discover` flow's habit of dumping every cluster to `data/events/` is why there are ~6,000 raw files there).
- `run_pipeline_for_event` was extracted from `scripts/scale_test.py` into `pipeline/run_event.py` (shared by both flows; scale_test CLI unchanged).

### 1d. Scheduling
- `config/launchd/com.critiqal.newsroom.autorun.plist` → installed at `~/Library/LaunchAgents/`. Every 4h while the Mac is awake.
- Disable: `launchctl bootout gui/$(id -u)/com.critiqal.newsroom.autorun`
- Run now: `launchctl kickstart gui/$(id -u)/com.critiqal.newsroom.autorun`
- Logs: `data/logs/autorun/launchd.{out,err}.log` + per-run `run_*.json`.

---

## 2. Operating the autonomous pipeline

```bash
# Manual cycle (same thing launchd runs)
.venv/bin/python3 scripts/auto_run.py

# See what would be published without spending tokens
.venv/bin/python3 scripts/auto_run.py --dry-run

# Check what automation has done lately
ls -t data/logs/autorun/run_*.json | head -3 | xargs cat
```

**Spot-check duty:** automation supersedes the "human review before publish" mitigation (owner decision, July 2026). Review new events on the homepage every day or two, especially image choices and contested-claim classifications.

---

## 3. Known issues / next work

| Item | Notes |
|---|---|
| **Homepage duplicates (B-13)** | Pre-existing: several near-duplicate events are live (e.g. three "US-Iran Ceasefire Extension Framework" variants). The novelty gate stops *new* duplicates but old ones need manual cleanup — dedupe/merge, then delete the redundant `*_analyzed.json` files. |
| B-10 remaining | `claim_ids` often empty in report paragraphs. |
| Validator feedback (M6/M9) | Still none received. |
| Image relevance | Commons only has file photos, not event photos. Watch for subtle mismatches; the disqualify prompt is new. |
| world_news beat | Config exists but automation currently runs israel_middle_east only (`--beat` per invocation; a second launchd job or a loop in auto_run would enable it). |

---

## 4. Working conventions (unchanged)

Tracksheet first and last; golden dataset is the regression fixture; schema bumps logged in the Change Log; ask before heavy deps or structural changes; never commit `.env`.

---

## ADDENDUM — Session 14, part 2 (same day, 6 July 2026)

G reviewed part 1 and requested a second wave, all delivered:

1. **B-16/B-02 RESOLVED** (the project's long-standing contested-claims bane) — schema v0.4 adds optional `claim.dispute_type: "actor"`. Actor disputes stay `contested` with empty `contested_by` by design; every reporting outlet corroborates the dispute's existence; a "conflicting accounts" tag replaces the chip split in the UI. Validated: evt_066 0→3, evt_040 0→3, evt_062 1→4 contested claims. Details in Master Doc §13 B-16 (RESOLVED block).
2. **Homepage dedup** — 9 duplicate/grab-bag events removed (kept richest variant of each story); 6,051 stale raw cluster files deleted. `data/events/` now holds only published events.
3. **Image engine v2** — Openverse second provider, angle-specific queries (military ≠ shipping ≠ talks imagery), cross-event image dedup (no shared file photos). The two Hormuz stories now have visually distinct, angle-appropriate images.
4. **GitHub Actions** — `.github/workflows/autorun.yml` (cron every 6h + manual). **Waiting on one manual step: add the `ANTHROPIC_API_KEY` repo secret**, then disable launchd (`launchctl bootout gui/$(id -u)/com.critiqal.newsroom.autorun`). Run ONE scheduler, never both. State ledger moved to tracked `data/autorun/state.json`. Private-repo minutes caveat documented in the workflow header.
5. **Alerts** — CI failure → auto GitHub issue (`autorun-failure` label) + email; local failure → macOS notification.
6. **Go-live polish** — `/about` methodology page, OG meta tags (event image in social shares), `sitemap.xml`, `robots.txt`, "Neutral synthesis" tagline corrected to "Transparent synthesis" (fixed positioning decision, Master Doc §8).
7. **Multi-theatre** — new beats `europe` / `americas` / `asia` (feeds live-verified, 13 new outlets in the provenance registry), homepage theatre tabs, `auto_run --beats` loops all four, novelty gate global across beats. launchd reloaded with all four theatres.

**Watch items for next session:** first auto-published events in the new theatres (spot-check outlet diversity + images); whether Fox topic_filters are too broad/narrow; GH Actions first green run once the secret is added; B-17 (state-aligned outlets) remains open for G's decision; B-10 (claim_ids) unchanged.

---

## ADDENDUM — Session 14, part 3 (same day)

1. **B-17 RESOLVED** — state-aligned outlets added with loud labeling: RT News (europe), Global Times (asia), Asharq Al-Awsat + Saudi Gazette (middle east). `state_alignment` field flows config → Article → sources[] → UI (⚑ chips, red outlet-card badge, About section). Enforced as *perspective, not corroboration*: excluded from the auto_run spectrum gate and B-01's agreed tier count; prompts require inline attribution ("Russian state-controlled RT reported that…").
2. **Developing news** — novelty gate redefined: a cluster needs ≥50% previously-unpublished URLs (same-articles block, not same-story block). Overlapping prior events are recorded in `event.related_events` and shown as an "Earlier coverage of this story" box. Follow-ups now publish as linked developments.
3. **UI** — beat label is now "Middle East" everywhere (`web/lib/beats.ts` is the single label map); the event image moved from the top hero into the report body after the lede paragraph (`EventImageFigure`, placement heuristic in `ReportView`).
4. **⚠ launchd is TCC-blocked** — background launchd jobs cannot read `~/Documents` (macOS privacy). Every scheduled run dies with PermissionError before doing anything; today's successful cycles all ran from an interactive shell. Fix: System Settings → Privacy & Security → Full Disk Access → add `/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app`, then `launchctl kickstart gui/$(id -u)/com.critiqal.newsroom.autorun` and confirm a run log appears. Alternative: activate GitHub Actions (part-2 addendum steps) and skip local scheduling entirely. **Until one of these happens, nothing publishes automatically.**
5. GH Actions activation (PAT `workflow` scope + secret) still pending — G deferred to next session.
