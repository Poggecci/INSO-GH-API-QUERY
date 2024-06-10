from src.utils.models import LectureTopicTaskData

from src.utils.queryRunner import run_graphql_query

get_team_lecture_topic_tasks = """
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
                title
                createdAt
                closed
                assignees(first:20) {
                  nodes{
                    login
                  }
                }
              }
            }
          }   
        }
      }
    }
  }
}

"""


def getLectureTopicTaskMetrics(
    org: str, team: str, members: list[str]
) -> LectureTopicTaskData:
    lectureTopicTaskData = LectureTopicTaskData()
    lectureTopicTaskData.lectureTopicTasksByDeveloper = {
        member: 0 for member in members
    }

    params = {"owner": org, "team": team}
    hasAnotherPage = True
    while hasAnotherPage:
        response = run_graphql_query(get_team_lecture_topic_tasks, params)
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
            # Expect LTTs to be properly titled as such
            if "[Lecture Topic Task]" not in issue["content"].get("title", ""):
                continue
            lectureTopicTaskData.totalLectureTopicTasks += 1
            for dev in issue["content"]["assignees"]["nodes"]:
                if dev["login"] not in members:
                    raise Exception(
                        f"Task assigned to developer {dev['login']} not"
                        " belonging to the team"
                    )
                lectureTopicTaskData.lectureTopicTasksByDeveloper[dev["login"]] += 1

        hasAnotherPage = project["items"]["pageInfo"]["hasNextPage"]
        if hasAnotherPage:
            params["nextPage"] = project["items"]["pageInfo"]["endCursor"]

    return lectureTopicTaskData
