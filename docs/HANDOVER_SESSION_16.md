# HANDOVER — Session 16
## News Synthesis & Credibility Engine ("Critiqal")
**Handover date:** 8 July 2026
**Prepared by:** Claude Code (Fable 5), Session 16
**Owner:** G (GitHub: Ephemiral)

---

## 0. Read this first

The product is **live and fully autonomous** — GitHub Actions runs the whole pipeline on a cron across four beats (Middle East, Europe, Americas, Asia) and publishes to Vercel with no human in the loop.

- **Live site:** https://newsroom-sand-seven.vercel.app
- **Repo (public):** https://github.com/Ephemiral/Newsroom
- **Source of truth:** `docs/00_MASTER_DOCUMENT.md`. **Read `docs/HANDOVER_SESSION_15.md` too** — it has the full build history, the GitHub Actions migration saga, and the file map. This doc (16) only covers what changed after 15 and the current live state.
- **Schema:** v0.4 (`pipeline/schema.py`).

At session start, check what the cron published since: `git log --oneline | grep auto:` and the GitHub Actions run history / open `autorun-failure` issues.

---

## 1. ⚠️ ACTIVE ISSUE — Anthropic credits (action may be pending)

The autonomous pipeline **stopped publishing on 7 July because the Anthropic API account ran out of credits** ("credit balance is too low", HTTP 400). This is a **billing matter, not a bug** — the code and key are fine.

- **G was topping up the balance** at the end of session 16. **Verify this is done.** If the balance is positive, the pipeline resumes automatically at the next cron; if failure issues are still appearing, the balance is still empty.
- The fast auth-check now reports this distinctly ("BALANCE EXHAUSTED — top up at console.anthropic.com") vs a bad key, in both CI and the runner (`_is_systemic_api_error` in `scripts/auto_run.py`). A mid-cycle exhaustion now aborts remaining beats instead of erroring on each.
- **Recommended (may still be open):** set a monthly spend limit + alert in the Anthropic console so it never silently runs dry again.

**Key economics fact (a common misconception):** GitHub Actions minutes and Anthropic API credits are *separate meters*. Running locally vs. in the cloud makes **zero** difference to Anthropic credit usage — the API calls are identical. Credit burn is driven by *events published × cost/event* (Sonnet reconcile + generate dominate). Cycles that publish nothing cost ~$0.

---

## 2. What changed this session (16)

Small session — mostly the credit diagnosis + two config/robustness tweaks:

1. **Cron slowed to every 12 hours** (`.github/workflows/autorun.yml`: `23 */12 * * *`, i.e. 00:23 & 12:23 UTC). This is a **pre-launch cost-control** measure per G. Raise back to `*/6` when live, or keep 12h. (Compute minutes are free on the public repo; this is purely to slow Anthropic credit burn.)
2. **Balance-vs-key diagnostics** (`43aab58`): the CI fast-check and the runner now distinguish "out of credits" (HTTP 400 credit balance) from "invalid key" (HTTP 401), so a future failure issue names the real cause.
3. **Cross-beat ID collision fix** landed just before this session (`3995bd5`, documented in handover 15 / Master Doc §15a) — event IDs are now `evt_<date>_<beat>_<NNN>`, globally unique. The live site shows all events distinctly, no duplicates.

---

## 3. Current live state

- **Events:** Middle East 18, Europe 2, Asia 5, Americas 0 (= 25). Counts grow each successful cron.
- **No duplicates / correct routing** after the ID fix.
- **Scheduler:** GitHub Actions only, every 12h. launchd disabled + plist removed — do not re-enable.
- **Schema v0.4;** B-16 (actor disputes) and B-17 (state-aligned outlets) both RESOLVED.

---

## 4. Open items / next work

| Item | Priority | Notes |
|---|---|---|
| **Confirm credits topped up** | **First thing** | Check open `autorun-failure` issues + latest cron run. If still failing on "BALANCE EXHAUSTED", the top-up hasn't landed. |
| **Semantic dedup + homepage story-grouping** | High | Background task `task_4517860d` was spawned in session 15 and runs in its own session. **Check whether it merged.** It adds embedding-based dedup (the URL-based novelty gate let 3 same-story "Khamenei funeral" events through) + collapses `related_events` into one homepage card. |
| Anthropic spend limit/alert | Medium | Set in console so the pipeline can't silently run dry again. |
| Cost tuning (optional) | Medium | If credit burn is still too high at 12h: `--max-events 1`, fewer beats, or switch reconcile+generate from Sonnet to Haiku (biggest single saving, some quality cost). |
| Americas beat empty | Low/expected | Nothing has cleared the gates yet; watch that Fox `topic_filter` isn't too narrow. |
| B-10 (`claim_ids` often empty) | Medium | Unchanged. |
| External validator feedback | Medium | Never received. |

---

## 5. Operating reference (unchanged from S15)

```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom && source .venv/bin/activate
python3 scripts/auto_run.py --beats israel_middle_east,europe,americas,asia   # manual cycle
python3 scripts/auto_run.py --dry-run --beats europe                          # no LLM, no publish
python3 -m pipeline.images.run --all-missing                                  # images
cd web && npm run dev                                                         # front end (G often has :3000 up)
```

- **CI:** Actions → autorun → Run workflow (or API). Failures open an issue with embedded diagnostics.
- **If the key rotates:** re-set the `ANTHROPIC_API_KEY` repo secret; the fast auth-check confirms in ~1 min.
- **Cron cadence:** edit the `cron:` line in `.github/workflows/autorun.yml` (needs a `workflow`-scoped PAT to push — G's credential has it).

---

## 6. Conventions (carry forward — see S15 §6 for the full list)

Beat-namespaced globally-unique event IDs (never revert). One scheduler (Actions). Image attribution is a license requirement. "Transparent," never "neutral." State-aligned outlets = perspective, not corroboration, always labeled. Bump `EVENT_SCHEMA_VERSION` + log for schema changes. Keep `data/autorun/state.json` consistent with committed events. Watch for stale `.git/index.lock`.
