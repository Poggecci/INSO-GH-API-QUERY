import json
from getTeamMembers import get_team_members
from utils.models import DeveloperMetrics, MilestoneData
from datetime import datetime
from utils.queryRunner import run_graphql_query

get_team_issues = """
query QueryProjectItemsForTeam($owner: String!, $team: String!,
                               $nextPage: String) {
  organization(login: $owner) {
    projectsV2(query: $team, first: 100) {
      nodes{
        title
        items(first: 100, after: $nextPage) {
          pageInfo {
            endCursor
            hasNextPage
          }
          nodes {
            content {
              ... on Issue {
                createdAt
                closed
                milestone {
                  title
                }
                assignees(first:20) {
                  nodes{
                    login
                  }
                }
              }
            }
            urgency: fieldValueByName(name:"Urgency") {
              ... on ProjectV2ItemFieldNumberValue {
                number
              }
            }
            difficulty: fieldValueByName(name:"Difficulty") {
              ... on ProjectV2ItemFieldNumberValue {
                number
              }
            }
            modifier: fieldValueByName(name:"Modifier") {
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


# Expects each score to be [0,inf)
def outliersRemovedAverage(scores: list) -> float:
    non_zero_lst = [x for x in scores if x > 0]
    smallest_non_zero = min(non_zero_lst, default=0)
    largestVal = max(scores, default=0)
    newLength = len(scores) - (largestVal != 0) - (smallest_non_zero != 0)
    total = sum(scores) - largestVal - smallest_non_zero
    return total / newLength


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
) -> MilestoneData:
    developers = [member for member in members if member not in managers]
    devPointsClosed = {dev: 0.0 for dev in developers}
    totalPointsClosed = 0.0
    params = {"owner": org, "team": team}
    hasAnotherPage = True
    while hasAnotherPage:
        response = run_graphql_query(get_team_issues, params)
        projects: list[dict] = response["data"]["organization"]["projectsV2"]["nodes"]
        project = next(filter(lambda x: x["title"] == team, projects), None)
        if not project:
            raise Exception(
                "Project not found in org. Likely means the project board"
                " doesn't share the same name as the team."
            )
        # Extract data
        issues = project["items"]["nodes"]
        for issue in issues:
            # don't count open issues
            if not issue["content"].get("closed", False):
                continue
            if issue["content"].get("milestone", None) is None:
                continue
            if issue["difficulty"] is None or issue["urgency"] is None:
                continue
            if not issue["difficulty"] or not issue["urgency"]:
                continue
            if issue["content"]["milestone"]["title"] != milestone:
                continue
            if issue["modifier"] is None or not issue["modifier"]:
                issue["modifier"] = {"number": 0}
            workedOnlyByManager = True
            # attribute points to correct developer
            numberAssignees = len(issue["content"]["assignees"]["nodes"])
            print(issue)
            for dev in issue["content"]["assignees"]["nodes"]:
                try:
                    if dev["login"] not in developers:
                        raise Exception(
                            f"Task assigned to developer {dev['login']} not"
                            " belonging to the team"
                        )
                except Exception as e:
                    print(e)
                    continue
                if dev["login"] not in managers:
                    workedOnlyByManager = False
                if dev["login"] in managers:
                    continue  # don't count manager metrics
                createdAt = datetime.fromisoformat(issue["content"]["createdAt"])
                issueScore = (
                    issue["difficulty"]["number"]
                    * issue["urgency"]["number"]
                    * (decay(startDate, endDate, createdAt) if useDecay else 1)
                    + issue["modifier"]["number"]
                )
                devPointsClosed[dev["login"]] += issueScore / numberAssignees
            if not workedOnlyByManager:
                totalPointsClosed += issueScore

        hasAnotherPage = project["items"]["pageInfo"]["hasNextPage"]
        if hasAnotherPage:
            params["nextPage"] = project["items"]["pageInfo"]["endCursor"]

    untrimmedAverage = totalPointsClosed / len(devPointsClosed)
    trimmedAverage = outliersRemovedAverage(devPointsClosed.values())
    devBenchmark = min(untrimmedAverage, trimmedAverage) / (milestoneGrade / 100)
    milestoneData = MilestoneData()
    milestoneData.totalPointsClosed = totalPointsClosed
    for dev in developers:
        contribution = devPointsClosed[dev] / totalPointsClosed
        milestoneData.devMetrics[dev] = DeveloperMetrics(
            pointsClosed=devPointsClosed[dev],
            percentContribution=contribution * 100.0,
            expectedGrade=min((devPointsClosed[dev] / devBenchmark) * milestoneGrade, 100.0),
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
        print(getTeamMetricsForMilestone(
            org=organization,
            team=team,
            milestone=teamdata["milestone"],
            milestoneGrade=teamdata["milestoneGrade"],
            members=members,
            managers=teamdata["managers"],
            startDate=startDate,
            endDate=endDate,
            useDecay=useDecay,
        ))