# Cross-Region Viral Predictor — Design

Date: 2026-04-18
Status: P0 spec — approved, ready for implementation planning.

## 1. What we're building

A backend pipeline that takes **one short-form video from a Chinese SNS platform** (Douyin / Bilibili / Xiaohongshu) and tells a content creator:

1. **How well this video would fit TikTok-US** right now — a fit score, reasons it works, reasons it struggles, and which *trend patterns* currently viral in TikTok-US it matches.
2. **A concrete localization plan** — prioritized actions across language, captions, music, pacing, length, visuals, CTAs, and hashtags, plus a suggested new title + caption.

The intended user is a creator or studio in the source region deciding whether and how to localize for TikTok-US. The demo runs on bundled sample source videos against a bundled regional-insight corpus.

## 2. Pipeline at a glance

```
D (offline, one-time)      →   A (per source)        →   L (per source)     →   sort
regional-insight corpus         score against D           localization plan       by fit_score
JSON fixture                    Gemini call #1            Gemini call #2          trivial
```

- **D** — `samples/insights/us_tiktok.json`. An LLM-synthesized list of ~12 plausible currently-trending TikTok-US videos with rich per-video features. Today synthesized via one offline Gemini call; tomorrow produced by real-data ingestion. Same schema either way.
- **A (scorer)** — takes the source video bytes, its metadata, and the full D corpus; emits a `ScoringReport`.
- **L (localization planner)** — takes the source video bytes, its metadata, and A's `ScoringReport`; emits a `LocalizationPlan`. Deliberately does *not* re-read D — it rides on A's digested reasoning.
- **Sort** — `sorted(results, key=fit_score, desc)`. No LLM rerank in P0.

Gemini call budget for the hero demo: 3 sources × 2 calls = **6 calls**, sequential.

## 3. Module layout

```
src/trend_bridge/
  api_clients/
    gemini/
      client.py                 # existing — singleton genai.Client
      media.py                  # existing — MediaPart
      structured_output.py      # existing — GeminiStructuredOutputServiceService
      mock.py                   # CachingGeminiStructuredOutputServiceService (TB_MOCK)
      __init__.py               # existing exports + make_gemini_service() factory
  samples/
    insights/us_tiktok.json     # D: committed regional-insight corpus
    source_videos/              # bundled demo sources
      video_01.mp4 + video_01.json
      video_02.mp4 + video_02.json
      video_03.mp4 + video_03.json
    gemini_cache/               # TB_MOCK cache (populated by record mode)
  schemas.py                    # Pydantic: VideoMetadata, RegionalInsight,
                                # ScoringReport, LocalizationPlan, ...
  insight_builder.py            # offline: build samples/insights/us_tiktok.json
  scorer.py                     # A: score_video() -> ScoringReport
  localizer.py                  # L: plan_localization() -> LocalizationPlan
  renderer.py                   # Rich pretty-printer
  cli.py                        # arg-driven: `score`, `build-insight`
  demo.py                       # zero-arg: loops bundled sources
  __main__.py                   # python -m trend_bridge → cli
```

- One file per responsibility; small enough to hold in context at once.
- All Gemini calls route through `api_clients/gemini/`. Business logic never sees the mock flag.
- `samples/` ships inside the package because the demo depends on it at runtime. The name reflects that this is placeholder data today (swapped for real ingestion later), not pytest-style test fixtures.

## 4. Schemas (`schemas.py`)

Pydantic models. Those used as Gemini `response_schema` are marked.

