# Output Formatting

## Purpose

- Holds Markdown report writers for the GitHub Actions metrics output
- No business logic — receives computed `MilestoneData` and writes formatted Markdown tables

## Ownership

- `markdown.py` — all Markdown output functions
- `charts.py` — interactive HTML chart generator for cycle/lead time graphs using Chart.js

## Local Contracts

- `writeMilestoneToMarkdown` — writes the main milestone data table (overwrites file)
- `writeSprintTaskCompletionToMarkdown` — appends sprint task completion table with date ranges
- `writeWeeklyDiscussionParticipationToMarkdown` — appends discussion participation table with penalties
- `writePointPercentByLabelToMarkdown` — appends per-label point percentage table
- `writeLogsToMarkdown` — appends log messages table from log file
- All functions except `writeMilestoneToMarkdown` append to the file (`mode="a"`)
- Output filename pattern: `{StrippedMilestoneName}-{Team}-{Organization}.md`

## Work Guidance

- Keep formatting changes minimal and consistent with existing Markdown table style
- No scoring or filtering logic belongs here — all data must be pre-computed by the caller

## Verification

- No dedicated tests for `src/io/` — output is validated through integration tests in `test/test_generateTeamMetrics.py`
- Run `poetry run pytest` to verify the full pipeline

## Child DOX Index

No child DOX files.
