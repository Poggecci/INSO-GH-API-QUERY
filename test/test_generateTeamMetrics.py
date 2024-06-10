import pytz
from src.generateTeamMetrics import getTeamMetricsForMilestone
import pytest
from unittest.mock import patch
from datetime import datetime
import logging


@pytest.fixture
def logger():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    return logger


mock_gh_res_with_issue_closed_by_dev = {
    "data": {
        "organization": {
            "projectsV2": {
                "nodes": [
                    {
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
                                        "reactions": {"nodes": []},
                                        "comments": {"nodes": []},
                                    },
                                    "urgency": {"number": 3},
                                    "difficulty": {"number": 2},
                                    "modifier": {"number": 1},
                                }
                            ],
                        },
                    }
                ]
            }
        }
    }
}

mock_gh_res_v20_milestone = {
    "data": {
        "organization": {
            "projectsV2": {
                "nodes": [
                    {
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
                                        "milestone": {
                                            "title": "v2.0"
                                        },  # Different milestone
                                        "assignees": {"nodes": [{"login": "dev1"}]},
                                        "timelineItems": {
                                            "nodes": [{"actor": {"login": "manager1"}}]
                                        },
                                        "reactions": {"nodes": []},
                                        "comments": {"nodes": []},
                                    },
                                    "urgency": {"number": 3},
                                    "difficulty": {"number": 2},
                                    "modifier": {"number": 1},
                                }
                            ],
                        },
                    }
                ]
            }
        }
    }
}

mock_gh_res_with_open_issue = {
    "data": {
        "organization": {
            "projectsV2": {
                "nodes": [
                    {
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
                                        "milestone": {"title": "v1.0"},
                                        "assignees": {"nodes": [{"login": "dev1"}]},
                                        "reactions": {"nodes": []},
                                        "comments": {"nodes": []},
                                    },
                                    "urgency": {"number": 3},
                                    "difficulty": {"number": 2},
                                    "modifier": {"number": 1},
                                }
                            ],
                        },
                    }
                ]
            }
        }
    }
}


@patch("src.generateTeamMetrics.run_graphql_query")
def test_issues_closed_by_non_managers_arent_counted(mock_run_graphql_query, logger):
    mock_run_graphql_query.return_value = mock_gh_res_with_issue_closed_by_dev

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90

    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    assert result.totalPointsClosed == 0
    assert result.devMetrics["dev1"].pointsClosed == 0


@patch("src.generateTeamMetrics.run_graphql_query")
def test_issues_not_belonging_to_milestone_arent_counted(
    mock_run_graphql_query, logger
):
    mock_run_graphql_query.return_value = mock_gh_res_v20_milestone

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90

    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    assert result.totalPointsClosed == 0
    assert result.devMetrics["dev1"].pointsClosed == 0


@patch("src.generateTeamMetrics.run_graphql_query")
def test_open_issues_arent_counted_iff_shouldCountOpenIssues_is_false(
    mock_run_graphql_query, logger
):
    mock_run_graphql_query.return_value = mock_gh_res_with_open_issue

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

    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
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
        milestoneGrade=milestoneGrade,
        shouldCountOpenIssues=shouldCountOpenIssues,
        logger=logger,
    )

    assert resultCountingOpen.totalPointsClosed != 0
    assert resultCountingOpen.devMetrics["dev1"].pointsClosed != pytest.approx(0)


mock_gh_res_issue_only_worked_by_manager = {
    "data": {
        "organization": {
            "projectsV2": {
                "nodes": [
                    {
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
                                        "milestone": {"title": "v1.0"},
                                        "assignees": {"nodes": [{"login": "manager1"}]},
                                        "reactions": {"nodes": []},
                                        "comments": {"nodes": []},
                                        "timelineItems": {
                                            "nodes": [{"actor": {"login": "manager1"}}],
                                        },
                                    },
                                    "urgency": {"number": 3},
                                    "difficulty": {"number": 2},
                                    "modifier": {"number": 1},
                                }
                            ],
                        },
                    }
                ]
            }
        }
    }
}

mock_gh_res_issue_with_hooray = {
    "data": {
        "organization": {
            "projectsV2": {
                "nodes": [
                    {
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
                                        "milestone": {"title": "v1.0"},
                                        "assignees": {"nodes": [{"login": "dev1"}]},
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
                                    "urgency": {"number": 3},
                                    "difficulty": {"number": 2},
                                    "modifier": {"number": 1},
                                }
                            ],
                        },
                    }
                ]
            }
        }
    }
}

mock_gh_res_issue_with_multiple_devs = {
    "data": {
        "organization": {
            "projectsV2": {
                "nodes": [
                    {
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
                                        "milestone": {"title": "v1.0"},
                                        "assignees": {
                                            "nodes": [
                                                {"login": "dev1"},
                                                {"login": "dev2"},
                                            ]
                                        },
                                        "reactions": {"nodes": []},
                                        "comments": {"nodes": []},
                                        "timelineItems": {
                                            "nodes": [{"actor": {"login": "manager1"}}],
                                        },
                                    },
                                    "urgency": {"number": 3},
                                    "difficulty": {"number": 2},
                                    "modifier": {"number": 1},
                                }
                            ],
                        },
                    }
                ]
            }
        }
    }
}


@patch("src.generateTeamMetrics.run_graphql_query")
def test_issues_only_worked_on_by_managers_arent_counted(
    mock_run_graphql_query, logger
):
    mock_run_graphql_query.return_value = mock_gh_res_issue_only_worked_by_manager

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2", "manager1"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90

    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    assert result.totalPointsClosed == 0
    assert "manager1" not in result.devMetrics


@patch("src.generateTeamMetrics.run_graphql_query")
def test_issues_with_hooray_reaction_get_bonus(mock_run_graphql_query, logger):
    mock_run_graphql_query.return_value = mock_gh_res_issue_with_hooray

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2", "manager1"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90

    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    expected_score = (3 * 2 + 1) * 1.1  # Urgency * Difficulty + Modifier * 110%
    assert result.totalPointsClosed == pytest.approx(expected_score)
    assert result.devMetrics["dev1"].pointsClosed == pytest.approx(expected_score)


@patch("src.generateTeamMetrics.run_graphql_query")
def test_issues_with_multiple_developers_have_points_divided(
    mock_run_graphql_query, logger
):
    mock_run_graphql_query.return_value = mock_gh_res_issue_with_multiple_devs

    org = "sample-org"
    team = "sample-team"
    milestone = "v1.0"
    members = ["dev1", "dev2", "manager1"]
    managers = ["manager1"]
    startDate = datetime(2023, 1, 1, tzinfo=pytz.UTC)
    endDate = datetime(2023, 12, 31, tzinfo=pytz.UTC)
    useDecay = True
    milestoneGrade = 90

    result = getTeamMetricsForMilestone(
        org=org,
        team=team,
        milestone=milestone,
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        milestoneGrade=milestoneGrade,
        logger=logger,
    )

    expected_score = 3 * 2 + 1  # Urgency * Difficulty + Modifier
    divided_score = expected_score / 2

    assert result.totalPointsClosed == pytest.approx(expected_score)
    assert result.devMetrics["dev1"].pointsClosed == pytest.approx(divided_score)
    assert result.devMetrics["dev2"].pointsClosed == pytest.approx(divided_score)


if __name__ == "__main__":
    pytest.main()
