# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A **content and analysis repository**, not a software project. It holds transcripts of
*KAOS* (Netflix 2024, Charlie Covell) Season 1 and a prose series bible derived from them.
The long-term goal is a **novelization of a non-existent Season 2** that resolves Season 1's
open plot threads.

There is no build, no test suite, no linter, and one Python script. Most work here is
reading transcripts and writing Markdown.

## Commands

```bash
# Re-download and regenerate all transcript formats (only script in the repo)
.venv/bin/python download_transcripts.py
```

The `.venv` (gitignored) has `requests` and `beautifulsoup4`. Recreate with
`python -m venv .venv && .venv/bin/pip install requests beautifulsoup4`.

## Critical: transcripts are gitignored

`.gitignore` excludes `transcripts/` entirely, even though `README.md` documents its
structure in detail. **A fresh clone has no transcripts** — run the downloader first.
Do not assume the files described in the README are present; check before reading.

## How the transcript pipeline works

`download_transcripts.py` scrapes one hardcoded subtitlecat URL per episode (1–8), then
derives three formats from each SRT:

| Directory | Content | Use it for |
|---|---|---|
| `transcripts/srt/` | Raw subtitles with timecodes | Getting a timestamp for a specific line |
| `transcripts/txt/` | Dialogue only, consecutive duplicates dropped | **Default for reading and analysis** — smallest, and `grep -n` line numbers make good citations |
| `transcripts/md/` | Formatted: bracketed sound cues italicized, dash-prefixed lines split into bullets | Human reading |

Plus `transcripts/KAOS_Season_1_Complete.txt`, all eight episodes concatenated.

Failure behavior matters: a failed fetch or a missing SRT link **prints an error and
continues to the next episode**. The season-complete file is then silently short an
episode. After any run, verify all eight files exist in each format.

The whole season is ~190KB of text (~50k tokens) — small enough to read in full rather
than sampling.

## The `bible/` directory

Thirteen cross-linked Markdown files, `00-OVERVIEW.md` through `12-S2-OUTLINE.md`.
`00-OVERVIEW.md` is the index; `05-MYSTERIES.md` is the load-bearing file (open/resolved
threads, each with resolution constraints for Season 2). Files `00`–`10` are written from
the transcripts. **`11-S2-CANON.md` and `12-S2-OUTLINE.md` are invention, not evidence** —
decisions and structure for the novelization itself (drafted as forty chapters in
`drafts/`); never cite them as show canon.

Conventions to preserve when editing:

- **Claims the show states outright are stated plainly; anything drawn from implication is
  marked `**(inference)**`.** This distinction is the point of the document — do not blur it.
- Attribute facts to a specific episode. Verify attributions with
  `grep -ln "<phrase>" transcripts/txt/*.txt` rather than from memory; several phrases recur
  across episodes in different mouths, and the first hit is often not the significant one.
- Summarize in your own words. Quote only short signature lines — the two prophecy couplets,
  liturgical phrases like "Vero". Never reproduce song lyrics; the transcripts are full of them.
- Cross-link files with relative Markdown links (`[05-MYSTERIES.md](05-MYSTERIES.md)`).
- `05-MYSTERIES.md` entries use stable IDs (`R1`, `P1`, `O1`…) that other files may reference.
