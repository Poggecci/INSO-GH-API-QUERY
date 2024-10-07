from src.utils.queryRunner import run_graphql_query

get_projects_query = """
query QueryProjects($owner: String!, $project_name: String!,  $nextPage: String) {
  organization(login: $owner) {
		projectsV2(query: $project_name, first: 100, after: $nextPage ) {
			nodes {
				title
				number
			}
			pageInfo {
					endCursor
					hasNextPage
			}
		}
  }
}
"""


def get_project_number(*, organization: str, project_name: str) -> int:
    params = {"owner": organization, "project_name": project_name}
    hasAnotherPage = True
    while hasAnotherPage:
        response: dict = run_graphql_query(get_projects_query, params)
        projects: list[dict] = response["data"]["organization"]["projectsV2"]["nodes"]
        for project in projects:
            if project["title"] == project_name:
                return project["number"]
        hasAnotherPage = response["data"]["organization"]["projectsV2"]["pageInfo"][
            "hasNextPage"
        ]
        if hasAnotherPage:
            params["nextPage"] = response["data"]["organization"]["projectsV2"][
                "pageInfo"
            ]["endCursor"]
    raise ValueError(
        "Project not found in org. Likely means the project board"
        " doesn't share the same name as the team."
    )
