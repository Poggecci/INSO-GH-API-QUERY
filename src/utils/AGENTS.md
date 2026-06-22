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

## Local Contracts

- `runGraphqlQuery` is the sole API entry point — all GraphQL calls must route through it
- `parseIssue` raises `ParsingError` on missing/empty content; `KeyError`/`ValueError` on structural problems
- Issue scoring formula: `Score = (Difficulty * Urgency * Decay) + Modifier` with optional 10% documentation bonus via 🎉 reaction
- `decay()` returns 1.0 at milestone start and ~0.3 at milestone end; uses exponential decay
- `shouldCountIssue` filters by milestone match, closure by manager, urgency/difficulty population, and open-issue flag
- `whoShouldGetBonus` returns `None` if multiple valid 🎉 reactions exist (penalizes ambiguity)
- `applyIssuePreProcessingHooks` uses `exec()` — hooks must come from trusted sources only
- `calculateWeeklyDiscussionPenalties` applies 2 points per missed week plus escalating consecutive-miss penalties, capped at 100
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
