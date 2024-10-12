from src.utils.queryRunner import runGraphqlQuery

get_teams_query = """
query QueryClassroomTeams($owner: String!) {
  organization(login: $owner) {
    teams(first: 100, userLogins: ["github-classroom"]) {
      nodes {
        name
        slug
      }
    }
  }
}
"""


def getTeams(organization: str) -> list[str]:
    params = {"owner": organization}
    response = runGraphqlQuery(query=get_teams_query, variables=params)
    teams = response["data"]["organization"]["teams"]["nodes"]
    print([team["name"] for team in teams])
    return [team["name"] for team in teams]
