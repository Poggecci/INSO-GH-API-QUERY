from collections import defaultdict
from dataclasses import dataclass, field
import datetime as dt
from typing import DefaultDict


@dataclass(eq=True, frozen=True)
class Developer:
    """Represents a developer identified by their GitHub login (their username).

    Attributes:
        githubUsername (str): The GitHub username of the developer.
    """

    githubUsername: str

    def __str__(self):
        """Returns the string representation of the Developer, which is their GitHub login."""
        return self.githubUsername

    def __repr__(self):
        """Returns the string representation of the Developer, which is their GitHub login."""
        return self.githubUsername


@dataclass
class DeveloperMetrics:
    """Represents the metrics associated with a developer during a sprint or milestone.

    Attributes:
        pointsClosed (float): The total points closed by the developer.
        percentContribution (float): The percentage contribution of the developer.
        expectedGrade (float): The expected grade of the developer.
        lectureTopicTasksClosed (int): The number of lecture topic tasks closed by the developer.
    """

    pointsClosed: float = 0
    percentContribution: float = 0
    expectedGrade: float = 0
    lectureTopicTasksClosed: int = 0


@dataclass
class SprintData:
    """Represents the data for a sprint.

    Attributes:
        startDate (dt.date): The start date of the sprint.
        duration (dt.timedelta): The duration of the sprint.
        totalPointsClosed (float): The total points closed during the sprint.
        devMetrics (DefaultDict[Developer, DeveloperMetrics]): A dictionary of Developer objects and their corresponding metrics for the sprint.
    """

    startDate: dt.date
    duration: dt.timedelta
    totalPointsClosed: float = 0
    devMetrics: DefaultDict[Developer, DeveloperMetrics] = field(
        default_factory=lambda: defaultdict(DeveloperMetrics)
    )


@dataclass
class MilestoneData:
    """Represents the data for a milestone, which consists of multiple sprints.
    This class is meant to be initialized with the default parameters and then later populated.

    Attributes:
        startDate (dt.date): The start date of the milestone.
        endDate (dt.date): The end date of the milestone.
        developers (set[Developer]): A set of Developer objects involved in the milestone.
        sprints (list[SprintData]): A list of SprintData objects representing each sprint in the milestone.
    """

    startDate: dt.date
    endDate: dt.date
    developers: set[Developer] = field(default_factory=set)
    sprints: list[SprintData] = field(default_factory=list)

    def getMetricsForDev(self, dev: Developer) -> None | DeveloperMetrics:
        """Calculates and returns the cumulative metrics for a developer across all sprints in the milestone.

        Args:
            dev (Developer): The developer for whom to calculate the metrics.

        Returns:
            DeveloperMetrics | None: The cumulative metrics for the developer, or None if the developer is not part of the milestone.
        """
        if dev not in self.developers:
            return None
        milestoneMetrics = DeveloperMetrics()
        for sprint in self.sprints:
            if dev not in sprint.devMetrics:
                continue
            sprintMetrics = sprint.devMetrics[dev]
            milestoneMetrics.pointsClosed += sprintMetrics.pointsClosed
            milestoneMetrics.percentContribution += sprintMetrics.pointsClosed / len(
                self.sprints
            )
            milestoneMetrics.expectedGrade += sprintMetrics.expectedGrade / len(
                self.sprints
            )
            milestoneMetrics.lectureTopicTasksClosed += (
                sprintMetrics.lectureTopicTasksClosed
            )
        return milestoneMetrics

    def getTotalLectureTopicTasks(self) -> int:
        """Calculates and returns the total number of lecture topic tasks closed during the milestone.

        Returns:
            int: The total number of lecture topic tasks closed.
        """
        totalLectureTopicTasks = 0
        for sprint in self.sprints:
            totalLectureTopicTasks += sum(
                map(lambda m: m.lectureTopicTasksClosed, sprint.devMetrics.values())
            )
        return totalLectureTopicTasks

    def getTotalPointsClosed(self) -> float:
        """Calculates and returns the total points closed during the milestone.

        Returns:
            int: The total number of lecture topic tasks closed.
        """
        totalPoints = 0
        for sprint in self.sprints:
            totalPoints += sum(
                map(lambda m: m.pointsClosed, sprint.devMetrics.values())
            )
        return totalPoints


@dataclass
class LectureTopicTaskData:
    """Represents the data for lecture topic tasks.

    Attributes:
        totalLectureTopicTasks (int): The total number of lecture topic tasks.
        lectureTopicTasksByDeveloper (dict[str, int]): A dictionary mapping developer GitHub logins to the number of lecture topic tasks they closed.
    """

    totalLectureTopicTasks: int = 0
    lectureTopicTasksByDeveloper: dict[str, int] = field(default_factory=dict)
