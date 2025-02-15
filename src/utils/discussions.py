from collections.abc import Iterator
from datetime import datetime, timedelta
import logging
from typing import Any, Callable
from src.utils.models import Category, Discussion, DiscussionComment, ParsingError
from src.utils.queryRunner import runGraphqlQuery


team_scrum_prep_discussions_query = """
query QueryScrumPrepForTeam (
  $owner: String!, 
  $team: String!,
  $category: ID,
  $cursor: String) {
    organization(login: $owner) {
        teams(query: $team, first: 1) {
            nodes {
                repositories(first: 1) {
                    nodes {
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
        }
    }
}
"""


def parseDiscussion(*, discussion_dict: dict) -> Discussion:
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
        TypeError: If certain fields declared non-nullable by the API aren't present.
            (this likely means the API has changed and thus the parsing code must be updated)
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


def getDiscussionDicts(
    *, org: str, team: str, category: int | None = None
) -> Iterator[dict]:
    """
    Retrieves GitHub discussion data through GraphQL API as an iterator of dictionaries.

    This function makes paginated GraphQL queries to fetch all discussions from a GitHub repository.
    It yields each discussion's raw dictionary data one at a time to conserve memory.

    Args:
        org (str): GitHub organization name
        team (str): Name of the team within the organization
        category (int | None): Optional category ID to filter discussions

    Returns:
        Iterator[dict]: An iterator yielding dictionaries containing raw discussion data
                       from the GitHub GraphQL API

    Raises:
        GraphQLError: If the API request fails or returns an error
        ValueError: If organization or repository parameters are invalid

    Examples:
        >>> discussions = getDiscussionDicts(org="myorg", team="myteam")
        >>> first_discussion = next(discussions)
        >>> print(first_discussion["title"])
    """
    params: dict[str, Any] = {"owner": org, "team": team}
    if category is not None:
        params["category"] = category
    hasAnotherPage = True
    while hasAnotherPage:
        response: dict = runGraphqlQuery(
            query=team_scrum_prep_discussions_query, variables=params
        )
        discussion_info: dict = response["organization"]["teams"]["nodes"][0][
            "repositories"
        ]["nodes"][0]["discussions"]
        discussion_dicts: list[dict] = discussion_info["nodes"]
        yield from discussion_dicts

        hasAnotherPage = discussion_info["pageInfo"]["hasNextPage"]
        if hasAnotherPage:
            params["cursor"] = discussion_info["pageInfo"]["endCursor"]


def getDiscussions(
    *, org: str, team: str, category: int | None = None
) -> list[Discussion]:
    """
    Retrieves and parses all GitHub discussions from a repository into Discussion objects.

    Acts as a high-level wrapper around getDiscussionDicts(), converting the raw dictionary
    data into properly structured Discussion objects.

    Args:
        org (str): GitHub organization name
        team (str): Name of the team within the organization
        category (int | None): Optional category ID to filter discussions

    Returns:
        list[Discussion]: List of parsed Discussion objects containing all discussion data

    Raises:
        ParsingError: If discussion data cannot be parsed correctly
        GraphQLError: If the API request fails or returns an error
        ValueError: If organization or repository parameters are invalid

    Examples:
        >>> discussions = getDiscussions(org="myorg", repository="myrepo")
        >>> print(discussions[0].title)
        >>> print(len(discussions[0].comments))
    """
    return [
        parseDiscussion(discussion_dict=d)
        for d in getDiscussionDicts(org=org, team=team, category=category)
    ]


def getWeekIndex(
    *, dateOfInterest: datetime, milestoneStart: datetime, milestoneEnd: datetime
) -> int:
    """
    Calculates the week index of a date relative to milestone boundaries.

    Returns the zero-based index of the week containing the date of interest, where week 0
    is the partial week from milestone start to first Sunday. Returns -1 if the date falls
    outside the milestone boundaries.

    Args:
        dateOfInterest (datetime): The date to find the week index for
        milestoneStart (datetime): Start date of the milestone period
        milestoneEnd (datetime): End date of the milestone period

    Returns:
        int: Week index (0-based) of the date, or -1 if date is outside milestone bounds

    Examples:
        >>> start = datetime(2024, 1, 1)  # Monday
        >>> end = datetime(2024, 1, 31)
        >>> date = datetime(2024, 1, 8)  # Next Monday
        >>> print(getWeekIndex(dateOfInterest=date,
        ...                   milestoneStart=start,
        ...                   milestoneEnd=end))
        1
    """
    if dateOfInterest < milestoneStart or dateOfInterest > milestoneEnd:
        return -1
    # Get the weekday of milestoneStart (Monday is 0, Sunday is 6)
    startWeekday = milestoneStart.weekday()
    # Find the first Sunday after milestoneStart
    firstSunday = milestoneStart + timedelta(days=(6 - startWeekday))
    if dateOfInterest <= firstSunday:
        return 0
    # Calculate the start of the first full week (the Monday after the first Sunday)
    firstFullWeekStart = firstSunday + timedelta(days=1)
    daysSinceFirstFullWeek = (dateOfInterest - firstFullWeekStart).days
    # Week index is the number of full weeks passed after week 0
    weekIndex = daysSinceFirstFullWeek // 7 + 1
    return weekIndex


