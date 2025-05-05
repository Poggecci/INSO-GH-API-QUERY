from collections.abc import Iterator, ValuesView
import logging
from datetime import datetime
from queue import Queue
from threading import Thread
from src.getMilestones import getMilestones
from src.getProject import getProject
from src.utils.constants import pr_tz
from src.utils.issues import (
    applyIssuePreProcessingHooks,
    calculateIssueScores,
    parseIssue,
    shouldCountIssue,
)
from src.utils.models import (
    DeveloperMetrics,
    Issue,
    LectureTopicTaskData,
    MilestoneData,
    ParsingError,
)
from src.utils.queryRunner import runGraphqlQuery
from concurrent.futures import ThreadPoolExecutor

# Check out https://docs.github.com/en/graphql/guides/introduction-to-graphql#schema to understand this query better
get_team_issues = """
query QueryProjectItemsForTeam(
  $owner: String!
  $projectNumber: Int!
  $nextPage: String
) {
    organization(login: $owner) {
        projectV2(number: $projectNumber
        ) {
            title
            items(first: 100, after: $nextPage) {
                pageInfo {
                    endCursor
                    hasNextPage
                }
                nodes {
                    content {
                    ... on Issue {
                        url
                        number
                        title
                        author {
                        login
                        }
                        createdAt
                        closedAt
                        closed
                        milestone {
                        title
                        }
                        assignees(first: 20) {
                        nodes {
                            login
                        }
                        }
                        labels(first: 10) {
                        nodes {
                            name
                        }
                        }
                        reactions(first: 10, content: HOORAY) {
                        nodes {
                            user {
                            login
                            }
                        }
                        }
                        comments(first: 30) {
                        nodes {
                            author {
                            login
                            }
                            reactions(first: 10, content: HOORAY) {
                            nodes {
                                user {
                                login
                                }
                            }
                            }
                        }
                        }
                        timelineItems(last: 1, itemTypes : [CLOSED_EVENT]){
                            nodes {
                                ... on ClosedEvent {
                                        actor {
                                            login
                                        }
                                }
                            }
                        }
                        }
                    }

                    Urgency: fieldValueByName(name: "Urgency") {
                        ... on ProjectV2ItemFieldNumberValue {
                            number
                        }
                    }
                    Difficulty: fieldValueByName(name: "Difficulty") {
                        ... on ProjectV2ItemFieldNumberValue {
                            number
                        }
                    }
                    Modifier: fieldValueByName(name: "Modifier") {
                        ... on ProjectV2ItemFieldNumberValue {
                            number
                        }
                    }
                }
            }
        }
    }
}
"""


def outliersRemovedAverage(scores: ValuesView[float], /) -> float:
    non_zero_scores = [s for s in scores if s > 0]
    smallest_elem = min(non_zero_scores, default=0)
    largestVal = max(non_zero_scores, default=0)
    newLength = len(list(scores)) - 2
    total = sum(scores, start=0) - largestVal - smallest_elem
    return total / max(1, newLength)


def getCurrentSprintIndex(*, date: datetime, cutoffs: list[datetime]):
    sprintIndex = 0
    for cutoff in cutoffs:
        if date > cutoff:
            sprintIndex += 1
    return sprintIndex


def getFormattedSprintDateRange(
    *, startDate: datetime, endDate: datetime, cutoffs: list[datetime], sprintIndex: int
):
    if len(cutoffs) == 0:
        return f"{startDate.strftime('%Y/%m/%d')}-{endDate.strftime('%Y/%m/%d')}"
    if sprintIndex >= len(cutoffs):
        return f"{cutoffs[-1].strftime('%Y/%m/%d')}-{endDate.strftime('%Y/%m/%d')}"
    if sprintIndex == 0:
        return f"{startDate.strftime('%Y/%m/%d')}-{cutoffs[0].strftime('%Y/%m/%d')}"
    return f"{cutoffs[sprintIndex-1].strftime('%Y/%m/%d')}-{cutoffs[sprintIndex].strftime('%Y/%m/%d')}"


def generateSprintCutoffs(
    *, startDate: datetime, endDate: datetime, sprints: int
) -> list[datetime]:
    if sprints <= 1:
        return []

    total_duration = endDate - startDate
    cutoffs = []

    for i in range(1, sprints):
        fraction = i / sprints
        cutoff_date = startDate + total_duration * fraction
        cutoffs.append(cutoff_date)

    return cutoffs


