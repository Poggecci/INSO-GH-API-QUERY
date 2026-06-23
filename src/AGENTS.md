# Source Code

## Purpose

- Contains all importable Python source code for the INSO Metrics project
- Entry points are CLI scripts that read config files, fetch GitHub data, calculate metrics, and write output
- Core engine: `generateTeamMetrics.py` orchestrates issue fetching, scoring, sprint tracking, and lecture topic task metrics

## Ownership

- All modules under `src/` are importable Python packages
- Entry-point scripts live directly in `src/` (e.g., `generateMilestoneMetricsForActions.py`, `exportMetricsForCourseMilestone.py`)
- Utility modules live in `src/utils/` — no CLI entry points there
- Output formatting lives in `src/io/` — no business logic there
- Deprecated V1 support lives in `src/legacy/`

## Local Contracts

- `generateMilestoneMetricsForActions.py` — primary entry point for GitHub Actions; reads v2.0 config, outputs Markdown reports
- `exportMetricsForCourseMilestone.py` — local professor run; reads v1.0 local config, outputs CSV files
- `exportMetricsForLectureTopicTasks.py` — standalone lecture topic task CSV exporter for local professor run
- `exportMetricsForDiscussionParticipation.py` — standalone discussion participation CSV exporter for local professor run
- `generateTeamMetrics.py` — core metrics engine; fetches issues via GraphQL, calculates scores, sprint completion, LTT metrics, and cycle/lead time per developer concurrently
- `getProject.py`, `getMilestones.py`, `getTeamMembers.py`, `getTeams.py` — GitHub GraphQL API fetchers
- `generateLectureTopicTaskMetrics.py` — wrapper that fetches processed issues and delegates to LTT metric calculation
- GraphQL queries are inline strings in the modules that use them
- All API calls go through `src/utils/queryRunner.py:runGraphqlQuery`
- `getTeamMetricsForMilestone` uses threading (`ThreadPoolExecutor`, `Queue`) to split the issue iterator for concurrent issue metrics and LTT metrics processing

## Work Guidance

- Follow the fetch → parse → filter → score → output pattern when adding new metrics
- Entry-point scripts parse config JSON, detect version, and dispatch to appropriate handlers
- Keep `scoring.md` in sync with scoring logic changes in `src/utils/issues.py`
- Keyword-only arguments for functions with many parameters
- Type hints throughout, dataclasses for models
- Max line length: 120 chars

## Verification

- Run `poetry run pytest` from the project root
- Tests mock `runGraphqlQuery` and `getProject` — no live API calls in tests
- See `test/AGENTS.md` for test conventions

## Child DOX Index

- `src/utils/AGENTS.md` — Utility layer: data models, parsing, scoring, discussions, date/time, GraphQL runner
- `src/io/AGENTS.md` — Output formatting: Markdown report writers
- `src/legacy/AGENTS.md` — Deprecated V1 config support
