from src.utils.models import Project
from src.utils.project import parseProject
from src.utils.queryRunner import runGraphqlQuery

get_projects_query = """
query QueryProjects($owner: String!, $project_name: String!,  $nextPage: String) {
  organization(login: $owner) {
		projectsV2(query: $project_name, first: 100, after: $nextPage ) {
			nodes {
				title
				number
                public
                url
			}
			pageInfo {
                endCursor
                hasNextPage
			}
		}
  }
}
"""


def getProject(*, organization: str, project_name: str) -> Project:
    params = {"owner": organization, "project_name": project_name}
    hasAnotherPage = True
    while hasAnotherPage:
        response: dict = runGraphqlQuery(query=get_projects_query, variables=params)
        project_dicts: list[dict] = response["organization"]["projectsV2"]["nodes"]
        for project_dict in project_dicts:
            project = parseProject(project_dict)
            if project.name == project_name:
                return project
        hasAnotherPage = response["organization"]["projectsV2"]["pageInfo"][
            "hasNextPage"
        ]
        if hasAnotherPage:
            params["nextPage"] = response["organization"]["projectsV2"]["pageInfo"][
                "endCursor"
            ]
    raise ValueError(
        f"Project Board with name {project_name} not found in organization. Ensure that all"
        " the team's issues are listed in a board with this *exact* name."
    )