def fetchIssuesFromGithub(
    *, org: str, team: str, logger: logging.Logger | None = None
) -> Iterator[dict]:
    if not logger:
        logger = logging.getLogger()

    project = getProject(organization=org, project_name=team)
    logger.info(f"Found {project}")
    if not project.public:
        logger.warning(
            "Project visibility is set to private. This can lead to"
            " issues not being found if the Personal Access Token doesn't"
            " have permissions for viewing private projects."
        )

    params = {"owner": org, "team": team, "projectNumber": project.number}
    hasAnotherPage = True
    while hasAnotherPage:
        response: dict = runGraphqlQuery(query=get_team_issues, variables=params)
        project_dict_with_issues: dict = response["organization"]["projectV2"]
        issues = project_dict_with_issues["items"]["nodes"]
        yield from issues

        hasAnotherPage = project_dict_with_issues["items"]["pageInfo"]["hasNextPage"]
        if hasAnotherPage:
            params["nextPage"] = project_dict_with_issues["items"]["pageInfo"][
                "endCursor"
            ]


def fetchProcessedIssues(
    *,
    org: str,
    team: str,
    logger: logging.Logger,
    hooks: list[str] | None = None,
    milestone: str | None = None,
    startDate: datetime | None = None,
    endDate: datetime | None = None,
    managers: list[str],
    shouldCountOpenIssues: bool = False,
) -> Iterator[Issue]:
    """
    This function will fetch all team issues from Github and process them accordingly
    by applying specified hooks and filtering issues that should not be counted.

    Args:
        org : str
            Organization name
        team : str
            Team name
        logger : Logger
            Logger to use
        hooks : List[str]
            List of hooks to apply per issue before filtering them
        milestone : str
            Milestone name. Will ignore milestone filtering if left null
        startDate : datetime
            Date of milestone start
        endDate : datetime
            Date of milestone end
        managers : List[str]
            List of manager names
        shouldCountOpenIssues : bool
            Determines whether to filter open issues or not
    """
    for issue_dict in fetchIssuesFromGithub(org=org, team=team, logger=logger):
        try:
            issue = parseIssue(issue_dict=issue_dict)
        except ParsingError:
            # don't log since the root cause can be hard to identify without manual review
            continue
        except KeyError as e:
            logger.exception(
                f"{e}. GH GraphQL API Issue type may have changed. This requires updating the code. Please contact the maintainers."
            )
            continue
        except ValueError as e:
            logger.exception(
                f"{e}. GH GraphQL API Issue type may have changed. This requires updating the code. Please contact the maintainers."
            )
            continue

        # Apply any overrides prior to counting or discarding the issue
        if (
            hooks is not None
            and milestone is not None
            and startDate is not None
            and endDate is not None
        ):
            issue = applyIssuePreProcessingHooks(
                hooks=hooks,
                issue=issue,
                milestone=milestone,
                startDate=startDate,
                endDate=endDate,
            )

        if not shouldCountIssue(
            issue=issue,
            logger=logger,
            currentMilestone=milestone,
            managers=managers,
            shouldCountOpenIssues=shouldCountOpenIssues,
        ):
            continue

        print(f"Successfully validated Issue #{issue.number}")
        yield issue


def getLectureTopicTaskMetricsFromIssues(
    issues: Iterator[Issue], members: list[str], logger: logging.Logger
) -> LectureTopicTaskData:
    """
    Read issues from iterator to calculate lecture topic task metrics.

    Non lecture topic task issues are ignored. If a non 1 amount of developers
    are assigned to the issue then it is skipped.

    Args:
        issues : Iterator[Issue]
            Iterator of all issues to analyze
        members : List[str]
            List of all developers
        logger : Logger
            Logger to use
    """
    lectureTopicTaskData = LectureTopicTaskData()
    lectureTopicTaskData.lectureTopicTasksByDeveloperByMilestone = {
        member: {} for member in members
    }

    for issue in issues:
        # Skip issue if no milestone is assigned
        if issue.milestone is None:
            logger.warning(
                f"[Issue #{issue.number}]({issue.url}) does not have a milestone assigned so lecture topic task points were ignored"
            )
            continue
        # Add milestone before isLectureTopicTask filtering so it includes milestones where no one did any LTTs
        lectureTopicTaskData.totalMilestones.add(issue.milestone)

        # Skip issue if it is not a lecture topic task
        if not issue.isLectureTopicTask:
            continue

        # Skip issue if it does not have only one assignee
        if len(issue.assignees) != 1:
            logger.warning(
                f"[Issue #{issue.number}]({issue.url}) does not have only 1 assigned developer so lecture topic task points for this issue will be ignored"
            )
            continue

        # Track metrics
        tasks_by_milestone = (
            lectureTopicTaskData.lectureTopicTasksByDeveloperByMilestone[
                issue.assignees[0]
            ]
        )
        if tasks_by_milestone.get(issue.milestone) is None:
            tasks_by_milestone[issue.milestone] = 0
        tasks_by_milestone[issue.milestone] += 1
        lectureTopicTaskData.totalLectureTopicTasks += 1
        logger.debug(
            f"Issue #{issue.number} was marked as a lecture topic task for {issue.assignees[0]} in {issue.milestone}"
        )

    return lectureTopicTaskData


