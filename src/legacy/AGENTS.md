# Deprecated V1 Config Support

## Purpose

- Maintains backward compatibility with the deprecated V1 config format
- V1 configs use `projectName`, `milestoneName`, `milestoneStartDate`, `milestoneEndDate` fields
- New projects should use V2 config — this module should not be extended

## Ownership

- `generateMilestoneMetricsForActions.py` — V1 config handler, logs deprecation warning

## Local Contracts

- Organization is hardcoded to `uprm-inso4116-2024-2025-S1` in V1 handler
- V1 always uses `sprints=1` and `minTasksPerSprint=0` (no sprint enforcement)
- V1 only writes milestone data and logs to Markdown — no sprint, discussion, or label tables
- Logs a deprecation warning on every run

## Work Guidance

- Do not add new features or metrics to V1 handler
- Only fix critical bugs that break V1 compatibility
- Encourage migration to V2 config format

## Verification

- No dedicated tests for V1 handler
- V1 path is exercised when config `version` starts with `"1."`

## Child DOX Index

No child DOX files.
