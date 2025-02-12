import pytest
from datetime import datetime, timedelta
from collections import defaultdict
from unittest.mock import MagicMock
from src.utils.constants import pr_tz
from src.utils.issues import calculateIssueScores, decay, shouldCountIssue
from src.utils.models import Issue, IssueMetrics, Reaction, ReactionKind, Comment


# Mock the logging module
@pytest.fixture
def mock_logger():
    return MagicMock()


# Fixture for creating Issue objects
@pytest.fixture
def create_issue():
    def _create_issue(**kwargs):
        default_values = {
            "url": "https://github.com/org/repo/issues/1",
            "number": 1,
            "title": "Test Issue",
            "author": "user1",
            "createdAt": datetime.now(tz=pr_tz),
            "closedAt": None,
            "closed": False,
            "closedBy": None,
            "milestone": "Milestone #1",
            "assignees": ["user1"],
            "labels": [],
            "reactions": [],
            "comments": [],
            "urgency": 1.0,
            "difficulty": 1.0,
            "modifier": 0.0,
            "isLectureTopicTask": False,
            "isTeamLeadTask": False,
        }
        default_values.update(kwargs)
        return Issue(**default_values)

    return _create_issue


# Tests for should_count_issue function
def test_should_count_issue_valid(create_issue, mock_logger):
    issue = create_issue(milestone="Milestone #1", closed=True, closedBy="manager1")
    assert (
        shouldCountIssue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Milestone #1",
            managers=["manager1"],
            shouldCountOpenIssues=False,
        )
        == True
    )


def test_should_count_issue_no_milestone(create_issue, mock_logger):
    issue = create_issue(milestone=None)
    assert (
        shouldCountIssue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Milestone #1",
            managers=["manager1"],
            shouldCountOpenIssues=True,
        )
        == False
    )
    mock_logger.warning.assert_called_once()


def test_should_count_issue_wrong_milestone(create_issue, mock_logger):
    issue = create_issue(milestone="Milestone #2")
    assert (
        shouldCountIssue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Milestone #1",
            managers=["manager1"],
            shouldCountOpenIssues=True,
        )
        == False
    )


def test_should_count_issue_closed_by_non_manager(create_issue, mock_logger):
    issue = create_issue(closed=True, closedBy="user1")
    assert (
        shouldCountIssue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Milestone #1",
            managers=["manager1"],
            shouldCountOpenIssues=True,
        )
        == False
    )
    mock_logger.warning.assert_called_once()


def test_should_count_issue_open_not_allowed(create_issue, mock_logger):
    issue = create_issue(closed=False)
    assert (
        shouldCountIssue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Milestone #1",
            managers=["manager1"],
            shouldCountOpenIssues=False,
        )
        == False
    )


def test_should_count_issue_missing_fields(create_issue, mock_logger):
    noUrgencyIssue = create_issue(urgency=None)

    assert (
        shouldCountIssue(
            issue=noUrgencyIssue,
            logger=mock_logger,
            currentMilestone="Milestone #1",
            managers=["manager1"],
            shouldCountOpenIssues=True,
        )
        == False
    )
    mock_logger.warning.assert_called_once()

    mock_logger.warning.reset_mock()
    noDifficultyIssue = create_issue(difficulty=None)

    assert (
        shouldCountIssue(
            issue=noDifficultyIssue,
            logger=mock_logger,
            currentMilestone="Milestone #1",
            managers=["manager1"],
            shouldCountOpenIssues=True,
        )
        == False
    )
    mock_logger.warning.assert_called_once()


# Tests for decay function
def test_decay_start_of_milestone():
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 31)
    created = start
    assert decay(start, end, created) == pytest.approx(1.0)


def test_decay_end_of_milestone():
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 31)
    created = end
    assert decay(start, end, created) == pytest.approx(0.3, rel=1e-2)


def test_decay_after_milestone():
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 31)
    created = end + timedelta(days=1)
    assert decay(start, end, created) == pytest.approx(0.3, rel=1e-2)


def test_decay_middle_of_milestone():
    start = datetime(2023, 1, 1)
    end = datetime(2023, 1, 31)
    created = start + timedelta(days=15)
    assert 0.3 < decay(start, end, created) < 1.0


# Tests for calculate_issue_scores function
def test_calculate_issue_scores_basic(create_issue, mock_logger):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    issue = create_issue(difficulty=2.0, urgency=3.0, assignees=["dev1", "dev2"])

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1", "dev2"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=False,  # Disable Decay to simplify calculation
        logger=mock_logger,
    )

    assert result.pointsByDeveloper["dev1"] == pytest.approx(3.0)
    assert result.pointsByDeveloper["dev2"] == pytest.approx(3.0)
    assert sum(result.bonusesByDeveloper.values()) == 0