```python
# --- Input: metadata JSON bundled with each source video ---
class VideoMetadata(BaseModel):
    title: str
    caption: str | None = None
    hashtags: list[str] = []
    source_platform: Literal["douyin", "bilibili", "xiaohongshu"]
    original_url: str | None = None

# --- D: regional-insight corpus (samples/insights/us_tiktok.json) ---
# Gemini response_schema for insight_builder.
class TrendingVideoSynth(BaseModel):
    title: str
    hook_style: str
    topic_category: str
    pacing: Literal["slow", "medium", "fast", "very_fast"]
    visual_signature: str
    audio_style: str
    language_register: Literal["casual", "slang", "formal", "meme"]
    length_sec: int
    emotional_tone: str
    format: Literal["talking-head", "tutorial", "skit", "pov", "list", "other"]
    creator_niche: str

class RegionalInsight(BaseModel):
    region: str               # "US"
    platform: str             # "TikTok"
    generated_at: str         # ISO timestamp
    videos: list[TrendingVideoSynth]  # target N=12

# --- A's output: Gemini response_schema for scorer. ---
class TrendPatternMatch(BaseModel):
    trend_pattern_name: str   # A coins/picks a name from the D corpus
    match_strength: int       # 0-100
    rationale: str            # 1-2 sentences

class CulturalFlag(BaseModel):
    severity: Literal["info", "caution", "blocker"]
    category: Literal["taboo", "language", "visual_norm", "format", "legal_ip"]
    message: str

class HookAnalysis(BaseModel):
    source_hook: str
    target_audience_fit: Literal["strong", "weak", "needs_rework"]
    suggested_target_hook: str

class ScoringReport(BaseModel):
    fit_score: int                          # 0-100
    confidence: Literal["low", "medium", "high"]
    one_line_verdict: str
    top_reasons_works: list[str]            # 2-3 bullets
    top_reasons_struggles: list[str]        # 2-3 bullets
    trend_pattern_matches: list[TrendPatternMatch]  # top 3
    cultural_flags: list[CulturalFlag]
    hook_analysis: HookAnalysis
    notes: str | None = None                # stub-report footer on failure

# --- L's output: Gemini response_schema for localizer. ---
class LocalizationAction(BaseModel):
    priority: Literal["must", "should", "nice"]
    area: Literal["language", "captions", "music", "pacing",
                  "length", "visuals", "cta", "hashtags"]
    action: str
    rationale: str

class LocalizationPlan(BaseModel):
    summary: str                        # 1-2 sentence remix pitch
    target_language: str                # "en-US"
    suggested_new_title: str
    suggested_new_caption: str
    suggested_hashtags: list[str]
    actions: list[LocalizationAction]   # prioritized
    estimated_effort: Literal["light", "moderate", "heavy"]
```

### Schema design notes

- `fit_score` and `match_strength` are ints, not floats — judge-readable, and Gemini emits them more stably.
- `Literal` enums where the option set is fixed — keeps Gemini from drifting and lets the renderer color-code by value.
- `trend_pattern_name` is free-form string, not enum — A coins pattern names inline from the D corpus (Approach 1). This is the key simplification vs. pre-extracting archetypes at build time.
- `CulturalFlag.severity="blocker"` is the demo's "do not ship this" signal; the renderer shows it as a red badge.
- `ScoringReport.notes` carries error context when a per-source run falls through to the stub report (see §6).
- Deliberately absent: per-archetype confidence beyond `match_strength`, multi-target output in one report, timestamps/owners on actions, any reranker schema.

## 5. Data flow

### Build-time — run once, commit output

```
python -m trend_bridge build-insight --region US --platform TikTok --n 12
  → insight_builder.py
      → GeminiStructuredOutputService.generate(schema=RegionalInsight, prompt=…)
  → writes samples/insights/us_tiktok.json
```

### Runtime — single source (`score`)

```
python -m trend_bridge score --source v.mp4 --metadata v.json --target us-tiktok

 1. cli.py loads:
      - MediaPart from v.mp4 (File API auto-upload if > 20 MB)
      - VideoMetadata from v.json
      - RegionalInsight from samples/insights/us_tiktok.json
 2. scorer.score_video(media, metadata, insight)
      → Gemini call #1, response_schema=ScoringReport
      → returns ScoringReport
 3. localizer.plan_localization(media, metadata, report)
      → Gemini call #2, response_schema=LocalizationPlan
      → prompt includes the full ScoringReport JSON (reuses A's reasoning)
      → returns LocalizationPlan
 4. renderer.render_pair(metadata, report, plan) → Rich panels to stdout
```

### Runtime — demo (`demo`)

```
python -m trend_bridge demo

 1. Discover samples/source_videos/*.mp4 (+ matching .json)
 2. Load samples/insights/us_tiktok.json once
 3. For each source (sequentially, NOT gathered):
       run the same score+localize pair
       collect (metadata, report, plan)
 4. Sort collected list by report.fit_score desc
 5. renderer.render_demo(sorted_triples) → header + one panel set per source,
    highest-scoring first, with rank badge
```

### What flows where

- `VideoMetadata` → both A and L.
- `RegionalInsight` → A only. L rides on A's digested reasoning.
- Raw video bytes → both A and L (both look at pixels).

## 6. Mock seam (`TB_MOCK`)

All Gemini clients constructed via one factory:

```python
# api_clients/gemini/__init__.py
def make_gemini_service() -> GeminiStructuredOutputService:
    mode = os.getenv("TB_MOCK", "off")  # off | record | replay
    if mode == "off":
        return GeminiStructuredOutputService()
    return CachingGeminiStructuredOutputService(mode=mode)
```

