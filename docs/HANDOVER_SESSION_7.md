# HANDOVER — Session 7
## News Synthesis & Credibility Engine
**Handover date:** 1 June 2026
**Prepared by:** Claude (Cowork), Session 6
**For:** Claude (Cowork), Session 7
**Owner:** G (GitHub: Ephemiral)

---

## 1. Current status

| Milestone | Status | Notes |
|-----------|--------|-------|
| M0–M5 | ✅ Done | Golden dataset, ingest, cluster, analyze, annotate, Phase-1 page |
| M6 — Validate Phase 1 | 🔄 In progress | Internal audit done; external validation pending |
| M7 — Generate | ✅ Done | |
| M8 — Toggle UI | ✅ Done | |
| M9 — Validate Phase 2 | 🔄 **In progress** | Scale test done (3 events); external validation next |

**Live event pages** (run `cd web && npm run dev` → http://localhost:3000):
- `/event/evt_2026_05_31_001` — golden event (Netanyahu 70% Gaza)
- `/event/evt_2026_06_01_009` — scale test event 1 (24 articles, full spectrum)
- `/event/evt_2026_06_01_068` — scale test event 2 (6 articles)
- `/event/evt_2026_06_01_065` — scale test event 3 (4 articles, high contrast)

---

## 2. What changed this session

### Ingest — concurrent body fetching (`pipeline/ingest/rss.py`)
Sequential article fetching (1s global delay × N articles ≈ 10+ min) replaced with `ThreadPoolExecutor`:
- Phase 1: parse all RSS feeds sequentially (fast)
- Phase 2: fetch article bodies concurrently, up to 8 simultaneous connections
- Per-domain rate limiting: each outlet still gets ≤1 request/second, but all outlets run in parallel
- Result: ~10× speed improvement (~1 min for 400 articles)

### Ingest — RSS source fixes (`pipeline/ingest/rss.py`, `config/beats/israel_middle_east.json`)
Previously 5 of 10 sources produced 0 articles. Fixed:
- **User-Agent**: browser UA added to all `feedparser.parse()` calls — fixes UA-blocking (Al Jazeera, others)
- **topic_filter**: per-source keyword list; broad feeds (Euronews, Al Jazeera) only pass matching articles
- **rss_fallback**: secondary URL tried if primary returns empty
- **Jerusalem Post**: old URL redirected to HTML; fixed to `rssfeedsisraelnews.aspx`
- **Reuters**: deprecated RSS replaced with Google News RSS proxy
- **i24 News**: SPA with no RSS replaced with Google News RSS proxy
- **Haaretz**: URL updated + Google News fallback

Al Jazeera is still producing 0 articles despite the UA fix. Likely bot detection on their CDN — run the diagnostic command from Session 6 to confirm, then switch to Google News proxy if needed.

### Cluster — threshold + time-window (`pipeline/cluster/group.py`, `cluster/run.py`)
- `DEFAULT_THRESHOLD` raised 0.50 → 0.70 — requires specific event language, not just beat vocabulary
- `DEFAULT_TIME_WINDOW_HOURS = 48` — articles >48h apart cannot cluster together
- `pub_dates` wired through from `run.py` and `scale_test.py`
- `--time-window N` arg added to `cluster/run.py` (0 = disable)
- Result: broke 367-article mega-cluster into coherent same-day event clusters

### Generate — prompt + validation fix (`pipeline/generate/generate.py`)
- Prompt now explicitly states: `clm_XXX` → `claim_ids`; `src_XXX` → `source_ids`
- `validate_report()` auto-corrects transposed IDs instead of hard-aborting
- `evt_009` first run failed (`[ERROR] p9: unknown source_id 'clm_011'`); rerun with `--force-generate` succeeded

### Scale test — 3 events processed
`scripts/scale_test.py --run-events evt_009,evt_068,evt_065` ran successfully. All 3 events have analyzed JSON + report + provenance cards. Front end renders all three cleanly.

---

## 3. What's next (M9 completion)

### Step 1: Al Jazeera diagnostic
Run locally to understand why it still produces 0 articles:
```bash
cd /Users/gidon/Documents/Claude/Projects/Newsroom
source .venv/bin/activate
python3 - << 'EOF'
import feedparser, urllib.request
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
feed = feedparser.parse("https://www.aljazeera.com/xml/rss/all.xml", agent=UA)
print(f"Status: {feed.get('status','n/a')}  Entries: {len(feed.entries)}  Bozo: {feed.bozo}")
if feed.bozo: print(f"Reason: {feed.bozo_exception}")
req = urllib.request.Request("https://www.aljazeera.com/xml/rss/all.xml", headers={"User-Agent": UA, "Accept-Encoding": "identity"})
with urllib.request.urlopen(req, timeout=10) as r:
    print(f"Raw status: {r.status}  First 300 bytes: {r.read(300)}")
EOF
```
If it shows a bot challenge or empty feed, switch Al Jazeera to Google News proxy (same pattern as Reuters/i24).

### Step 2: External validation (M9 definition of done)
Three-profile test — pro-Palestinian / pro-Israel / centrist — on the Phase-2 report:
- Does the narrative feel balanced given the source mix?
- Are contested paragraphs presented fairly?
- Did expanding sources change how you read any paragraph?
- Is context (Hezbollah/Lebanon, Hamas-run health ministry attribution) sufficient?

Use evt_2026_06_01_009 as the primary test event — it has the best outlet diversity and a 24-article cluster that exercises the full pipeline.

### Step 3: More scale test events (optional)
If external validators raise issues about a specific topic or framing, run more events:
```bash
python3 scripts/scale_test.py --discover --beat israel_middle_east
# pick 2-3 more events from the list
python3 scripts/scale_test.py --run-events evt_X,evt_Y
```

---

## 4. Known issues / backlog

| ID | Issue | Priority |
|----|-------|----------|
| Al Jazeera | Still producing 0 articles despite UA fix | High — it's the primary left source |
| B-03 | Rationale text mentions outlet not in source list (warning only) | Low |
| B-05 | Extract stated rationale for policy decisions | Low |
| B-06 | Parallel framing in contested claims | Already in reconcile prompt |
| B-07 | clm_024 misclassification | Resolved by B-01 enforcement |

Full backlog in `docs/00_MASTER_DOCUMENT.md §13`.

---

## 5. Working conventions

1. **Sandbox can't call Anthropic API.** Write pipeline code here; G runs locally.
2. **Tracksheet first and last.** Upload to Drive after updating. Parent folder ID: `1idpUalHp1ixZEf59JL5rGmFWVt5p_eOX`.
3. **Schema v0.2 is current.** Bump + log if structure changes.
4. **Ask before** heavy new dependencies, structural repo changes, fixed decisions (§8).
5. **Golden dataset** is the regression fixture — test pipeline changes against it before live runs.
6. **UI design decisions** in `docs/00_MASTER_DOCUMENT.md §12`.