def iteratorSplitter(iterator: Iterator[Issue], queues: list[Queue[Issue | None]]):
    """
    Add values received from the iterator to 2 individual queues, essentially splitting
    the iterator into 2.

    Args:
        iterator : Iterator
            Data source
        queue1 : Queue
            One of the queues to add iterator data to
        queue2 : Queue
            The other queue to add iterator data to
    """

    def add_to_queues(item):
        for queue in queues:
            queue.put(item)

    try:
        for item in iterator:
            add_to_queues(item)
        add_to_queues(None)

    except Exception as e:
        add_to_queues(e)


def getIteratorFromQueue(queue: Queue[Issue]) -> Iterator[Issue]:
    """
    Convert queue to an iterator.

    End is marked when value is null.
    """

    def queueIteratorNext():
        value = queue.get()
        if isinstance(value, Exception):
            raise value
        return value

    return iter(queueIteratorNext, None)


def getTeamMetricsForMilestone(
    *,
    org: str,
    team: str,
    milestone: str,
    members: list[str],
    managers: list[str],
    startDate: datetime,
    endDate: datetime,
    sprints: int,
    minTasksPerSprint: int,
    useDecay: bool,
    milestoneGrade: float,
    shouldCountOpenIssues: bool = False,
    issuePreProcessingHooks: list[str] | None = None,
    logger: logging.Logger | None = None,
) -> MilestoneData:
    if issuePreProcessingHooks is None:
        issuePreProcessingHooks = []
    if logger is None:
        logger = logging.getLogger(__name__)

    # Do some sanity checks on the passed in parameters
    if sprints < 1:
        raise ValueError(
            "Each milestone must contain at least 1 sprint. Revise the config file."
        )
    if endDate < startDate:
        raise ValueError("Milestone end date must be after start date.")
    try:
        milestones = getMilestones(organization=org, team=team)
        logger.debug(f"Milestones found: {[m.title for m in milestones]}")
        matchingMilestone = next(
            filter(lambda m: m.title == milestone, milestones), None
        )
        if matchingMilestone is None:
            logger.warning(
                f'Milestone "{milestone}" not found in any repo associated with the team'
            )
        elif (
            matchingMilestone.dueOn is not None
            and matchingMilestone.dueOn.date() != endDate.date()
        ):
            logger.warning(
                f"Milestone due date in config doesn't match milestone due date on Github"
            )
        else:
            print(f"Fetching issues associated with milestone {matchingMilestone}")
    except Exception as e:
        logger.warning(e)

    print(members)
    developers = [member for member in members if member not in managers]
    logger.debug(f"Developers: {developers}, Managers: {managers}")
    devPointsClosed = {dev: 0.0 for dev in developers}
    devTasksCompleted = {dev: [0 for _ in range(sprints)] for dev in developers}
    totalPointsClosed = 0.0
    milestoneData = MilestoneData(sprints=sprints, startDate=startDate, endDate=endDate)
    sprintCutoffs = generateSprintCutoffs(
        startDate=startDate, endDate=endDate, sprints=sprints
    )
    logger.debug(f"Sprint cutoffs: {sprintCutoffs}")
    devPointsByLabel = {dev: {} for dev in developers}
    milestoneLabels = set()

    issues = fetchProcessedIssues(
        org=org,
        team=team,
        logger=logger,
        hooks=issuePreProcessingHooks,
        milestone=milestone,
        startDate=startDate,
        endDate=endDate,
        managers=managers,
        shouldCountOpenIssues=shouldCountOpenIssues,
    )

    # Split issues iterator to read for both issue metrics and lecture topic task metrics
    issueMetricsQueue, lectureTopicTaskQueue = Queue(), Queue()
    thread = Thread(
        target=iteratorSplitter,
        args=(issues, [issueMetricsQueue, lectureTopicTaskQueue]),
    )
    thread.start()

    with ThreadPoolExecutor() as executor:
        # Run concurrently to obtain lecture topic task data in parallel with issue metrics data
        future = executor.submit(
            getLectureTopicTaskMetricsFromIssues,
            getIteratorFromQueue(lectureTopicTaskQueue),
            members,
            logger,
        )

        # Fetch all issues for the team, drop invalid ones, and apply their points to the correct developers
        for issue in getIteratorFromQueue(issueMetricsQueue):
            logger.debug(f"Calculating scores for issue #{issue.number}")
            issueMetrics = calculateIssueScores(
                issue=issue,
                managers=managers,
                developers=developers,
                startDate=startDate,
                endDate=endDate,
                useDecay=useDecay,
                logger=logger,
            )
            # attribute base issue points to developer alongside giving them credit for the completed task
            for dev, score in issueMetrics.pointsByDeveloper.items():
                devPointsClosed[dev] += score
                logger.debug(
                    f"{dev} now has closed {round(devPointsClosed[dev], 1)} points total"
                )
                # attribute task completion to appropriate sprint
                taskCompletionDate = (
                    issue.closedAt if issue.closedAt is not None else issue.createdAt
                )
                sprintIndex = getCurrentSprintIndex(
                    date=taskCompletionDate, cutoffs=sprintCutoffs
                )
                devTasksCompleted[dev][sprintIndex] += 1
                # update total points closed metric
                totalPointsClosed += score

                # assign issue score to labels per developer
                for label in issue.labels:
                    devPointsByLabel[dev][label] = (
                        devPointsByLabel[dev].get(label, 0) + score
                    )
                    milestoneLabels.add(label)

            # attribute bonuses for developers
            for dev, bonus in issueMetrics.bonusesByDeveloper.items():
                devPointsClosed[dev] += bonus
                # Note that bonus do not increase the total points closed such as to not "raise the bar"

        # Obtain lecture topic task metrics result
        lectureTopicTaskData = future.result()

    untrimmedAverage = totalPointsClosed / max(1, len(devPointsClosed))
    trimmedAverage = outliersRemovedAverage(devPointsClosed.values())
    devBenchmark = max(
        1, min(untrimmedAverage, trimmedAverage) / (milestoneGrade / 100)
    )
    logger.debug(f"Dev benchmark: {devBenchmark}")

    milestoneData.totalPointsClosed = totalPointsClosed
    for dev in developers:
        contribution = devPointsClosed[dev] / max(totalPointsClosed, 1)
        # check if the developer has completed the minimum tasks up until the current sprint
        # If they haven't thats an automatic zero for that milestone
        currentSprint = getCurrentSprintIndex(
            date=pr_tz.localize(datetime.today()), cutoffs=sprintCutoffs
        )
        individualGrade = min(devPointsClosed[dev] / devBenchmark * 100, 100.0)
        for sprintIdx in range(currentSprint + 1):
            if devTasksCompleted[dev][sprintIdx] < minTasksPerSprint:
                sprintDateRange = getFormattedSprintDateRange(
                    startDate=startDate,
                    endDate=endDate,
                    cutoffs=sprintCutoffs,
                    sprintIndex=sprintIdx,
                )
                logger.warning(
                    f"{dev} hasn't completed the minimum {minTasksPerSprint} task(s) required for sprint {sprintDateRange}"
                )
                if not shouldCountOpenIssues:
                    individualGrade = 0.0
        milestoneData.devMetrics[dev] = DeveloperMetrics(
            tasksBySprint=devTasksCompleted[dev],
            pointsClosed=devPointsClosed[dev],
            percentContribution=contribution * 100.0,
            individualGrade=individualGrade,
            milestoneGrade=milestoneGrade * 0.4 + individualGrade * 0.6,
            lectureTopicTasksClosed=lectureTopicTaskData.lectureTopicTasksByDeveloperByMilestone[
                dev
            ].get(
                milestone, 0
            ),
            pointPercentByLabel={
                label: devPointsByLabel[dev].get(label, 0)
                / max(1, devPointsClosed[dev])
                * 100
                for label in milestoneLabels
            },
        )
    return milestoneData
