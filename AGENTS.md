# DOX framework

- DOX is highly performant AGENTS.md hierarchy installed here
- Agent must follow DOX instructions across any edits

## Core Contract

- AGENTS.md files are binding work contracts for their subtrees
- Work products, source materials, instructions, records, assets, and durable docs must stay understandable from the nearest applicable AGENTS.md plus every parent AGENTS.md above it

## Purpose

- INSO Metrics generates individual and team contribution metrics for UPRM Software Engineering course projects hosted on GitHub
- Fetches issues, milestones, discussions, and project board data via the GitHub GraphQL API
- Calculates developer scores based on issue difficulty, urgency, decay, bonuses, sprint completion, and lecture topic tasks
- Outputs results as CSV files (local run) or Markdown reports (GitHub Actions)

## Ownership

- Repository: `github.com/Poggecci/INSO-GH-API-QUERY`
- Language: Python 3.11+, managed with Poetry
- Config format: JSON (v1.0 deprecated, v2.0 current for Actions; separate format for local professor run)
- GitHub PAT requires `read:org` and `read:project` scopes
- All times default to `America/Puerto_Rico` timezone (`pr_tz`)

## Local Contracts

- `src/` contains all importable source code; entry points are scripts under `src/` (e.g., `generateMilestoneMetricsForActions.py`)
- `src/utils/` holds data models, parsing, scoring logic, and API query runners — no CLI entry points here
- `src/io/` holds output formatting only — no business logic
- `src/legacy/` holds deprecated V1 config support — do not extend, only maintain compatibility
- `test/` mirrors `src/` structure; tests use pytest with `unittest.mock` for GraphQL responses
- Config JSON schemas differ between Actions (v2.0: `projectName`, `milestones` dict) and local professor run (`organization`, `teams` dict)
- `GITHUB_API_TOKEN` environment variable is required for all API calls
- `ORGANIZATION` environment variable is required for GitHub Actions runs
- Issue scoring formula: `Score = (Difficulty * Urgency * Decay) + Modifier` with optional 10% documentation bonus
- Sprint failure (fewer than `minTasksPerSprint` in any sprint) results in individual grade of 0
- `scoring.md` documents the grading rules for students — keep it in sync with code changes

## Read Before Editing

1. Read the root AGENTS.md
2. Identify every file or folder you expect to touch
3. Walk from the repository root to each target path
4. Read every AGENTS.md found along each route
5. If a parent AGENTS.md lists a child AGENTS.md whose scope contains the path, read that child and continue from there
6. Use the nearest AGENTS.md as the local contract and parent docs for repo-wide rules
7. If docs conflict, the closer doc controls local work details, but no child doc may weaken DOX

Do not rely on memory. Re-read the applicable DOX chain in the current session before editing.

## Update After Editing

Every meaningful change requires a DOX pass before the task is done.

Update the closest owning AGENTS.md when a change affects:

- purpose, scope, ownership, or responsibilities
- durable structure, contracts, workflows, or operating rules
- required inputs, outputs, permissions, constraints, side effects, or artifacts
- user preferences about behavior, communication, process, organization, or quality
- AGENTS.md creation, deletion, move, rename, or index contents

Update parent docs when parent-level structure, ownership, workflow, or child index changes. Update child docs when parent changes alter local rules. Remove stale or contradictory text immediately. Small edits that do not change behavior or contracts may leave docs unchanged, but the DOX pass still must happen.

## Hierarchy

- Root AGENTS.md is the DOX rail: project-wide instructions, global preferences, durable workflow rules, and the top-level Child DOX Index
- Child AGENTS.md files own domain-specific instructions and their own Child DOX Index
- Each parent explains what its direct children cover and what stays owned by the parent
- The closer a doc is to the work, the more specific and practical it must be

## Child Doc Shape

- Create a child AGENTS.md when a folder becomes a durable boundary with its own purpose, rules, responsibilities, workflow, materials, or quality standards
- Work Guidance must reflect the current standards of the project or user instructions; if there are no specific standards or instructions yet, leave it empty
- Verification must reflect an existing check; if no verification framework exists yet, leave it empty and update it when one exists

Default section order:
- Purpose
- Ownership
- Local Contracts
- Work Guidance
- Verification
- Child DOX Index

## Style

- Keep docs concise, current, and operational
- Document stable contracts, not diary entries
- Put broad rules in parent docs and concrete details in child docs
- Prefer direct bullets with explicit names
- Do not duplicate rules across many files unless each scope needs a local version
- Delete stale notes instead of explaining history
- Trim obvious statements, repeated rules, misplaced detail, and warnings for risks that no longer exist

## Closeout

1. Re-check changed paths against the DOX chain
2. Update nearest owning docs and any affected parents or children
3. Refresh every affected Child DOX Index
4. Remove stale or contradictory text
5. Run existing verification when relevant
6. Report any docs intentionally left unchanged and why

## Work Guidance

- Follow existing code style: keyword-only arguments for functions with many params, dataclasses for models, type hints throughout
- Max line length: 120 chars (`.flake8`)
- Type checking: `basic` mode (`.vscode/settings.json`), mypy with tests excluded
- GraphQL queries are inline strings in the modules that use them
- All API calls go through `src/utils/queryRunner.py:runGraphqlQuery`
- When adding new metrics, follow the pattern: fetch → parse → filter → score → output
- Keep `scoring.md` in sync with scoring logic changes in `src/utils/issues.py`

## Verification

- Run `poetry run pytest` from the project root
- CI runs pytest on Python 3.11 across ubuntu-22.04, macos-latest, windows-latest (see `.github/workflows/ci.yml`)
- Tests mock `runGraphqlQuery` and `getProject` — no live API calls in tests

## User Preferences

When the user requests a durable behavior change, record it here or in the relevant child AGENTS.md

## Child DOX Index

- `src/AGENTS.md` — Source code: entry points, GitHub API fetchers, metrics calculation engine
- `src/utils/AGENTS.md` — Utility layer: data models, parsing, scoring, discussions, date/time, GraphQL runner
- `src/io/AGENTS.md` — Output formatting: Markdown report writers
- `src/legacy/AGENTS.md` — Deprecated V1 config support
- `test/AGENTS.md` — Test suite: pytest conventions and mock patterns
- `.github/workflows/AGENTS.md` — CI pipeline and daily metrics generation workflow
