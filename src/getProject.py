import logging
from src.utils.queryRunner import runGraphqlQuery

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


def getProjectNumber(
    *, organization: str, project_name: str, logger: logging.Logger | None = None
) -> int:
    if not logger:
        logger = logging.getLogger()
    params = {"owner": organization, "project_name": project_name}
    hasAnotherPage = True
    while hasAnotherPage:
        response: dict = runGraphqlQuery(query=get_projects_query, variables=params)
        projects: list[dict] = response["data"]["organization"]["projectsV2"]["nodes"]
        for project in projects:
            if project["title"] == project_name:
                logger.info(f"Found project: {project}")
                return project["number"]
        hasAnotherPage = response["data"]["organization"]["projectsV2"]["pageInfo"][
            "hasNextPage"
        ]
        if hasAnotherPage:
            params["nextPage"] = response["data"]["organization"]["projectsV2"][
                "pageInfo"
            ]["endCursor"]
    raise ValueError(
        f"Project Board with name {project_name} not found in organization. Ensure that all"
        " the team's issues are listed in a board with this *exact* name."
    )
