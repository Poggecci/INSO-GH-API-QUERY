import json
import logging
from typing import Iterable
from datetime import datetime
from src.utils.constants import pr_tz
from src.utils.issues import (
    calculate_issue_scores,
    parse_issue,
    should_count_issue,
)
from src.utils.models import DeveloperMetrics, MilestoneData, ParsingError
from src.utils.queryRunner import run_graphql_query

# Check out https://docs.github.com/en/graphql/guides/introduction-to-graphql#schema to understand this query better
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
            Urgency: fieldValueByName(name: "Urgency") {
              ... on ProjectV2ItemFieldNumberValue {
                number
              }
            }
            Difficulty: fieldValueByName(name: "Difficulty") {
              ... on ProjectV2ItemFieldNumberValue {
                number
              }
            }
            Modifier: fieldValueByName(name: "Modifier") {
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


def outliersRemovedAverage(scores: Iterable) -> float:
    smallest_elem = min(scores, default=0)
    largestVal = max(scores, default=0)
    newLength = len(list(scores)) - (largestVal != 0) - (smallest_elem != 0)
    total = sum(scores, start=0) - largestVal - smallest_elem
    return total / max(1, newLength)


def getCurrentSprintIndex(date: datetime, cutoffs: list[datetime]):
    sprintIndex = 0
    for cutoff in cutoffs:
        if date > cutoff:
            sprintIndex += 1
    return sprintIndex


def getFormattedSprintDateRange(
    startDate: datetime, endDate: datetime, cutoffs: list[datetime], sprintIndex: int
):
    if len(cutoffs) == 0:
        return f"{startDate.strftime('%Y/%m/%d')}-{endDate.strftime('%Y/%m/%d')}"
    if sprintIndex >= len(cutoffs):
        return f"{cutoffs[-1].strftime('%Y/%m/%d')}-{endDate.strftime('%Y/%m/%d')}"
    if sprintIndex == 0:
        return f"{startDate.strftime('%Y/%m/%d')}-{cutoffs[0].strftime('%Y/%m/%d')}"
    return f"{cutoffs[sprintIndex-1].strftime('%Y/%m/%d')}-{cutoffs[sprintIndex].strftime('%Y/%m/%d')}"


def generateSprintCutoffs(
    *, startDate: datetime, endDate: datetime, sprints: int
) -> list[datetime]:
    if sprints <= 1:
        return []

    total_duration = endDate - startDate
    cutoffs = []

    for i in range(1, sprints):
        fraction = i / sprints
        cutoff_date = startDate + total_duration * fraction
        cutoffs.append(cutoff_date)

    return cutoffs


def getTeamMetricsForMilestone(
    org: str,
    team: str,
    milestone: str,
    members: list[str],
    managers: list[str],
    startDate: datetime,
    endDate: datetime,
    sprints: int,
    minTasksPerSprint: int,
    useDecay: bool,
    milestoneGrade: float,
    shouldCountOpenIssues: bool = False,
    logger: logging.Logger | None = None,
) -> MilestoneData:
    if logger is None:
        logger = logging.getLogger(__name__)
    developers = [member for member in members if member not in managers]
    devPointsClosed = {dev: 0.0 for dev in developers}
    devTasksCompleted = {dev: [0 for _ in range(sprints)] for dev in developers}
    devLectureTopicTasks = {dev: 0 for dev in developers}
    totalPointsClosed = 0.0
    params = {"owner": org, "team": team}
    milestoneData = MilestoneData(sprints=sprints, startDate=startDate, endDate=endDate)
    sprintCutoffs = generateSprintCutoffs(
        startDate=startDate, endDate=endDate, sprints=sprints
    )
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
        for issue_dict in issues:
            try:
                issue = parse_issue(issue_dict=issue_dict)
            except ParsingError:
                # don't log since the root cause can be hard to identify without manual review
                continue
            except KeyError as e:
                logger.exception(
                    f"{e}. GH GraphQL API Issue type may have changed. This requires updating the code. Please contact the maintainers."
                )
            except ValueError as e:
                logger.exception(
                    f"{e}. GH GraphQL API Issue type may have changed. This requires updating the code. Please contact the maintainers."
                )

            if not should_count_issue(
                issue=issue,
                logger=logger,
                currentMilestone=milestone,
                managers=managers,
                shouldCountOpenIssues=shouldCountOpenIssues,
            ):
                continue

            print(f"Successfully validated Issue #{issue.number}")
            issueMetrics = calculate_issue_scores(
                issue=issue,
                managers=managers,
                developers=developers,
                startDate=startDate,
                endDate=endDate,
                useDecay=useDecay,
                logger=logger,
            )
            # attribute base issue points to developer alongside giving them credit for the completed task
            for dev, score in issueMetrics.pointsByDeveloper.items():
                devPointsClosed[dev] += score
                # attribute task completion to appropriate sprint
                taskCompletionDate = (
                    issue.closedAt if issue.closedAt is not None else issue.createdAt
                )
                sprintIndex = getCurrentSprintIndex(taskCompletionDate, sprintCutoffs)
                devTasksCompleted[dev][sprintIndex] += 1
                # update total points closed metric
                totalPointsClosed += score

                # attribute Lecture topic tasks if applicable
                if issue.isLectureTopicTask:
                    devLectureTopicTasks[dev] += 1

            # attribute bonuses for developers
            for dev, bonus in issueMetrics.bonusesByDeveloper.items():
                devPointsClosed[dev] += bonus
                # Note that bonus do not increase the total points closed such as to not "raise the bar"

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
        # check if the developer has completed the minimum tasks up until the current sprint
        # If they haven't thats an automatic zero for that milestone
        currentSprint = getCurrentSprintIndex(
            pr_tz.localize(datetime.today()), sprintCutoffs
        )
        expectedGrade = min(
            (devPointsClosed[dev] / devBenchmark) * milestoneGrade, 100.0
        )
        for sprintIdx in range(currentSprint + 1):
            if devTasksCompleted[dev][sprintIdx] < minTasksPerSprint:
                sprintDateRange = getFormattedSprintDateRange(
                    startDate=startDate,
                    endDate=endDate,
                    cutoffs=sprintCutoffs,
                    sprintIndex=sprintIdx,
                )
                logger.warning(
                    f"{dev} hasn't completed the minimum {minTasksPerSprint} task(s) required for sprint {sprintDateRange}"
                )
                if not shouldCountOpenIssues:
                    expectedGrade = 0.0
        milestoneData.devMetrics[dev] = DeveloperMetrics(
            tasksBySprint=devTasksCompleted[dev],
            pointsClosed=devPointsClosed[dev],
            percentContribution=contribution * 100.0,
            expectedGrade=expectedGrade,
            lectureTopicTasksClosed=devLectureTopicTasks[dev],
        )
    return milestoneData
