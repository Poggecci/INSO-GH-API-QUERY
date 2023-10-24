from getTeamMembers import get_team_members
from utils.models import DeveloperMetrics, MilestoneData
from datetime import datetime
from utils.queryRunner import run_graphql_query


get_team_issues = """
query QueryProjectItemsForTeam($owner: String!, $team: String!, $nextPage: String)
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
    org: str, team: str, milestone: str, members: list[str], 
    managers: list[str], startDate: datetime, endDate: datetime
) -> MilestoneData:
    exponentialRatio = 1/(endDate-startDate).days
    milestoneData = MilestoneData()
    milestoneData.devMetrics = {member: DeveloperMetrics() for member in members}
    params = {"owner": org, "team": team}
    hasAnotherPage = True
    while hasAnotherPage:
        response = run_graphql_query(get_team_issues, params)
        projects: list[dict] = response["data"]["organization"]["projectsV2"]["nodes"]
        project = next(filter(lambda x: x["title"] == team, projects), None)
        if not project:
            raise Exception(
                "Project not found in org. Likely means the project board doesn't share the same name as the team."
            )
        ### Extract data
        issues = project["items"]["nodes"]
        for issue in issues:
            # don't count open issues
            if not issue["content"].get("closed", False):
                continue
            if issue["content"].get("milestone", None) is None:
                continue
            if issue["difficulty"] is None or issue["urgency"] is None:
                continue
            if issue["content"]["milestone"]["title"] != milestone:
                continue
            workedOnlyByManager = True
            # attribute points to correct developer
            for dev in issue["content"]["assignees"]["nodes"]:
                try:
                    if dev["login"] not in members:
                        raise Exception(
                            "Task assigned to developer not belonging to the team"
                        )
                except Exception as e:
                    print(e)
                    continue
                if dev["login"] not in managers:
                    workedOnlyByManager = False
                if dev["login"] in managers:
                    continue  # don't count manager metrics
                # P = Po(1-r)^t
                # Po = initial point value
                # r = 1/<how many days to complete milestone>
                # t = <amount of days from when issue was created vs the start date of milestone>
                createdAt = datetime.fromisoformat(issue["content"]["createdAt"])
                timePower = createdAt - startDate
                milestoneData.devMetrics[dev["login"]].pointsClosed += (
                    (issue["difficulty"]["number"] * issue["urgency"]["number"])*pow(1-exponentialRatio, timePower.days)
                )
            if not workedOnlyByManager:
                milestoneData.totalPointsClosed += (
                    (issue["difficulty"]["number"] * issue["urgency"]["number"])*pow(1-exponentialRatio, timePower.days)
                )

        hasAnotherPage = project["items"]["pageInfo"]["hasNextPage"]
        if hasAnotherPage:
            params["nextPage"] = project["items"]["pageInfo"]["endCursor"]

    for member in members:
        pointsClosed = milestoneData.devMetrics[member].pointsClosed
        milestoneData.devMetrics[member].percentContribution = (
            pointsClosed / milestoneData.totalPointsClosed * 100
        )
    return milestoneData


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        exit(0)
    _, org, milestone, *_ = sys.argv
    # idk why this isn't working, so hardcode for now. Kinda had to anyway cuz managers are hard coded rn
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
