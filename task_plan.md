# Task Plan: Phase 3.5 Owner Post Analysis Context

## Goal
Connect imported owner-blog post bodies to pre-publish analysis so BMS can suggest internal links and detect keyword/topic overlap before publishing.

## Current Phase
Complete

## Phases

### Phase 1: Requirements & Discovery
- [x] Read BMS harness docs and relevant development specs
- [x] Read prior progress, roadmap, and current assistant spec
- [x] Inspect current analyzer, storage, API, static UI, and tests
- [x] Document findings in findings.md
- **Status:** complete

### Phase 2: Spec Update
- [x] Add Phase 3.5 intent, acceptance criteria, API/UI/data behavior, and validation plan to development docs before code edits
- **Status:** complete

### Phase 3: Implementation
- [x] Add owner post context analysis in `core/`
- [x] Expose imported post context through storage/API without coupling `core/` to `webapp/`
- [x] Attach owner post context to `POST /api/content-analysis`
- [x] Render internal link and overlap results in the pre-publish UI
- [x] Add focused unit/API/UI tests
- **Status:** complete

### Phase 4: Testing & Verification
- [x] Run focused analyzer/storage/webapp tests
- [x] Run full `source venv/bin/activate && python -m pytest` if shared behavior changes
- [x] Fix any failures and log results
- **Status:** complete

### Phase 5: Delivery
- [x] Reconcile docs with actual implementation
- [x] Update progress.md and findings.md
- [x] Summarize changed files and verification
- **Status:** complete

## Key Questions
1. Should imported owner posts be passed into the existing content analyzer or analyzed through a separate endpoint?
2. Which owner-post fields are sufficient for safe suggestions: title, URL, category, summary, published date, target keywords, and stored body text?
3. How should overlap detection avoid encouraging keyword stuffing or duplicate content?

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| Keep owner-post analysis inside `core/` and make API/UI thin | Matches BMS layering rule and makes behavior testable. |
| Treat imported owner posts as private context only | The feature should help internal linking and topic planning, not competitor copying. |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
