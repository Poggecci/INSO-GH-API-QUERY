import logging
from src.generateTeamMetrics import (
    fetchProcessedIssues,
    getLectureTopicTaskMetricsFromIssues,
)
from src.utils.models import LectureTopicTaskData


def getLectureTopicTaskMetrics(
    org: str,
    team: str,
    members: list[str],
    managers: list[str],
    logger: logging.Logger | None = None,
    shouldCountOpenIssues: bool = False,
) -> LectureTopicTaskData:
    if logger is None:
        logger = logging.getLogger(__name__)
    return getLectureTopicTaskMetricsFromIssues(
        issues=fetchProcessedIssues(
            org=org,
            team=team,
            logger=logger,
            managers=managers,
            shouldCountOpenIssues=shouldCountOpenIssues,
        ),
        members=members,
        logger=logger,
    )
