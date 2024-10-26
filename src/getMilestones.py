import logging
from src.utils.milestones import parseMilestone
from src.utils.models import Milestone
from src.utils.queryRunner import runGraphqlQuery


get_milestones_query = """
query GetRepositoryMilestones($org: String!, $repo: String!, $nextPage: String) {
    organization(login: $org) {
        repository(name: $repo) {
            milestones(first: 100, after: $nextPage) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    title
                    url
                }
            }
        }
    }
}
"""


def getMilestones(*, organization: str, repository: str) -> list[Milestone]:
    params = {"org": organization, "repo": repository}
    hasAnotherPage = True
    milestones = []
    while hasAnotherPage:
        response: dict = runGraphqlQuery(query=get_milestones_query, variables=params)
        milestone_dicts: list[dict] = response["data"]["organization"]["repository"][
            "milestones"
        ]["nodes"]
        milestones.extend(map(parseMilestone, milestone_dicts))
        hasAnotherPage = response["data"]["organization"]["repository"]["milestones"][
            "pageInfo"
        ]["hasNextPage"]
        if hasAnotherPage:
            params["nextPage"] = response["data"]["organization"]["repository"][
                "milestones"
            ]["pageInfo"]["endCursor"]
    return milestones
