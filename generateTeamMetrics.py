import logging
from typing import Iterable
from utils.models import Developer, DeveloperMetrics, MilestoneData, SprintData
import datetime as dt
from utils.queryRunner import run_graphql_query

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
                closedAt
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
    milestoneStart: dt.date, milestoneEnd: dt.date, issueCreated: dt.date
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


# Expects each score to be [0,inf)
def outliersRemovedAverage(scores: Iterable) -> float:
    non_zero_lst = [x for x in scores if x > 0]
    smallest_non_zero = min(non_zero_lst, default=0)
    largestVal = max(non_zero_lst, default=0)
    newLength = len(non_zero_lst) - (largestVal != 0) - (smallest_non_zero != 0)
    total = sum(non_zero_lst) - largestVal - smallest_non_zero
    return total / max(1, newLength)


def createSprints(
    startDate: dt.date, endDate: dt.date, duration: dt.timedelta
) -> list[SprintData]:
    sprints = []
    currentDate = startDate
    while currentDate < endDate:
        if currentDate + duration > endDate:
            sprints.append(
                SprintData(startDate=currentDate, duration=endDate - currentDate)
            )
        else:
            sprints.append(SprintData(startDate=currentDate, duration=duration))
        currentDate += duration
    return sprints


def findSprintIndex(sprints: list[SprintData], targetDate: dt.date) -> int:
    for index, sprint in enumerate(sprints):
        if sprint.startDate <= targetDate < (sprint.startDate + sprint.duration):
            return index
    return -1


def getTeamMetricsForMilestone(
    org: str,
    team: str,
    milestone: str,
    members: list[Developer],
    managers: list[Developer],
    startDate: dt.date,
    endDate: dt.date,
    sprintDuration: dt.timedelta,
    useDecay: bool,
    milestoneGrade: float,
    shouldCountOpenIssues: bool = False,
    logger: logging.Logger | None = None,
) -> MilestoneData:
    if logger is None:
        logger = logging.getLogger(__name__)
    sprints = createSprints(
        startDate=startDate, endDate=endDate, duration=sprintDuration
    )
    params = {"owner": org, "team": team}
    milestoneData = MilestoneData(startDate=startDate, endDate=endDate)
    milestoneData.developers = {member for member in members if member not in managers}
    milestoneData.sprints = sprints
    hasAnotherPage = True
    while hasAnotherPage:
        response = run_graphql_query(get_team_issues, params)
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
            createdAt = dt.datetime.fromisoformat(issue["content"]["createdAt"]).date()
            closedAt = dt.datetime.fromisoformat(
                issue["content"].get("closedAt", dt.datetime.now())
            ).date()
            sprintIndex = (
                findSprintIndex(sprints, closedAt) if closedAt is not None else -1
            )
            sprint = sprints[sprintIndex]
            assignee = issue["content"]["author"]["login"]
            issueScore = (
                issue["difficulty"]["number"]
                * issue["urgency"]["number"]
                * (decay(startDate, endDate, createdAt) if useDecay else 1)
                + issue["modifier"]["number"]
            )
            # attribute documentation bonus is a manager has reacted with 🎉
            documentationBonus = issueScore * 0.1
            issueAuthor = Developer(githubUsername=issue["content"]["author"]["login"])
            if any(
                map(
                    (lambda reaction: (reaction["user"]["login"] in managers)),
                    issue["content"]["reactions"]["nodes"],
                )
            ):
                if issueAuthor not in managers:
                    sprint.devMetrics[issueAuthor].pointsClosed += documentationBonus
                    logger.info(
                        f"Documentation Bonus given to [Issue #{issue['content'].get('number')}]({issue['content'].get('url')})"
                    )
            else:
                for comment in issue["content"]["comments"]["nodes"]:
                    commenter = comment["author"]["login"]
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
                        and issueAuthor not in managers
                    ):
                        sprint.devMetrics[commenter].pointsClosed += documentationBonus
                        break  # only attribute the bonus once and to the earliest comment

            # attribute points to correct developer
            for assignee in issue["content"]["assignees"]["nodes"]:
                dev = Developer(githubUsername=assignee["login"])
                if dev in managers:
                    logger.info(
                        f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) assigned to manager {assignee['login']}"
                    )
                    continue
                if dev not in milestoneData.developers:
                    logger.warning(
                        f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) assigned to developer {assignee['login']} not belonging to the team."
                    )
                    continue

                # attribute Lecture topic tasks even if they are a manager
                if "[Lecture Topic Task]" in issue["content"].get("title", ""):
                    sprint.devMetrics[dev].lectureTopicTasksClosed += 1
                if dev not in managers:
                    workedOnlyByManager = False
                if dev in managers:
                    continue  # don't count manager metrics
                sprint.devMetrics[dev].pointsClosed += issueScore / numberAssignees
            if not workedOnlyByManager:
                sprints[sprintIndex].totalPointsClosed += issueScore

        hasAnotherPage = project["items"]["pageInfo"]["hasNextPage"]
        if hasAnotherPage:
            params["nextPage"] = project["items"]["pageInfo"]["endCursor"]
    for sprint in sprints:
        untrimmedAverage = sprint.totalPointsClosed / max(1, len(sprint.devMetrics))
        trimmedAverage = outliersRemovedAverage(
            map(lambda d: d.pointsClosed, sprint.devMetrics.values())
        )
        devBenchmark = max(
            1, min(untrimmedAverage, trimmedAverage) / (milestoneGrade / 100)
        )
        for assignee in milestoneData.developers:
            contribution = sprint.devMetrics[assignee].pointsClosed / max(
                sprint.totalPointsClosed, 1
            )
            sprint.devMetrics[assignee] = DeveloperMetrics(
                pointsClosed=sprint.devMetrics[assignee].pointsClosed,
                percentContribution=contribution * 100.0,
                expectedGrade=min(
                    (sprint.devMetrics[assignee].pointsClosed / devBenchmark)
                    * milestoneGrade,
                    100.0,
                ),
                lectureTopicTasksClosed=sprint.devMetrics[
                    assignee
                ].lectureTopicTasksClosed,
            )
    return milestoneData
