import logging
from src.utils.milestones import parseMilestone
from src.utils.models import Milestone
from src.utils.queryRunner import runGraphqlQuery


get_milestones_query = """
query GetRepositoryMilestones($org: String!, $team: String!) {
  organization(login: $org) {
    teams(query: $team, first: 1) {
      nodes{
        repositories(first: 100) {
          nodes {
            milestones(first: 100) {
              nodes {
                url
                title
                dueOn
              }
            }
          }
        }
      }
    }
  }
}
"""


def getMilestones(*, organization: str, team: str) -> list[Milestone]:
    """
    Retrieve all milestones from repositories belonging to a team in an organization.

    Args:
        organization (str): The GitHub organization name. Keyword-only argument.
        team (str): The team slug within the organization. Keyword-only argument.

    Returns:
        list[Milestone]: List of Milestone objects containing milestone information.

    Raises:
        KeyError: If the response doesn't contain the expected data structure.
        ParsingError: If the milestone objects in the API response have an unknown structure.
    """
    params = {"org": organization, "team": team}
    milestones = []
    response: dict = runGraphqlQuery(query=get_milestones_query, variables=params)
    repositories = response["organization"]["teams"]["nodes"][0]["repositories"][
        "nodes"
    ]
    for repo in repositories:
        # Get milestones for current repository
        repo_milestones = repo["milestones"]["nodes"]
        for milestone_data in repo_milestones:
            milestones.append(parseMilestone(milestone_data))
    return milestones
