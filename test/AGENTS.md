# Test Suite

## Purpose

- pytest test suite that validates scoring logic, parsing, discussion metrics, and milestone auto-extraction
- Tests mock all GraphQL API calls — no live API access required

## Ownership

- `test_generateTeamMetrics.py` — integration tests for `getTeamMetricsForMilestone` with mocked GraphQL responses
- `test/utils/test_issues.py` — unit tests for `shouldCountIssue`, `decay`, `calculateIssueScores`, `applyIssuePreProcessingHooks`
- `test/utils/test_discussions.py` — unit tests for discussion parsing, week indexing, participation tracking, and penalty calculation
- `test/utils/test_autoExtractMilestone.py` — unit tests for milestone auto-extraction logic

## Local Contracts

- Tests use `unittest.mock.patch` to mock `runGraphqlQuery` and `getProject`
- Mock GraphQL responses are inline dicts matching the GitHub GraphQL API response structure
- `pytest.approx` is used for float comparisons in scoring tests
- `test_generateTeamMetrics.py` tests cover: non-manager closure filtering, milestone filtering, open issue filtering, manager-only issues, 🎉 bonus, multi-developer point division, sprint minimum enforcement, lecture topic task tracking, and label point percentages
- `test_issues.py` uses a `create_issue` fixture factory for building `Issue` objects with defaults

## Work Guidance

- Follow existing mock patterns: define mock GraphQL response dicts, patch `runGraphqlQuery` and `getProject`
- Use `pytest.approx` for floating-point score assertions
- Test both positive and negative cases for scoring rules
- Keep test data minimal but representative of real GitHub API responses

## Verification

- Run `poetry run pytest` from the project root
- CI runs pytest on Python 3.11 across ubuntu-22.04, macos-latest, windows-latest

## Child DOX Index

No child DOX files.
