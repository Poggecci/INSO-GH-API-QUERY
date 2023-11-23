from getTeamMembers import get_team_members
from utils.models import DeveloperMetrics, MilestoneData

from utils.queryRunner import run_graphql_query

get_team_issues = """
query QueryProjectItemsForTeam($owner: String!, $team: String!,
  $nextPage: String)
{
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
          }
        }
      }
    }
  }
}

"""


def getTeamMetricsForMilestone(
    org: str, team: str, milestone: str, members: list[str], managers: list[str]
) -> MilestoneData:
    developers = [member for member in members if member not in managers]
    devPointsClosed = {dev: 0.0 for dev in developers}
    params = {"owner": org, "team": team}
    hasAnotherPage = True
    while hasAnotherPage:
        response = run_graphql_query(get_team_issues, params)
        projects: list[dict] = response["data"]["organization"]["projectsV2"]["nodes"]
        project = next(filter(lambda x: x["title"] == team, projects), None)
        if not project:
            raise Exception(
                "Project not found in org. Likely means the project"
                " board doesn't share the same name as the team."
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
            # attribute points to correct developer
            numberAssignees = len(issue["content"]["assignees"]["nodes"])
            for dev in issue["content"]["assignees"]["nodes"]:
                if dev["login"] not in members:
                    raise Exception(
                        f"Task assigned to developer {dev['login']} not"
                        " belonging to the team"
                    )
                if dev["login"] in managers:
                    continue  # don't count manager metrics
                devPointsClosed[dev["login"]] += (
                    issue["difficulty"]["number"]
                    * issue["urgency"]["number"]
                    / numberAssignees
                )

        hasAnotherPage = project["items"]["pageInfo"]["hasNextPage"]
        if hasAnotherPage:
            params["nextPage"] = project["items"]["pageInfo"]["endCursor"]
    trimmedList = sorted(devPointsClosed.values())[1:-1]
    trimmedMeanPointsClosed = sum(trimmedList) / len(trimmedList)
    totalPointsClosed = sum(devPointsClosed.values())
    milestoneData = MilestoneData()
    for dev in developers:
        milestoneData.devMetrics[dev] = DeveloperMetrics(
            pointsClosed=devPointsClosed[dev],
            percentContribution=devPointsClosed[dev] / totalPointsClosed * 100.0,
            expectedGrade=min(
                devPointsClosed[dev] / trimmedMeanPointsClosed * 100.0, 100.0
            ),
        )
    return milestoneData


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        exit(0)
    _, org, milestone, *_ = sys.argv
    # idk why this isn't working, so hardcode for now.
    # Kinda had to anyway cuz managers are hard coded rn
    # teams = get_teams(org)
    teams_and_managers = {"College Toolbox": ["EdwinC1339", "Ryan8702"]}

    for team, managers in teams_and_managers.items():
        print(f"Team: {team}")
        print(f"Managers: {managers}")
        members = get_team_members(org, team)
        print(
            getTeamMetricsForMilestone(
                org=org,
                team=team,
                milestone=milestone,
                members=members,
                managers=managers,
            )
        )
