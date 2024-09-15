from collections import defaultdict
from datetime import datetime
import logging
from src.utils.models import (
    Comment,
    IssueMetrics,
    ParsingError,
    Reaction,
    ReactionKind,
    Issue,
)


def parse_issue(*, issue_dict: dict) -> Issue:
    """
    Parses a dictionary representing a GitHub Issue fetched through the GraphQL API and returns an Issue object.

    Args:
        issue_dict (dict): The dictionary containing the details of the GitHub issue, typically retrieved from the API.
                           This dictionary is expected to have a specific structure with fields like 'content', 'url',
                           'number', 'title', 'author', 'assignees', 'reactions', 'comments', etc.

    Returns:
        Issue: An instance of the Issue dataclass populated with all the relevant issue details such as title, author,
               created/closed times, assignees, reactions, comments, urgency, difficulty, and modifier values.

    Raises:
        ParsingError: If the structure of the issue_dict does not match the expected format, either due to missing fields
                      or permission errors. Specific errors include:
                      - Missing or incorrect 'content' field.
                      - KeyError for required fields such as 'url', 'number', 'title', 'createdAt', etc.
                      - ValueError if date formatting for 'createdAt' or 'closedAt' fails.
    """
    # Note that project scoped fields are not tied to the issue content!
    urgency: float | None = None
    if issue_dict["Urgency"] is not None:
        urgency = float(issue_dict["Urgency"]["number"])
    difficulty: float | None = None
    if issue_dict["Difficulty"] is not None:
        difficulty = float(issue_dict["Difficulty"]["number"])

    modifier: float | None = None
    if issue_dict["Modifier"] is not None:
        modifier = float(issue_dict["Modifier"]["number"])

    # Validate required fields for parsing
    content = issue_dict["content"]
    if content is None or not isinstance(content, dict) or len(content) < 1:
        raise ParsingError(
            "Missing, empty, or incorrectly typed 'content' field in issue data. This has many causes: the issue gathered was a draft, the PAT lacks permissions, the API changed, etc."
        )
    # Extract the fields declared non-nullable by the GH API
    url: str = content["url"]
    number = content["number"]
    title: str = content["title"]
    author: str = content["author"]
    createdAt = datetime.fromisoformat(content["createdAt"])
    closed = content["closed"]
    assignees = [
        assignee_dict["login"] for assignee_dict in content["assignees"]["nodes"]
    ]
    # Currently, we only search for reactions and comments with HOORAY 🎉
    reactions = [
        Reaction(user_login=reaction["user"]["login"], kind=ReactionKind.HOORAY)
        for reaction in content["reactions"]["nodes"]
    ]
    comments = [
        Comment(
            author_login=comment["author"]["login"],
            reactions=[
                Reaction(user_login=r["user"]["login"], kind=ReactionKind.HOORAY)
                for r in comment["reactions"]["nodes"]
            ],
        )
        for comment in content["comments"]["nodes"]
    ]

    # Extract the nullable fields
    closedAt = None
    if content["closedAt"] is not None:
        closedAt = datetime.fromisoformat(str(content["closedAt"]))

    closedBy = None
    if len(content["timelineItems"]["nodes"]) > 0:
        closedBy = content["timelineItems"]["nodes"][-1]["actor"]["login"]

    milestone: str | None = None
    if content["milestone"] is not None:
        milestone = str(content["milestone"]["title"])

    # Return the populated Issue dataclass
    return Issue(
        url=url,
        number=number,
        title=title,
        author=author,
        createdAt=createdAt,
        closedAt=closedAt,
        closed=closed,
        closedBy=closedBy,
        milestone=milestone,
        assignees=assignees,
        reactions=reactions,
        comments=comments,
        urgency=urgency,
        difficulty=difficulty,
        modifier=modifier,
        isLectureTopicTask="[Lecture Topic Task]" in title,
    )


