# STAGE 0 — Golden Dataset (Milestone 0)

> **Do this before any pipeline code.** This stage produces the fixture that every later stage is built and tested against. It is the cheapest way to de-risk the whole project.

**Prerequisite reading:** `00_MASTER_DOCUMENT.md`.
**Milestone:** M0.
**Phase:** Setup.

## Goal

Hand-assemble a small, high-quality dataset of real coverage for **one** news event in the primary beat (Israel / Middle East), so the pipeline can be developed against stable, well-understood data instead of a live feed.

## Definition of done

- One event chosen, with a one-line description and date.
- 8–12 articles covering that event, collected from outlets spanning the spectrum (not all from one side).
- Each article saved with the metadata below.
- Beat configuration files stubbed for both beats (primary + secondary).
- Everything committed to the repo under `data/golden/`.

## Steps

1. **Pick the event.** Choose one concrete, recently well-covered event in the primary beat. Good criteria: covered by many outlets; visibly framed differently across the spectrum; factually bounded (a specific incident, ruling, or announcement, not a sprawling ongoing topic).

2. **Choose sources across the spectrum.** Aim for a spread: outlets generally rated left, center, and right, plus at least one or two non-Western or regional outlets if relevant to the beat. Record each outlet's bias rating *and the source of that rating* (AllSides / Ground News / Media Bias Fact Check). Do not invent ratings.

3. **Collect 8–12 articles.** For each article, save:
   - `outlet` (name)
   - `url`
   - `author` (if available)
   - `published_at`
   - `title`
   - `body_text` (full text — for internal dev use only; see copyright note)
   - `bias_rating` and `bias_rating_source`
   - `collected_at`

4. **Store as structured files.** Suggested layout:
   ```
   data/golden/
     event_001/
       meta.json          # event description, date, list of article ids
       articles/
         art_001.json     # one file per article, fields as above
         art_002.json
         ...
   ```

5. **Stub the beat configs** (full format defined in `STAGE_1_INGEST.md`):
   ```
   config/beats/
     israel_middle_east.json
     world_news.json
   ```
   For M0 these can contain just the beat name and a placeholder source list; they get filled in at M1.

## Copyright note (important)

Full article text is stored **only** as a local development fixture, never served to end users and never redistributed. The production system links out and works from facts, not reproduced expression (see Master Doc §7). Keep `data/golden/` out of any public artifact and add it to `.gitignore` if the repo will be public.

## Handoff

When done, update the TRACKSHEET: mark M0 done, note the chosen event and article count in the change log, then proceed to `STAGE_1_INGEST.md`.
