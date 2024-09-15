import pytest
from datetime import datetime, timedelta
from collections import defaultdict
from unittest.mock import MagicMock

from src.utils.issues import calculate_issue_scores, decay, should_count_issue
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
            "createdAt": datetime.now(),
            "closedAt": None,
            "closed": False,
            "closedBy": None,
            "milestone": "Sprint 1",
            "assignees": ["user1"],
            "reactions": [],
            "comments": [],
            "urgency": 1.0,
            "difficulty": 1.0,
            "modifier": 0.0,
            "isLectureTopicTask": False,
        }
        default_values.update(kwargs)
        return Issue(**default_values)

    return _create_issue


# Tests for should_count_issue function
def test_should_count_issue_valid(create_issue, mock_logger):
    issue = create_issue(milestone="Sprint 1", closed=True, closedBy="manager1")
    assert (
        should_count_issue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Sprint 1",
            managers=["manager1"],
            shouldCountOpenIssues=False,
        )
        == True
    )


def test_should_count_issue_no_milestone(create_issue, mock_logger):
    issue = create_issue(milestone=None)
    assert (
        should_count_issue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Sprint 1",
            managers=["manager1"],
            shouldCountOpenIssues=True,
        )
        == False
    )
    mock_logger.warning.assert_called_once()


def test_should_count_issue_wrong_milestone(create_issue, mock_logger):
    issue = create_issue(milestone="Sprint 2")
    assert (
        should_count_issue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Sprint 1",
            managers=["manager1"],
            shouldCountOpenIssues=True,
        )
        == False
    )


def test_should_count_issue_closed_by_non_manager(create_issue, mock_logger):
    issue = create_issue(closed=True, closedBy="user1")
    assert (
        should_count_issue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Sprint 1",
            managers=["manager1"],
            shouldCountOpenIssues=True,
        )
        == False
    )
    mock_logger.warning.assert_called_once()


def test_should_count_issue_open_not_allowed(create_issue, mock_logger):
    issue = create_issue(closed=False)
    assert (
        should_count_issue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Sprint 1",
            managers=["manager1"],
            shouldCountOpenIssues=False,
        )
        == False
    )


def test_should_count_issue_missing_fields(create_issue, mock_logger):
    issue = create_issue(urgency=None)
    assert (
        should_count_issue(
            issue=issue,
            logger=mock_logger,
            currentMilestone="Sprint 1",
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
    issue = create_issue(difficulty=2.0, urgency=3.0, assignees=["dev1", "dev2"])
    result = calculate_issue_scores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1", "dev2"],
        startDate=datetime(2023, 1, 1),
        endDate=datetime(2023, 1, 31),
        useDecay=False,
        logger=mock_logger,
    )
    assert result.pointsByDeveloper["dev1"] == pytest.approx(3.0)
    assert result.pointsByDeveloper["dev2"] == pytest.approx(3.0)
    assert sum(result.bonusesByDeveloper.values()) == 0


def test_calculate_issue_scores_with_decay(create_issue, mock_logger):
    issue = create_issue(difficulty=2.0, urgency=3.0, assignees=["dev1"])
    result = calculate_issue_scores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=datetime(2023, 1, 1),
        endDate=datetime(2023, 1, 31),
        useDecay=True,
        logger=mock_logger,
    )
    assert (
        result.pointsByDeveloper["dev1"] < 6.0
    )  # Score should be less than 2.0 * 3.0 due to decay


def test_calculate_issue_scores_with_modifier(create_issue, mock_logger):
    issue = create_issue(difficulty=2.0, urgency=3.0, modifier=1.0, assignees=["dev1"])
    result = calculate_issue_scores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=datetime(2023, 1, 1),
        endDate=datetime(2023, 1, 31),
        useDecay=False,
        logger=mock_logger,
    )
    assert result.pointsByDeveloper["dev1"] == pytest.approx(7.0)  # (2.0 * 3.0) + 1.0


def test_calculate_issue_scores_documentation_bonus(create_issue, mock_logger):
    issue = create_issue(
        difficulty=2.0,
        urgency=3.0,
        assignees=["dev1"],
        reactions=[Reaction(user_login="manager1", kind=ReactionKind.HOORAY)],
    )
    result = calculate_issue_scores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=datetime(2023, 1, 1),
        endDate=datetime(2023, 1, 31),
        useDecay=False,
        logger=mock_logger,
    )
    assert result.pointsByDeveloper["dev1"] == pytest.approx(6.0)
    assert result.bonusesByDeveloper[issue.author] == pytest.approx(0.6)  # 10% of 6.0


def test_calculate_issue_scores_comment_bonus(create_issue, mock_logger):
    issue = create_issue(
        difficulty=2.0,
        urgency=3.0,
        assignees=["dev1"],
        comments=[
            Comment(
                author_login="dev1",
                reactions=[Reaction(user_login="manager1", kind=ReactionKind.HOORAY)],
            )
        ],
    )
    result = calculate_issue_scores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=datetime(2023, 1, 1),
        endDate=datetime(2023, 1, 31),
        useDecay=False,
        logger=mock_logger,
    )
    assert result.pointsByDeveloper["dev1"] == pytest.approx(6.0)
    assert result.bonusesByDeveloper[issue.author] == pytest.approx(0.6)  # 10% of 6.0


def test_calculate_issue_scores_non_team_member(create_issue, mock_logger):
    issue = create_issue(difficulty=2.0, urgency=3.0, assignees=["dev1", "external"])
    result = calculate_issue_scores(
        issue=issue,
        managers=["manager1"],
        developers=["dev1"],
        startDate=datetime(2023, 1, 1),
        endDate=datetime(2023, 1, 31),
        useDecay=False,
        logger=mock_logger,
    )
    assert result.pointsByDeveloper["dev1"] == pytest.approx(6.0)
    assert "external" not in result.pointsByDeveloper
    mock_logger.warning.assert_called_once()


# Run the tests
if __name__ == "__main__":
    pytest.main([__file__])
