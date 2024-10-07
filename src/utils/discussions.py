from collections.abc import Iterator
from datetime import datetime
from typing import Any
from src.utils.models import Category, Discussion, DiscussionComment, ParsingError
from src.utils.queryRunner import run_graphql_query


team_scrum_prep_discussions_query = """
query QueryScrumPrepForTeam (
  $owner: String!, 
  $repositoryName: String!,
  $category: ID,
  $cursor: String) {
    organization(login: $owner) {
        repository(name: $repositoryName) {
            discussions(first: 100, categoryId: $category, after: $cursor) {
                pageInfo {
                    hasNextPage
                    endCursor
                }
                nodes {
                    author {
                        login
                    }
                    title    
                    body
                    category{
                        id
                        name
                    }
                    comments(first: 100) {
                        nodes {
                            author {
                                login
                            }
                            publishedAt
                            body
                        }
                    }
                    publishedAt
                }
            }
        }
    }
}
"""


def parse_discussion(*, discussion_dict: dict) -> Discussion:
    """
    Parses a dictionary representing a GitHub Discussion fetched through the GraphQL API and returns a Discussion object.

    Args:
        discussion_dict (dict): The dictionary containing the details of the GitHub discussion, typically retrieved from the API.
                                This dictionary is expected to have a specific structure with fields like 'publishedAt',
                                'title', 'body', 'category', 'comments', etc.

    Returns:
        Discussion: An instance of the Discussion dataclass populated with all the relevant discussion details such as
                    author, title, body, category, comments, and published time.

    Raises:
        ParsingError: If required fields are missing or empty.
        ValueError: If date formatting for 'publishedAt' fails.
    """
    # Validate required fields for parsing
    if not isinstance(discussion_dict, dict) or len(discussion_dict) < 1:
        raise ParsingError(
            "Missing, empty, or incorrectly typed discussion data. This could be due to permission errors or API changes."
        )

    # Extract the fields
    author = discussion_dict["author"]["login"]
    title: str = discussion_dict["title"]
    body: str = discussion_dict["body"]
    published_at = datetime.fromisoformat(discussion_dict["publishedAt"])

    # Extract category
    category_dict = discussion_dict["category"]
    category = Category(id=category_dict["id"], name=category_dict["name"])

    # Extract comments
    comments = [
        DiscussionComment(
            author=comment["author"]["login"] if comment["author"] else "Unknown",
            body=comment["body"],
            publishedAt=datetime.fromisoformat(comment["publishedAt"]),
        )
        for comment in discussion_dict["comments"]["nodes"]
    ]

    # Return the populated Discussion dataclass
    return Discussion(
        author=author,
        title=title,
        body=body,
        category=category,
        comments=comments,
        publishedAt=published_at,
    )


def get_discussion_dicts(
    *, org: str, repository: str, category: int | None = None
) -> Iterator[dict]:
    params: dict[str, Any] = {"owner": org, "repositoryName": repository}
    if category is not None:
        params["category"] = category
    hasAnotherPage = True
    while hasAnotherPage:
        response: dict = run_graphql_query(team_scrum_prep_discussions_query, params)
        discussion_dicts: list[dict] = response["data"]["organization"]["repository"][
            "discussions"
        ]["nodes"]
        yield from discussion_dicts

        hasAnotherPage = response["data"]["organization"]["repository"]["discussions"][
            "pageInfo"
        ]["hasNextPage"]
        if hasAnotherPage:
            params["cursor"] = response["data"]["organization"]["repository"][
                "discussions"
            ]["pageInfo"]["endCursor"]


def get_discussions(
    *, org: str, repository: str, category: int | None = None
) -> list[Discussion]:
    return [
        parse_discussion(discussion_dict=d)
        for d in get_discussion_dicts(org=org, repository=repository, category=category)
    ]
