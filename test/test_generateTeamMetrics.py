import pytz
from src.generateTeamMetrics import getTeamMetricsForMilestone
import pytest
from unittest.mock import patch
from datetime import datetime
import logging

from src.utils.models import Project


@pytest.fixture
def logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    return logger


mock_project = Project(number=1, name="test", url="", public=True)

mock_gh_res_with_issue_closed_by_dev = {
    "organization": {
        "projectV2": {
            "title": "sample-team",
            "items": {
                "pageInfo": {
                    "endCursor": "end-cursor",
                    "hasNextPage": False,
                },
                "nodes": [
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/1",
                            "number": 1,
                            "title": "Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "timelineItems": {
                                "nodes": [
                                    {
                                        "actor": {
                                            "login": "dev2"
                                        }  # Closed by non-manager
                                    }
                                ]
                            },
                            "labels": {"nodes": []},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                        },
                        "Urgency": {"number": 3},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 1},
                    }
                ],
            },
        }
    }
}

mock_gh_res_v20_milestone = {
    "organization": {
        "projectV2": {
            "title": "sample-team",
            "items": {
                "pageInfo": {
                    "endCursor": "end-cursor",
                    "hasNextPage": False,
                },
                "nodes": [
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/2",
                            "number": 2,
                            "title": "Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v2.0"},  # Different milestone
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}]
                            },
                            "labels": {"nodes": []},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                        },
                        "Urgency": {"number": 3},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 1},
                    }
                ],
            },
        }
    }
}

mock_gh_res_with_open_issue = {
    "organization": {
        "projectV2": {
            "title": "sample-team",
            "items": {
                "pageInfo": {
                    "endCursor": "end-cursor",
                    "hasNextPage": False,
                },
                "nodes": [
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/3",
                            "number": 3,
                            "title": "Open Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": False,  # Open issue
                            "closedAt": None,
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "labels": {"nodes": []},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                            "timelineItems": {"nodes": []},
                        },
                        "Urgency": {"number": 3},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 1},
                    }
                ],
            },
        }
    }
}


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_issues_closed_by_non_managers_arent_counted(
    mock_runGraphqlQuery, mock_getProject, logger
):
    mock_getProject.return_value = mock_project
    mock_runGraphqlQuery.return_value = mock_gh_res_with_issue_closed_by_dev

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90
    sprints = 1
    minTasksPerSprint = 0

    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    assert result.totalPointsClosed == 0
    assert result.devMetrics["dev1"].pointsClosed == 0


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_issues_not_belonging_to_milestone_arent_counted(
    mock_runGraphqlQuery, mock_getProject, logger
):
    mock_getProject.return_value = mock_project
    mock_runGraphqlQuery.return_value = mock_gh_res_v20_milestone

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90
    sprints = 1
    minTasksPerSprint = 0
    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    assert result.totalPointsClosed == 0
    assert result.devMetrics["dev1"].pointsClosed == 0


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_open_issues_arent_counted_iff_shouldCountOpenIssues_is_false(
    mock_runGraphqlQuery, mock_getProject, logger
):
    mock_getProject.return_value = mock_getProject
    mock_runGraphqlQuery.return_value = mock_gh_res_with_open_issue

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90
    shouldCountOpenIssues = False
    sprints = 1
    minTasksPerSprint = 0
    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        shouldCountOpenIssues=shouldCountOpenIssues,
        logger=logger,
    )

    assert result.totalPointsClosed == 0
    assert result.devMetrics["dev1"].pointsClosed == 0

    # ensure the issue is counted if we are counting open issues
    shouldCountOpenIssues = True
    resultCountingOpen = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        shouldCountOpenIssues=shouldCountOpenIssues,
        logger=logger,
    )

    assert resultCountingOpen.totalPointsClosed != 0
    assert resultCountingOpen.devMetrics["dev1"].pointsClosed != pytest.approx(0)


