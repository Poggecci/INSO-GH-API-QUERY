import json
import logging
from typing import Iterable
from datetime import datetime
from src.utils.constants import pr_tz
from src.getTeamMembers import get_team_members
from src.utils.models import DeveloperMetrics, MilestoneData
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
    startDate: datetime, endDate: datetime, sprints: int
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
    sprintCutoffs = generateSprintCutoffs(startDate, endDate, sprints)
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
                closedByList = issue["content"]["timelineItems"]["nodes"]
                closedBy = closedByList[-1]["actor"]["login"]
                if closedBy not in managers:
                    logger.warning(
                        f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) was closed by non-manager {closedBy}. Only issues closed by managers are accredited. Managers for this project are: {managers}"
                    )
                    continue

            elif not shouldCountOpenIssues:
                continue
            if issue["Difficulty"] is None or issue["Urgency"] is None:
                logger.warning(
                    f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) does not have the Urgency and/or Difficulty fields populated"
                )
                continue
            if not issue["Difficulty"] or not issue["Urgency"]:
                logger.warning(
                    f"[Issue #{issue['content'].get('number')}]({issue['content'].get('url')}) does not have the Urgency and/or Difficulty fields populated"
                )
                continue

            if issue["Modifier"] is None or not issue["Modifier"]:
                issue["Modifier"] = {"number": 0}
            workedOnlyByManager = True
            numberAssignees = len(issue["content"]["assignees"]["nodes"])
            print(issue)
            createdAt = datetime.fromisoformat(issue["content"]["createdAt"])
            issueScore = (
                issue["Difficulty"]["number"]
                * issue["Urgency"]["number"]
                * (decay(startDate, endDate, createdAt) if useDecay else 1)
                + issue["Modifier"]["number"]
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
                # attribute task completion to appropriate sprint
                closedAt = None
                if issue["content"]["closedAt"] is not None:
                    closedAt = datetime.fromisoformat(issue["content"]["closedAt"])
                taskCompletionDate = closedAt if closedAt is not None else createdAt
                sprintIndex = getCurrentSprintIndex(taskCompletionDate, sprintCutoffs)
                devTasksCompleted[dev["login"]][sprintIndex] += 1
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
                    f"{dev} didn't complete the minimum {minTasksPerSprint} task(s) required for sprint {sprintDateRange}"
                )
                expectedGrade = 0.0
        milestoneData.devMetrics[dev] = DeveloperMetrics(
            tasksBySprint=devTasksCompleted[dev],
            pointsClosed=devPointsClosed[dev],
            percentContribution=contribution * 100.0,
            expectedGrade=expectedGrade,
            lectureTopicTasksClosed=devLectureTopicTasks[dev],
        )
    return milestoneData
