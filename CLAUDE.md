# Trend Bridge

Python monolith. Backend only (frontend may come later in `frontend/`).

**Status: hackathon sprint, ~3h left.** Target demo = cross-region viral-content prediction/generation. Ship > polish.

## Structure

- `src/trend_bridge/` — application code
- `src/trend_bridge/api_clients/` — thin wrappers around external APIs (Vertex AI / Gemini, BytePlus Seedance)
- `tests/` — pytest tests
- `docs/plans/<feature>/` — planning + running notes per feature
- `.worktrees/` — git worktrees for isolated feature work

## Setup

```bash
./init.sh
```

## Conventions

- Imports: `from trend_bridge import ...` (editable install via `pip install -e .`)
- Deps: `requirements.txt`
- Tests: `pytest`
- Worktrees: use `.worktrees/` directory

## Hackathon mode

We have ~3 hours. Optimise for the end-to-end demo, not for production.

### Mock aggressively — real data is optional

Any of these are fine to stub with canned data and wire up for real later:

- **Trending-content ingestion** — a JSON fixture of sample posts per region beats a live scraper. One file per region, ~5 items each.
- **BytePlus Seedance 2.0 video gen** — cache one generated `.mp4` per scripted scenario, serve from disk. The API is slow and costs real money; don't call it in inner loops.
- **Gemini structured output inside tight loops** — snapshot one real response per prompt shape, replay by prompt hash during dev. Keep one "real" call in the demo path so the judges see it work.
- **Cross-region translation / cultural adaptation** — hardcode 1–2 language pairs. Don't build a generic pipeline.

Keep a clean seam. Each external call lives behind a function or class in `api_clients/`; swap real ↔ mock via an env var (`TB_MOCK=1`) or a constructor arg. Don't sprinkle `if mock:` through business logic — the call site shouldn't know.

Put fixtures under `tests/fixtures/` (reusable in tests) or `src/trend_bridge/fixtures/` (shipped with the app). Whichever makes the call site simpler.

### Favour boring, fast choices

- Single process. No queues, workers, or background jobs. If you need concurrency, `asyncio.gather`.
- JSON files or SQLite before reaching for a real DB.
- CLI entry points before a web server. Add a server only when there's a UI that needs one.
- Hardcoded config is fine. Promote to env vars only when a second teammate needs to run it.
- Three similar lines beats an abstraction. Refactor only if the demo lives past tomorrow.

### Decisions and discussion

- Running notes live in `docs/plans/<feature>/NOTES.md` — who's doing what, trade-offs, TODOs. Keeps us off chat scrollback.
- Reversible choices: just make them and move on.
- Stop to discuss only the irreversible ones: data schemas, external API contracts, the demo-script shape.
- When you're blocked on a teammate, stub their interface with the dumbest possible fake and keep moving.

### Definition of "done" for the demo

- Runs end-to-end from a single command.
- Happy path works for the scripted demo scenario.
- Errors don't crash the run — log and fall through to a fallback.
- Everything else (retries, polish, coverage, types) is out of scope.
