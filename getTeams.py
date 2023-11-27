from utils.queryRunner import run_graphql_query

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


def get_teams(organization: str) -> list[str]:
    params = {"owner": organization}
    response = run_graphql_query(get_teams_query, params)
    teams = response['data']['organization']['teams']['nodes']
    print([team['name'] for team in teams])
    return [team['name'] for team in teams]