mock_gh_res_issue_only_worked_by_manager = {
    "organization": {
        "projectV2": {
            "title": "sample-team",
            "items": {
                "pageInfo": {
                    "endCursor": "end-cursor",
                    "hasNextPage": False,
                },
                "nodes": [
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/4",
                            "number": 4,
                            "title": "Issue Title",
                            "author": {"login": "manager1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "manager1"}]},
                            "labels": {"nodes": []},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}],
                            },
                        },
                        "Urgency": {"number": 3},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 1},
                    }
                ],
            },
        }
    }
}

mock_gh_res_issue_with_hooray = {
    "organization": {
        "projectV2": {
            "title": "sample-team",
            "items": {
                "pageInfo": {
                    "endCursor": "end-cursor",
                    "hasNextPage": False,
                },
                "nodes": [
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/5",
                            "number": 5,
                            "title": "Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "labels": {"nodes": []},
                            "reactions": {
                                "nodes": [
                                    {
                                        "user": {"login": "manager1"}
                                    }  # Manager reacted with 🎉
                                ]
                            },
                            "comments": {"nodes": []},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}],
                            },
                        },
                        "Urgency": {"number": 3},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 1},
                    }
                ],
            },
        }
    }
}

mock_gh_res_issue_with_multiple_devs = {
    "organization": {
        "projectV2": {
            "title": "sample-team",
            "items": {
                "pageInfo": {
                    "endCursor": "end-cursor",
                    "hasNextPage": False,
                },
                "nodes": [
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/6",
                            "number": 6,
                            "title": "Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {
                                "nodes": [
                                    {"login": "dev1"},
                                    {"login": "dev2"},
                                ]
                            },
                            "labels": {"nodes": []},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}],
                            },
                        },
                        "Urgency": {"number": 3},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 1},
                    }
                ],
            },
        }
    }
}


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_issues_only_worked_on_by_managers_arent_counted(
    mock_runGraphqlQuery, mock_getProject, logger
):
    mock_getProject.return_value = mock_getProject
    mock_runGraphqlQuery.return_value = mock_gh_res_issue_only_worked_by_manager

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2", "manager1"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90
    sprints = 1
    minTasksPerSprint = 0
    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    assert result.totalPointsClosed == 0
    assert "manager1" not in result.devMetrics


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_issues_with_hooray_reaction_get_bonus(
    mock_runGraphqlQuery, mock_getProject, logger
):
    mock_getProject.return_value = mock_project
    mock_runGraphqlQuery.return_value = mock_gh_res_issue_with_hooray

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2", "manager1"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 100
    sprints = 1
    minTasksPerSprint = 0
    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    expected_score = (3 * 2 + 1) * 1.1  # Urgency * Difficulty + Modifier * 110%
    assert result.totalPointsClosed == pytest.approx(
        expected_score / 1.1
    )  # make sure the total points exclude bonuses
    assert result.devMetrics["dev1"].pointsClosed == pytest.approx(expected_score)


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_issues_with_multiple_developers_have_points_divided(
    mock_runGraphqlQuery, mock_getProject, logger
):
    mock_getProject.return_value = mock_getProject
    mock_runGraphqlQuery.return_value = mock_gh_res_issue_with_multiple_devs

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2", "manager1"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90
    sprints = 1
    minTasksPerSprint = 0
    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    expected_score = 3 * 2 + 1  # Urgency * Difficulty + Modifier
    divided_score = expected_score / 2

    assert result.totalPointsClosed == pytest.approx(expected_score)
    assert result.devMetrics["dev1"].pointsClosed == pytest.approx(divided_score)
    assert result.devMetrics["dev2"].pointsClosed == pytest.approx(divided_score)


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_students_get_0_if_under_minimum_tasks_per_sprint(
    mock_runGraphqlQuery, mock_getProject, logger
):
    mock_getProject.return_value = mock_getProject
    mock_runGraphqlQuery.return_value = mock_gh_res_issue_with_multiple_devs

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90
    sprints = 2
    minTasksPerSprint = 2

    # Mocked response will show both devs working on issues but neither has completed enough tasks in the sprint
    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    # Assert that both developers get 0 if they have not completed the minimum number of tasks per sprint
    assert result.devMetrics["dev1"].individualGrade == 0.0
    assert result.devMetrics["dev2"].individualGrade == 0.0


