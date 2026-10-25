# Findings & Decisions

## Requirements
- Continue BMS development under `bms-spec-harness`.
- Use imported owner-blog posts in `data/bms.sqlite3` as pre-publish analysis context.
- Connect existing post DB to three outcomes: pre-publish analysis, internal link candidates, and keyword/topic overlap detection.
- Keep `core/` independent from `webapp` and `bot`.
- Treat scores as BMS internal proxy scores, never official Naver scores.
- Avoid keyword-stuffing, competitor-copying, or spammy SEO guidance.
- Update `docs/development/` before or alongside the implementation.
- Run relevant tests before finalizing.

## Research Findings
- `docs/development/implementation-roadmap.md` records Phase 2.5 as complete with `my_posts` enabled=618 and body text stored for all enabled rows.
- The current assistant spec says imported body text should be used for duplicate topic detection, internal links, old-post checks, and post-publish feedback.
- Existing Phase 3 content analysis already accepts `reference_posts` for SERP title/summary signals and returns `serp_missing_topic_candidates`.
- Current planning files were for Phase 2.5 and have been replaced with Phase 3.5 owner-post analysis context planning.
- `core/content_analyzer.py` is already pure and dataclass-based, so owner post context can be added as another request field.
- `webapp/main.py` currently builds the `ContentAnalysisRequest` directly from JSON payload and can attach store-derived owner post context.
- `core/storage.py` returns full `my_posts` records through `my_post_summaries()`, but a narrower context method is better for analysis payload size and coupling.
- The static UI already renders optional analysis sections, so adding two result blocks is low-risk.

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| Add this as Phase 3.5 before post-publish feedback | The imported post DB is now ready and can immediately improve the pre-publish coach before Phase 4 rank feedback. |
| Use owner posts as private context, not public benchmark data | This preserves the product focus on one private operator and avoids competitor-copying incentives. |
| Extend existing `/api/content-analysis` instead of adding a separate endpoint | The new data is part of the same pre-publish decision and avoids another UI round trip. |
| Add a narrow storage method for analysis context | Keeps UI list payloads and analyzer inputs explicit, and avoids passing unrelated rank summary data. |
| Return both link candidates and overlap warnings from the analyzer | They serve different user decisions: what to connect versus what to differentiate. |
| Treat wishlist posts as `목록형` | Wishlist content is usually a curated candidate list, so comparison/ranking gaps create noisy feedback. |
| Move keyword detail under the rank search card | Top-blog results should appear in direct response to the search action, before watch/news sections. |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| Worktree already contains prior uncommitted Phase 2/2.5 changes | Left unrelated existing changes intact and edited only the Phase 3.5 behavior/docs needed for this task. |

## Resources
- `AGENTS.md`
- `docs/development/README.md`
- `docs/development/naver-blog-assistant-spec.md`
- `docs/development/implementation-roadmap.md`
- `progress.md`
- `core/content_analyzer.py`
- `core/storage.py`
- `webapp/main.py`
- `webapp/static/app.js`
- `tests/test_content_analyzer.py`
- `tests/test_storage.py`
- `tests/test_webapp.py`