def test_calculate_issue_scores_with_decay(create_issue, mock_logger):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    middleDate = milestoneStart + (milestoneEnd - milestoneStart) / 2
    issue = create_issue(
        difficulty=2.0, urgency=3.0, assignees=["dev1"], createdAt=middleDate
    )

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=True,
        logger=mock_logger,
    )

    assert (
        result.pointsByDeveloper["dev1"] < 6.0
    )  # Score should be less than 2.0 * 3.0 due to decay


def test_calculate_issue_scores_with_modifier(create_issue, mock_logger):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    issue = create_issue(difficulty=2.0, urgency=3.0, modifier=1.0, assignees=["dev1"])

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=False,
        logger=mock_logger,
    )

    assert result.pointsByDeveloper["dev1"] == pytest.approx(7.0)  # (2.0 * 3.0) + 1.0


def test_calculate_issue_scores_documentation_bonus(create_issue, mock_logger):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    issue = create_issue(
        difficulty=2.0,
        urgency=3.0,
        assignees=["dev1"],
        reactions=[Reaction(user_login="manager1", kind=ReactionKind.HOORAY)],
    )

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=False,
        logger=mock_logger,
    )

    assert result.pointsByDeveloper["dev1"] == pytest.approx(6.0)
    assert result.bonusesByDeveloper[issue.author] == pytest.approx(0.6)  # 10% of 6.0


def test_calculate_issue_scores_comment_bonus(create_issue, mock_logger):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    issue = create_issue(
        difficulty=2.0,
        urgency=3.0,
        assignees=["dev1"],
        comments=[
            Comment(
                author_login="dev2",
                reactions=[Reaction(user_login="manager1", kind=ReactionKind.HOORAY)],
            )
        ],
    )

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1", "dev2"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=False,
        logger=mock_logger,
    )

    assert result.pointsByDeveloper["dev1"] == pytest.approx(6.0)
    assert result.bonusesByDeveloper["dev2"] == pytest.approx(0.6)  # 10% of 6.0


def test_calculate_issue_scores_documentation_bonus_double_reaction(
    create_issue, mock_logger
):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    issue = create_issue(
        difficulty=2.0,
        urgency=3.0,
        assignees=["dev1"],
        reactions=[Reaction(user_login="manager1", kind=ReactionKind.HOORAY)],
        comments=[
            Comment(
                author_login="dev2",
                reactions=[Reaction(user_login="manager1", kind=ReactionKind.HOORAY)],
            )
        ],
    )

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1", "dev2"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=False,
        logger=mock_logger,
    )

    assert result.pointsByDeveloper["dev1"] == pytest.approx(6.0)
    assert result.bonusesByDeveloper["dev1"] == pytest.approx(0.0)
    assert result.bonusesByDeveloper["dev2"] == pytest.approx(0.0)


def test_calculate_issue_scores_non_team_member(create_issue, mock_logger):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    issue = create_issue(difficulty=2.0, urgency=3.0, assignees=["dev1", "external"])

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=False,
        logger=mock_logger,
    )

    assert result.pointsByDeveloper["dev1"] == pytest.approx(6.0)
    assert "external" not in result.pointsByDeveloper
    mock_logger.warning.assert_called_once()


def test_calculate_issue_scores_team_lead_task(create_issue, mock_logger):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    issue = create_issue(
        difficulty=2.0,
        urgency=3.0,
        assignees=["dev1"],
        labels=["team lead task"],
        isTeamLeadTask=True,
    )

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=False,
        teamLeadTaskAdditionalPercent=20,
        logger=mock_logger,
    )

    assert result.pointsByDeveloper["dev1"] == pytest.approx(6.0)
    assert result.bonusesByDeveloper["dev1"] == pytest.approx(1.2)  # 20% of 6.0


def test_calculate_issue_scores_multiple_team_lead_task(create_issue, mock_logger):
    milestoneStart = datetime(year=2023, month=1, day=1, tzinfo=pr_tz)
    milestoneEnd = datetime(year=2023, month=1, day=31, tzinfo=pr_tz)
    issue = create_issue(
        difficulty=2.0,
        urgency=3.0,
        assignees=["dev1", "dev2"],
        labels=["team lead task"],
        isTeamLeadTask=True,
    )

    result = calculateIssueScores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1", "dev2"],
        startDate=milestoneStart,
        endDate=milestoneEnd,
        useDecay=False,
        teamLeadTaskAdditionalPercent=20,
        logger=mock_logger,
    )

    assert result.pointsByDeveloper["dev1"] == pytest.approx(3.0)  # Half of 6.0
    assert result.pointsByDeveloper["dev2"] == pytest.approx(3.0)  # Half of 6.0
    assert result.bonusesByDeveloper["dev1"] == pytest.approx(0.6)  # 20% of half of 6.0
    assert result.bonusesByDeveloper["dev2"] == pytest.approx(0.6)  # 20% of half of 6.0


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__])
