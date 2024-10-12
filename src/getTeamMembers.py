from src.utils.queryRunner import runGraphqlQuery

member_fetching_query = """
query GetTeamMembers($owner: String!, $team: String!) {
  organization(login: $owner){
    teams(query: $team, first:1){
      nodes{
        members {
          nodes{
            login
          }
        }
      }
    }
  }
}
"""


def getTeamMembers(organization, team) -> list[str]:
    params = {"owner": organization, "team": team}
    response = runGraphqlQuery(member_fetching_query, params)
    teams = response["data"]["organization"]["teams"]["nodes"]
    if len(teams) < 1:
        return []
    return [member["login"] for member in teams[0]["members"]["nodes"]]


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        exit(0)
    _, org, team, *_ = sys.argv
    print(getTeamMembers(org, team))
