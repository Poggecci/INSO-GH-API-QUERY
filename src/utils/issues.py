from collections import defaultdict
from datetime import datetime
import logging
from src.utils.models import (
    IssueComment,
    IssueMetrics,
    ParsingError,
    Reaction,
    ReactionKind,
    Issue,
)


def parseIssue(*, issue_dict: dict) -> Issue:
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
        ParsingError: If the issue 'content' field is missing or is empty due to permission errors or possibly API changes.
        KeyError: If the structure of the issue_dict does not match the expected format, either due to missing fields
                      or permission errors. Specific errors include:
                      - Missing Required fields such as 'url', 'number', 'title', 'createdAt', etc.
        ValueError: if date formatting for 'createdAt' or 'closedAt' fails.
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
    url: str | None = content.get("url", None)
    number: int | None = content.get("number", None)
    # Except the two above which for some reason can sometimes be unpopulated
    title: str = content["title"]
    author: str = content["author"]["login"]
    createdAt = datetime.fromisoformat(content["createdAt"])
    closed = content["closed"]
    assignees = [
        assignee_dict["login"] for assignee_dict in content["assignees"]["nodes"]
    ]
    labels: list[str] = [label["name"] for label in content["labels"]["nodes"]]
    # Currently, we only search for reactions and comments with HOORAY 🎉
    reactions = [
        Reaction(user_login=reaction["user"]["login"], kind=ReactionKind.HOORAY)
        for reaction in content["reactions"]["nodes"]
    ]
    comments = [
        IssueComment(
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
        labels=labels,
        reactions=reactions,
        comments=comments,
        urgency=urgency,
        difficulty=difficulty,
        modifier=modifier,
        isLectureTopicTask="[Lecture Topic Task]" in title
        or "lecture topic task" in [l.lower() for l in labels],
    )


def shouldCountIssue(
    *,
    issue: Issue,
    logger: logging.Logger,
    currentMilestone: str | None,
    managers: list[str],
    shouldCountOpenIssues: bool,
) -> bool:
    """
    Determines whether an issue should be counted for scoring based on various criteria.

    This function checks if an issue meets the following conditions:
    1. The issue is associated with a milestone.
    2. The issue's milestone matches the current milestone.
    3. If the issue is closed, it was closed by a manager.
    4. If the issue is open, open issues are allowed to be counted.
    5. The issue has both Urgency and Difficulty fields populated.

    Args:
        issue (Issue): The issue to be evaluated.
        logger (logging.Logger): Logger object for recording warnings.
        currentMilestone (str): The milestone currently being processed.
        managers (list[str]): List of manager usernames.
        shouldCountOpenIssues (bool): Flag indicating whether open issues should be counted.

    Returns:
        bool: True if the issue should be counted, False otherwise.

    Side effects:
        Logs warnings for issues that:
        - Are not associated with a milestone.
        - Were closed by a non-manager.
        - Do not have Urgency and/or Difficulty fields populated.
    """
    if issue.milestone is None:
        logger.warning(
            f"[Issue #{issue.number}]({issue.url}) is not associated with a milestone."
        )
        return False
    if currentMilestone is not None and issue.milestone != currentMilestone:
        return False
    if issue.closed:
        if issue.closedBy is not None and issue.closedBy not in managers:
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


def whoShouldGetBonus(issue: Issue, managers: list[str]) -> str | None:
    # attribute documentation bonus to author when a manager has reacted to the issue description with 🎉
    target = None
    for reaction in issue.reactions:
        if (
            reaction.kind == ReactionKind.HOORAY
            and reaction.user_login in managers
            and issue.author
            not in managers  # Ensure the author isn't a manager as they shouldn't be receiving points
        ):
            # Penalize if there are more than 1 valid reactions
            if target is not None:
                return None
            target = issue.author
    # attribute documentation bonus to user when a manager reacts to a comment with 🎉
    for comment in issue.comments:
        if comment.author_login in managers:
            continue
        for reaction in comment.reactions:
            if reaction.kind == ReactionKind.HOORAY and reaction.user_login in managers:
                # Penalize if there are more than 1 valid reactions
                if target is not None:
                    return None
                target = comment.author_login
    return target


def calculateIssueScores(
    *,
    issue: Issue,
    managers: list[str],
    developers: list[str],
    startDate: datetime,
    endDate: datetime,
    useDecay: bool,
    logger: logging.Logger,
) -> IssueMetrics:
    """
    Calculates scores and bonuses for an issue based on various factors and team member roles.

    This function computes the base score for an issue and distributes it among assigned developers.
    It also calculates bonus points for documentation contributions.

    Args:
        issue (Issue): The issue to be scored.
        managers (list[str]): List of manager usernames.
        developers (list[str]): List of developer usernames.
        startDate (datetime): The start date of the relevant period (e.g., milestone start).
        endDate (datetime): The end date of the relevant period (e.g., milestone end).
        useDecay (bool): Flag to determine if decay factor should be applied to the score.
        logger (logging.Logger): Logger object for recording information and warnings.

    Returns:
        IssueMetrics: An object containing two defaultdict(float) attributes:
                      - pointsByDeveloper: Base scores attributed to each developer.
                      - bonusesByDeveloper: Bonus scores attributed to each developer.

    Behavior:
        1. Calculates base issue score using difficulty, urgency, and optional decay factor.
        2. Applies modifier to the base score if present.
        3. Attributes documentation bonus (10% of issue score) to the issue author if a manager reacted with 🎉.
        4. Attributes additional documentation bonus for helpful comments if a manager reacted with 🎉.
        5. Distributes the base issue score equally among assigned developers.
        6. Logs warnings for assignments to users not in the developers or managers lists.

    Note:
        - The function assumes that issue.difficulty and issue.urgency are not None.
        - Bonuses are only attributed once per issue and once for comments.
        - Scores are only attributed to users in the developers list.
    """

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
    logger.debug(f"Issue #{issue.number} score: {issueScore}")
    # attribute documentation bonus to author when a manager has reacted to the issue or comments with 🎉
    documentationBonus = issueScore * 0.1
    bonusTarget = whoShouldGetBonus(issue=issue, managers=managers)
    if bonusTarget is not None:
        logger.info(
            f"Documentation Bonus given to {bonusTarget} in [Issue #{issue.number}]({issue.url})"
        )
        bonusesByDeveloper[bonusTarget] += documentationBonus

    # attribute points only to developers in the team
    assignedDevelopers = len((set(issue.assignees) - set(managers)) & (set(developers)))
    logger.debug(
        f"Issue #{issue.number} assigned developers count: {assignedDevelopers}"
    )
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


def applyIssuePreProcessingHooks(
    *,
    hooks: list[str],
    issue: Issue,
    milestone: str,
    startDate: datetime,
    endDate: datetime,
) -> Issue:
    """
    Apply a series of preprocessing hooks to modify an Issue object.

    This function executes a list of Python code snippets (hooks) that can modify
    the given Issue object and access other relevant milestone information.
    Each hook is executed in the order it appears in the list, with access to
    the current state of the Issue object and milestone data. The current issue
    is available through an `issue` variable passed into the exec() call alongside the hook.

    Args:
        hooks : List[str]
            A list of Python code snippets to be executed as preprocessing hooks.
            Each hook should be a string containing valid Python code.

        issue : Issue
            The Issue object to be processed and potentially modified by the hooks.

        milestone : str
            The name or identifier of the current milestone. This is made available
            to the hooks for potential use in decision-making or modifications.

        startDate : datetime
            The start date of the current milestone. Available to hooks for
            timeline-based logic or modifications.

        endDate : datetime
            The end date of the current milestone. Available to hooks for
            timeline-based logic or modifications.

    Returns:
        The potentially modified Issue object after all hooks have been applied.

    Warnings:
        - Security Risk: This function uses exec() to run the provided hooks.
        Ensure that all hooks come from trusted sources and are properly sanitized
        before execution. Malicious hooks could potentially execute harmful code.
        Please don't use this function unless you know what you're doing.

        - Scope Limitation: Hooks only have access to the variables explicitly
        provided (issue, milestone, startDate, endDate). Any other required data
        should be encapsulated within these variables or the Issue object itself.

    Examples:
        hooks = [
            '''
            if issue.number == 1:
                issue.closedAt = startDate
            ''',
            '''
            if 'urgent' in issue.title.lower():
                issue.urgency = max(issue.urgency or 0, 4.0)
            '''
        ]
        modified_issue = applyIssuePreProcessingHooks(
            hooks=hooks,
            issue=original_issue,
            milestone="Q2 Release",
            startDate=datetime(2024, 4, 1),
            endDate=datetime(2024, 6, 30)
        )
    """
    for hook in hooks:
        # Create a local scope with the variables we want to expose to the hook
        local_vars = {
            "issue": issue,
            "milestone": milestone,
            "startDate": startDate,
            "endDate": endDate,
        }
        # Execute the hook in the context of local_vars
        exec(hook, None, local_vars)
        # Update the issue with any changes made by the hook
        issue = local_vars["issue"]

    return issue