def findWeeklyDiscussionParticipation(
    *,
    members: set[str],
    discussions: list[Discussion],
    milestone: str,
    milestoneStart: datetime,
    milestoneEnd: datetime,
) -> dict[str, set[int]]:
    """
    Tracks weekly participation of team members in GitHub discussions.

    Analyzes both discussion creation and comments to build a map of which weeks
    each team member participated in discussions during a milestone period.

    Args:
        members (set[str]): Set of team member GitHub usernames
        discussions (list[Discussion]): List of Discussion objects to analyze
        milestone (str): Name of current milestone
        milestoneStart (datetime): Start date of the milestone period
        milestoneEnd (datetime): End date of the milestone period

    Returns:
        dict[str, set[int]]: Dictionary mapping team member usernames to sets of week
                            indices in which they participated

    Examples:
        >>> members = {"alice", "bob"}
        >>> participation = findWeeklyDiscussionParticipation(
        ...     members=members,
        ...     discussions=discussions,
        ...     milestone="Milestone 1",
        ...     milestoneStart=datetime(2024, 1, 1),
        ...     milestoneEnd=datetime(2024, 1, 31)
        ... )
        >>> print(participation["alice"])  # Weeks alice participated
        {0, 1, 2}
    """
    filteredDiscussions = filter(
        lambda d: f"Scrum Prep {milestone} - Week {getWeekIndex(dateOfInterest=d.publishedAt, milestoneStart=milestoneStart, milestoneEnd=milestoneEnd) + 1}"
        == d.title,
        discussions,
    )
    participation = {member: set() for member in members}
    for discussion in filteredDiscussions:
        # attribute the discussion to the author if appropriate
        discussionWeek = getWeekIndex(
            dateOfInterest=discussion.publishedAt,
            milestoneStart=milestoneStart,
            milestoneEnd=milestoneEnd,
        )
        if discussionWeek != -1 and discussion.author in members:
            participation[discussion.author].add(discussionWeek)
        # attribute participation for the comments as well
        for comment in discussion.comments:
            commentWeek = getWeekIndex(
                dateOfInterest=comment.publishedAt,
                milestoneStart=milestoneStart,
                milestoneEnd=milestoneEnd,
            )
            if discussionWeek != -1 and comment.author in members:
                participation[comment.author].add(commentWeek)

    return participation


def calculateWeeklyDiscussionPenalties(
    participation: dict[str, set[int]], weeks: int
) -> dict[str, float]:
    """
    Penalties for team members based on their weekly discussion activity.

    Penalties start at 0 and are incremented based on missed weeks. Each missed week incurs a base
    penalty, with additional penalties for consecutive missed weeks. Consecutive miss penalties
    do not apply to the first missed week in a sequence. Penalties are meant to be subtracted from
    a score of 100.

    Args:
        participation (dict[str, set[int]]): Dictionary mapping member names to sets of week
                                           indices in which they participated
        weeks (int): Total number of weeks in the scoring period

    Returns:
        dict[str, float]: Dictionary mapping member names to their total penalties

    Examples:
        >>> participation = {
        ...     "alice": {0, 1, 2, 3},  # Perfect participation
        ...     "bob": {0, 2},          # Missed weeks 1 and 3
        ...     "charlie": {3}          # Missed weeks 0, 1, 2
        ... }
        >>> penalties = scoreWeeklyDiscussionParticipation(participation, weeks=4)
        >>> print(scores["alice"])  # Perfect attendance means no penalties
        0.0
        >>> print(scores["charlie"])  # missed thrice consecutively so 2 + (2+1) + (2+1+1)
        9.0
    """
    penaltyPerMissedWeek = 2  # 2 points deducted from milestone grade
    consecutiveMissesPenalty = 1  # additional penalty per consecutive miss after first

    penalties = {}

    for member, participated_weeks in participation.items():
        penalty = 0.0
        consecutive_misses = 0

        for week in range(weeks):
            if week not in participated_weeks:
                penalty += penaltyPerMissedWeek
                consecutive_misses += 1
                penalty += (consecutive_misses - 1) * consecutiveMissesPenalty
            else:
                consecutive_misses = 0
        # Ensure penalty doesn't exceed 100
        penalties[member] = min(100, penalty)

    return penalties


def getWeeks(milestoneStart: datetime, milestoneEnd: datetime):
    # Get the total number of weeks within the milestone
    return (
        getWeekIndex(
            dateOfInterest=milestoneEnd,
            milestoneStart=milestoneStart,
            milestoneEnd=milestoneEnd,
        )
        + 1
    )