- **`TB_MOCK=off`** (default, demo) — real calls.
- **`TB_MOCK=record`** (dev loop) — on cache miss, real call + write `samples/gemini_cache/<hash>.json`; hit → return cached.
- **`TB_MOCK=replay`** (test/CI) — hit → return cached; **miss → raise**. No accidental billing.

**Cache key** = hash of `(model, system_prompt, user_prompt, schema_name, media_sha256_list)`.
Media hashed by file bytes so the key is stable across reruns of the same `.mp4`.

**Cache file** stores the parsed Pydantic output as JSON plus a sidecar `(model, schema_name, prompt_hash, prompt_excerpt)` for debuggability. No full-prompt persistence.

Out of scope: per-call bypass flags, TTLs, cache compaction. Real video File API uploads still happen in `record` mode; only the `generate()` response is cached.

## 7. Error handling

Per CLAUDE.md: errors must not crash the demo — log and fall through.

- **Per-source isolation in `demo`:** each source's A + L pair runs inside `try/except Exception`. On failure, emit a stub `ScoringReport` with `fit_score=0`, `one_line_verdict="(analysis failed)"`, and the exception message in `notes`. The loop continues.
- **Schema validation failures** bubble up from `GeminiStructuredOutputService.generate()` and are caught by the per-source guard.
- **Missing fixture files** (`samples/insights/us_tiktok.json`) hard-fail at startup with an actionable message. Not a runtime concern.
- **File API upload failures** on large videos → same per-source fall-through.
- **No retries, no backoff** in P0.

## 8. Testing

Hackathon-scaled. `pytest`, no CI.

- `tests/test_schemas.py` — Pydantic round-trip on sample JSON.
- `tests/test_scorer.py` / `test_localizer.py` — run with `TB_MOCK=replay` against committed cache; assert returned objects are non-trivial (`0 ≤ fit_score ≤ 100`, at least one action, etc.).
- `tests/test_demo_smoke.py` — invoke `demo` end-to-end with `TB_MOCK=replay`; assert exit code 0 and all 3 sources produced a non-stub report.

Not writing: prompt-quality tests, retry tests, renderer snapshot tests, golden-output tests.

## 9. Demo script

Stage command (the one the judge sees):

```
python -m trend_bridge demo
```

Expected output: a header panel, then three source panels ordered by fit_score desc. Each source panel contains:

- Source summary (title, platform, thumbnail not strictly required).
- `ScoringReport` card (score badge, verdict, works/struggles bullets, top trend-pattern matches, cultural flags, hook analysis).
- `LocalizationPlan` card (remix summary, new title/caption/hashtags, prioritized actions, effort badge).

`demo.py` internally calls the same `score` command path so `cat demo.py` reads as genuine arg-passing, not hardcoded inline logic.

## 10. Priorities

### P0 — this sprint (the demo)

Everything in §1–§9.

### P1 — next, after P0 ships

- **BytePlus Seedance video generation.** Use `LocalizationPlan` as input to generate a short remix preview or localized thumbnail. Dependency is already in `requirements.txt`; no calls in P0.
- **Concurrency.** `asyncio.gather` across sources in the demo loop. A and L per source stay sequential (L depends on A). Cuts demo runtime ~3×.

### P2 — if time remains after P1

- **FastAPI + thin web UI.** Video upload + report cards on a page. Backend reuses `scorer` + `localizer` modules directly. No auth.

### Not in this project (explicit non-goals)

- LLM reranker (the "B" step).
- Multi-target scoring / cross-platform heat-map.
- Real trending-data ingestion — scrapers, platform APIs, public datasets.
- URL fetch for source videos. `original_url` is stored, not fetched.
- Multi-language source (JP/KR) or reverse direction (US → CN).
- Retries, backoff, rate-limit handling.
- Persistence (DB, SQLite, run history, user accounts).
- Evaluation / ground-truth dataset.
- Sensitive-category content — bundled samples stay clean lifestyle / food / fitness, ≤60 s.

## Appendix — decisions already closed

- **Source → target pair:** CN (Douyin / Bilibili / Xiaohongshu) → US (TikTok). One pair only.
- **Source input shape:** local `.mp4` + sidecar JSON (`VideoMetadata`). No URL fetching in P0.
- **D contents:** raw synthetic corpus (Approach 1) — no pre-extracted archetypes at build time.
- **Scoring output:** two-stage, separate Gemini calls for scoring (A) and localization (L). L receives A's full `ScoringReport` as prompt context.
- **Reranking:** trivial sort by `fit_score`. No LLM rerank in P0.
- **Number of bundled source videos:** 3.
- **Demo command:** zero-arg `python -m trend_bridge demo`; internally dispatches the arg-driven `score` command.
