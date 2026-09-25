# Utility Layer

## Purpose

- Holds data models, parsing functions, scoring logic, discussions processing, date/time utilities, and the GraphQL query runner
- No CLI entry points — these modules are imported by `src/` entry points and each other

## Ownership

- `models.py` — all dataclasses (`Issue`, `Milestone`, `Project`, `Discussion`, `DeveloperMetrics`, `MilestoneData`, `LectureTopicTaskData`, `IssueMetrics`, `Reaction`, `IssueComment`, `Category`, `DiscussionComment`, `ParsingError`, `ReactionKind`)
- `issues.py` — issue parsing, scoring, decay, bonus calculation, pre-processing hooks
- `discussions.py` — discussion parsing, weekly participation tracking, penalty calculation
- `queryRunner.py` — single GraphQL API endpoint runner
- `parseDateTime.py` — ISO datetime parsing with timezone and time defaults
- `constants.py` — timezone (`pr_tz`), default times, token retrieval
- `milestones.py`, `project.py` — GraphQL response parsers for milestones and projects
- `autoExtractMilestone.py` — milestone auto-selection based on current date
- `dataStore.py` — persistent local issue store: JSON cache of fetched project items

## Local Contracts

- `runGraphqlQuery` is the sole API entry point — all GraphQL calls must route through it
- `parseIssue` raises `ParsingError` on missing/empty content; `KeyError`/`ValueError` on structural problems
- Issue scoring formula: `Score = (Difficulty * Urgency * Decay) + Modifier` with optional 10% documentation bonus via 🎉 reaction
- `decay()` returns 1.0 at milestone start and ~0.3 at milestone end; uses exponential decay
- `shouldCountIssue` filters by milestone match, closure by manager, urgency/difficulty population, and open-issue flag
- `whoShouldGetBonus` returns `None` if multiple valid 🎉 reactions exist (penalizes ambiguity)
- `applyIssuePreProcessingHooks` uses `exec()` — hooks must come from trusted sources only
- `calculateWeeklyDiscussionPenalties` applies 2 points per missed week plus escalating consecutive-miss penalties, capped at 100
- `dataStore.py` — persistent local issue store used when config provides a `dataStore` path:
  - Store is a JSON file keyed by issue URL; deleting or renaming the file forces a complete reload
  - Fetched items are merged into the store; issues that dropped off the project board are retained from the store
  - If live fetching fails and a store exists, stored data is used as a fallback
  - Store format version is checked; incompatible or corrupt stores are replaced with a fresh one
  - **Design decision (2026-09-25): full board scan on every fetch — no incremental fetch.** Projects v2 field edits (Urgency, Difficulty, Modifier) do NOT update the underlying issue's `updatedAt`: the GraphQL `IssueTimelineItemsItemType` enum has no field-value-changed event (only ADDED_TO_PROJECT_V2_EVENT, PROJECT_V2_ITEM_STATUS_CHANGED_EVENT, REMOVED_FROM_PROJECT_V2_EVENT), so a REST search on `updated:>=` would silently miss score-field changes. Verified empirically impossible to test on live archived data (mutations off-limits) and settled via schema introspection. Revisit only if GitHub adds field-change events to issue timelines.
- `get_milestone_start` defaults to 08:00, `get_milestone_end` defaults to 20:00 in `America/Puerto_Rico` timezone

## Work Guidance

- Dataclasses use `kw_only=True` for non-trivial models; simple ones use defaults
- `ReactionKind` is a `StrEnum` — extend if new reaction types are needed
- Parsing functions validate input dicts and raise `ParsingError` for missing/empty data
- Keep scoring logic changes reflected in `scoring.md`

## Verification

- `test/utils/test_issues.py` — tests for `shouldCountIssue`, `decay`, `calculateIssueScores`, `applyIssuePreProcessingHooks`
- `test/utils/test_discussions.py` — tests for `parseDiscussion`, `getWeekIndex`, `findWeeklyDiscussionParticipation`, `calculateWeeklyDiscussionPenalties`
- `test/utils/test_autoExtractMilestone.py` — tests for `auto_extract_milestone`
- Run `poetry run pytest test/utils/` to run utility tests only

## Child DOX Index

No child DOX files.