mock_gh_res_issues_with_lecture_topic_tasks = {
    "organization": {
        "projectV2": {
            "title": "sample-team",
            "items": {
                "pageInfo": {
                    "endCursor": "end-cursor",
                    "hasNextPage": False,
                },
                "nodes": [
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/7",
                            "number": 7,
                            "title": "[Lecture Topic Task] Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "labels": {"nodes": []},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}],
                            },
                        },
                        "Urgency": {"number": 3},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 1},
                    },
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/8",
                            "number": 8,
                            "title": "Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "labels": {"nodes": [{"name": "lecture topic task"}]},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}],
                            },
                        },
                        "Urgency": {"number": 3},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 1},
                    },
                ],
            },
        }
    }
}


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_issues_with_lecture_topic_task_label(
    mock_runGraphqlQuery, mock_getProject, logger
):
    mock_getProject.return_value = mock_getProject
    mock_runGraphqlQuery.return_value = mock_gh_res_issues_with_lecture_topic_tasks

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "manager1"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90
    sprints = 1
    minTasksPerSprint = 0
    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    assert result.devMetrics["dev1"].lectureTopicTasksClosed == 2


mock_gh_res_issues_points_percent_by_label = {
    "organization": {
        "projectV2": {
            "title": "sample-team",
            "items": {
                "pageInfo": {
                    "endCursor": "end-cursor",
                    "hasNextPage": False,
                },
                "nodes": [
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/9",
                            "number": 9,
                            "title": "Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "labels": {"nodes": [{"name": "1"}]},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}],
                            },
                        },
                        "Urgency": {"number": 1},
                        "Difficulty": {"number": 2},
                        "Modifier": {"number": 0},
                    },
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/10",
                            "number": 10,
                            "title": "Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "labels": {"nodes": [{"name": "1"}, {"name": "2"}]},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}],
                            },
                        },
                        "Urgency": {"number": 1},
                        "Difficulty": {"number": 3},
                        "Modifier": {"number": 0},
                    },
                    {
                        "content": {
                            "url": "https://github.com/org/repo/issues/11",
                            "number": 11,
                            "title": "Issue Title",
                            "author": {"login": "dev1"},
                            "createdAt": "2023-01-01T00:00:00Z",
                            "closed": True,
                            "closedAt": "2023-01-01T00:00:00Z",
                            "milestone": {"title": "v1.0"},
                            "assignees": {"nodes": [{"login": "dev1"}]},
                            "labels": {"nodes": [{"name": "2"}, {"name": "3"}]},
                            "reactions": {"nodes": []},
                            "comments": {"nodes": []},
                            "timelineItems": {
                                "nodes": [{"actor": {"login": "manager1"}}],
                            },
                        },
                        "Urgency": {"number": 1},
                        "Difficulty": {"number": 5},
                        "Modifier": {"number": 0},
                    },
                ],
            },
        }
    }
}


@patch("src.generateTeamMetrics.getProject")
@patch("src.generateTeamMetrics.runGraphqlQuery")
def test_issues_points_percent_by_label(mock_runGraphqlQuery, mock_getProject, logger):
    mock_getProject.return_value = mock_getProject
    mock_runGraphqlQuery.return_value = mock_gh_res_issues_points_percent_by_label

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "manager1"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90
    sprints = 1
    minTasksPerSprint = 0
    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        sprints=sprints,
        minTasksPerSprint=minTasksPerSprint,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    pointsPercentByLabel = result.devMetrics["dev1"].pointPercentByLabel
    totalPoints = result.devMetrics["dev1"].pointsClosed
    assert totalPoints == 10
    assert pointsPercentByLabel["1"] == pytest.approx(
        5 / totalPoints * 100
    )  # Issues 1 and 2 total to 5 points and contain "1" label
    assert pointsPercentByLabel["2"] == pytest.approx(
        8 / totalPoints * 100
    )  # Issues 2 and 3 total to 8 points and contain "2" label
    assert pointsPercentByLabel["3"] == pytest.approx(
        5 / totalPoints * 100
    )  # Issue 3 totals to 5 points and contain "3" label


if __name__ == "__main__":
    pytest.main()
