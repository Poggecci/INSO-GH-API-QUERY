from dataclasses import dataclass, field
from datetime import datetime
from src.utils.constants import pr_tz


@dataclass
class DeveloperMetrics:
    tasksBySprint: list[int] = field(default_factory=list)
    pointsClosed: float = 0
    percentContribution: float = 0  # pointsClosed / (totalPoints) * %100
    expectedGrade: float = 0  # floor((pointsClosed / trimmedMean) * %100 , %100)
    lectureTopicTasksClosed: int = 0


@dataclass
class MilestoneData:
    sprints: int = 2
    totalPointsClosed: float = 0
    startDate: datetime = datetime.now(tz=pr_tz)
    endDate: datetime = datetime.now(tz=pr_tz)
    devMetrics: dict[str, DeveloperMetrics] = field(default_factory=dict)


@dataclass
class LectureTopicTaskData:
    totalLectureTopicTasks: int = 0
    lectureTopicTasksByDeveloper: dict[str, int] = field(default_factory=dict)
