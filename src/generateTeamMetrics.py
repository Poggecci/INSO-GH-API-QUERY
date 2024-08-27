import json
import logging
from typing import Iterable
from datetime import datetime

from src.getTeamMembers import get_team_members
from src.utils.models import DeveloperMetrics, MilestoneData
from src.utils.queryRunner import run_graphql_query

get_team_issues = """
query QueryProjectItemsForTeam(
  $owner: String!
  $team: String!
  $nextPage: String
) {
  organization(login: $owner) {
    projectsV2(
      query: $team
      first: 1
      orderBy: { field: TITLE, direction: ASC }
    ) {
      nodes {
        title
        items(first: 100, after: $nextPage) {
          pageInfo {
            endCursor
            hasNextPage
          }
          nodes {
            content {
              ... on Issue {
                url
                number
                title
                author {
                    login
                }
                createdAt
                closed
                milestone {
                  title
                }
                assignees(first: 20) {
                  nodes {
                    login
                  }
                }
                reactions(first: 10, content: HOORAY) {
                  nodes {
                    user {
                      login
                    }
                  }
                }
                comments(first: 30) {
                  nodes {
                    author {
                      login
                    }
                    reactions(first: 10, content: HOORAY) {
                      nodes {
                        user {
                          login
                        }
                      }
                    }
                  }
                }
                timelineItems(last: 1, itemTypes : [CLOSED_EVENT]){
                    nodes {
                        ... on ClosedEvent {
                                actor {
                                    login
                                }
                        }
                    }
                }
              }
            }
            urgency: fieldValueByName(name: "Urgency") {
              ... on ProjectV2ItemFieldNumberValue {
                number
              }
            }
            difficulty: fieldValueByName(name: "Difficulty") {
              ... on ProjectV2ItemFieldNumberValue {
                number
              }
            }
            modifier: fieldValueByName(name: "Modifier") {
              ... on ProjectV2ItemFieldNumberValue {
                number
              }
            }
          }
        }
      }
    }
  }
}
"""


def decay(
    milestoneStart: datetime, milestoneEnd: datetime, issueCreated: datetime
) -> float:
    duration = (milestoneEnd - milestoneStart).days
    if issueCreated > milestoneEnd:
        issueCreated = milestoneEnd
    issueLateness = max(0, (issueCreated - milestoneStart).days)
    decayBase = 1 + 1 / duration
    difference = pow(decayBase, 3 * duration) - pow(decayBase, 0)
    finalDecrease = 0.7
    translate = 1 + finalDecrease / difference
    return max(
        0, translate - finalDecrease * pow(decayBase, 3 * issueLateness) / difference
    )


def outliersRemovedAverage(scores: Iterable) -> float:
    smallest_elem = min(scores, default=0)
    largestVal = max(scores, default=0)
    newLength = len(list(scores)) - (largestVal != 0) - (smallest_elem != 0)
    total = sum(scores, start=0) - largestVal - smallest_elem
    return total / max(1, newLength)