def should_count_issue(
    *,
    issue: Issue,
    logger: logging.Logger,
    currentMilestone: str,
    managers: list[str],
    shouldCountOpenIssues: bool,
) -> bool:
    if issue.milestone is None:
        logger.warning(
            f"[Issue #{issue.number}]({issue.url}) is not associated with a milestone."
        )
        return False
    if issue.milestone != currentMilestone:
        return False
    if issue.closed:
        assert issue.closedBy is not None
        if issue.closedBy not in managers:
            logger.warning(
                f"[Issue #{issue.number}]({issue.url}) was closed by non-manager {issue.closedBy}. Only issues closed by managers are accredited. Managers for this project are: {managers}"
            )
            return False

    if not issue.closed and not shouldCountOpenIssues:
        return False

    if issue.difficulty is None or issue.urgency is None:
        logger.warning(
            f"[Issue #{issue.number}]({issue.url}) does not have the Urgency and/or Difficulty fields populated"
        )
        return False
    return True


def decay(
    milestoneStart: datetime, milestoneEnd: datetime, issueCreated: datetime
) -> float:
    duration = (milestoneEnd - milestoneStart).days
    if issueCreated > milestoneEnd:
        issueCreated = milestoneEnd
    issueLateness = max(0, (issueCreated - milestoneStart).days)
    decayBase = 1 + 1 / duration
    difference = pow(decayBase, 3 * duration) - pow(decayBase, 0)
    finalDecrease = 0.7
    translate = 1 + finalDecrease / difference
    return max(
        0, translate - finalDecrease * pow(decayBase, 3 * issueLateness) / difference
    )


def calculate_issue_scores(
    *,
    issue: Issue,
    managers: list[str],
    developers: list[str],
    startDate: datetime,
    endDate: datetime,
    useDecay: bool,
    logger: logging.Logger,
) -> IssueMetrics:

    assert issue.difficulty is not None and issue.urgency is not None
    modifier = issue.modifier if issue.modifier is not None else 0.0
    baseIssueScoresByDeveloper = defaultdict(float)
    bonusesByDeveloper = defaultdict(float)
    issueScore = (
        issue.difficulty
        * issue.urgency
        * (decay(startDate, endDate, issue.createdAt) if useDecay else 1)
        + modifier
    )
    # attribute documentation bonus to author when a manager has reacted to the issue description with 🎉
    documentationBonus = issueScore * 0.1
    for reaction in issue.reactions:
        if reaction.kind == ReactionKind.HOORAY and reaction.user_login in managers:
            logger.info(
                f"Documentation Bonus given to {issue.author} in [Issue #{issue.number}]({issue.url})"
            )
            bonusesByDeveloper[issue.author] += documentationBonus
            break  # bonus should only be applied once
    # attribute documentation bonus to user when a manager reacts to a comment with 🎉
    for comment in issue.comments:
        if comment.author_login in managers:
            continue
        shouldGetBonus = False
        for reaction in comment.reactions:
            if reaction.kind == ReactionKind.HOORAY and reaction.user_login:
                shouldGetBonus = True
                break
        if shouldGetBonus:
            bonusesByDeveloper[issue.author] += documentationBonus
            logger.info(
                f"Documentation Bonus given to {issue.author} in [Issue #{issue.number}]({issue.url})"
            )
            break  # only attribute the bonus once and to the earliest comment

    # attribute points only to developers
    assignedDevelopers = len(set(issue.assignees) - set(managers))
    distributedScore = (
        issueScore / assignedDevelopers if assignedDevelopers > 0 else issueScore
    )
    for user in issue.assignees:
        if user not in developers and user not in managers:
            logger.warning(
                f"[Issue #{issue.number}]({issue.url}) assigned to user {user} not belonging to the team."
            )
            continue
        if user in developers:
            baseIssueScoresByDeveloper[user] += distributedScore

    return IssueMetrics(
        pointsByDeveloper=baseIssueScoresByDeveloper,
        bonusesByDeveloper=bonusesByDeveloper,
    )