def getTeamMetricsForMilestone(
    org: str,
    team: str,
    milestone: str,
    members: list[str],
    managers: list[str],
    startDate: datetime,
    endDate: datetime,
    useDecay: bool,
    milestoneGrade: float,
    shouldCountOpenIssues: bool = False,
    logger: logging.Logger | None = None,
) -> MilestoneData:
    if logger is None:
        logger = logging.getLogger(__name__)
    developers = [member for member in members if member not in managers]
    devPointsClosed = {dev: 0.0 for dev in developers}
    devLectureTopicTasks = {dev: 0 for dev in developers}
    totalPointsClosed = 0.0
    params = {"owner": org, "team": team}
    milestoneData = MilestoneData()
    hasAnotherPage = True
    while hasAnotherPage:
        response: dict = run_graphql_query(get_team_issues, params)
        projects: list[dict] = response["data"]["organization"]["projectsV2"]["nodes"]
        project = next(filter(lambda x: x["title"] == team, projects), None)
        if not project:
            logger.critical(
                "Project not found in org. Likely means the project board doesn't share the same name as the team."
            )
            raise Exception(
                "Project not found in org. Likely means the project board"
                " doesn't share the same name as the team."
            )
        # Extract data
        issues = project["items"]["nodes"]
        for issue in issues:
            if issue["content"].get("milestone", None) is None:
                issueNumber = issue["content"].get("number")
                issueUrl = issue["content"].get("url")
                if issueUrl:
                    logger.warning(
                        f"[Issue #{issueNumber}]({issueUrl}) is not associated with a milestone."
                    )
                continue
            if issue["content"]["milestone"]["title"] != milestone:
                continue
            if issue["content"].get("closed", False):
                closedByList = issue["content"]["timelineItems"][
                    "nodes"
                ]  # should always have a length of 1 if the issue was closed
                closedBy = (
                    closedByList[0]["actor"]["login"]
                    if len(closedByList) == 1
                    else None
                )
                if closedBy is None:
                    logger.warning(
                        f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) is marked as closed but doesn't have an user who closed it."
                    )
                    continue
                if closedBy not in managers:
                    logger.warning(
                        f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) was closed by non-manager {closedBy}. Only issues closed by managers are accredited."
                    )
                    continue

            elif not shouldCountOpenIssues:
                continue
            if issue["difficulty"] is None or issue["urgency"] is None:
                logger.warning(
                    f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) does not have the Urgency and/or Difficulty fields populated"
                )
                continue
            if not issue["difficulty"] or not issue["urgency"]:
                logger.warning(
                    f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) does not have the Urgency and/or Difficulty fields populated"
                )
                continue

            if issue["modifier"] is None or not issue["modifier"]:
                issue["modifier"] = {"number": 0}
            workedOnlyByManager = True
            numberAssignees = len(issue["content"]["assignees"]["nodes"])
            print(issue)
            createdAt = datetime.fromisoformat(issue["content"]["createdAt"])
            issueScore = (
                issue["difficulty"]["number"]
                * issue["urgency"]["number"]
                * (decay(startDate, endDate, createdAt) if useDecay else 1)
                + issue["modifier"]["number"]
            )
            # attribute documentation bonus is a manager has reacted with 🎉
            documentationBonus = issueScore * 0.1
            if any(
                map(
                    (lambda reaction: (reaction["user"]["login"] in managers)),
                    issue["content"]["reactions"]["nodes"],
                )
            ):
                if issue["content"]["author"]["login"] not in managers:
                    devPointsClosed[
                        issue["content"]["author"]["login"]
                    ] += documentationBonus
                    logger.info(
                        f"Documentation Bonus given to [Issue #{issue['content'].get('number')}]({issue['content'].get('url')})"
                    )
                    totalPointsClosed += documentationBonus
            else:
                for comment in issue["content"]["comments"]["nodes"]:
                    if (
                        any(
                            map(
                                (
                                    lambda reaction: (
                                        reaction["user"]["login"] in managers
                                    )
                                ),
                                comment["reactions"]["nodes"],
                            )
                        )
                        and issue["content"]["author"]["login"] not in managers
                    ):
                        devPointsClosed[
                            comment["author"]["login"]
                        ] += documentationBonus
                        break  # only attribute the bonus once and to the earliest comment

            # attribute points to correct developer
            for dev in issue["content"]["assignees"]["nodes"]:
                if dev["login"] in managers:
                    logger.info(
                        f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) assigned to manager {dev['login']}"
                    )
                    continue
                if dev["login"] not in developers:
                    logger.warning(
                        f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) assigned to developer {dev['login']} not belonging to the team."
                    )
                    continue

                # attribute Lecture topic tasks even if they are a manager
                if "[Lecture Topic Task]" in issue["content"].get("title", ""):
                    devLectureTopicTasks[dev["login"]] += 1
                if dev["login"] not in managers:
                    workedOnlyByManager = False
                if dev["login"] in managers:
                    continue  # don't count manager metrics
                devPointsClosed[dev["login"]] += issueScore / numberAssignees
            if not workedOnlyByManager:
                totalPointsClosed += issueScore

        hasAnotherPage = project["items"]["pageInfo"]["hasNextPage"]
        if hasAnotherPage:
            params["nextPage"] = project["items"]["pageInfo"]["endCursor"]

    untrimmedAverage = totalPointsClosed / max(1, len(devPointsClosed))
    trimmedAverage = outliersRemovedAverage(devPointsClosed.values())
    devBenchmark = max(
        1, min(untrimmedAverage, trimmedAverage) / (milestoneGrade / 100)
    )

    milestoneData.totalPointsClosed = totalPointsClosed
    for dev in developers:
        contribution = devPointsClosed[dev] / max(totalPointsClosed, 1)
        milestoneData.devMetrics[dev] = DeveloperMetrics(
            pointsClosed=devPointsClosed[dev],
            percentContribution=contribution * 100.0,
            expectedGrade=min(
                (devPointsClosed[dev] / devBenchmark) * milestoneGrade, 100.0
            ),
            lectureTopicTasksClosed=devLectureTopicTasks[dev],
        )
    return milestoneData


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        exit(0)
    _, course_config_file, *_ = sys.argv
    with open(course_config_file) as course_config:
        course_data = json.load(course_config)
    organization = course_data["organization"]
    teams_and_teamdata = course_data["teams"]
    if (
        course_data.get("milestoneStartsOn", None) is None
        or not course_data["milestoneStartsOn"]
        or course_data["milestoneStartsOn"] is None
        or course_data.get("milestoneEndsOn", None) is None
        or course_data["milestoneEndsOn"] is None
        or not course_data["milestoneEndsOn"]
    ):
        startDate = datetime.now()
        endDate = datetime.now()
        useDecay = False
    else:
        startDate = datetime.fromisoformat(course_data["milestoneStartsOn"])
        endDate = datetime.fromisoformat(course_data["milestoneEndsOn"])
        useDecay = True

    print("Organization: ", organization)

    team_metrics = {}
    for team, teamdata in teams_and_teamdata.items():
        print("Team: ", team)
        print("Managers: ", teamdata["managers"])
        print("Milestone: ", teamdata["milestone"])
        members = get_team_members(organization, team)
        print(
            getTeamMetricsForMilestone(
                org=organization,
                team=team,
                milestone=teamdata["milestone"],
                milestoneGrade=teamdata["milestoneGrade"],
                members=members,
                managers=teamdata["managers"],
                startDate=startDate,
                endDate=endDate,
                useDecay=useDecay,
            )
        )
