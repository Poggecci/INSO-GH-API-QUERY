from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DeveloperMetrics:
    tasksPerSprint: int = 0
    pointsClosed: float = 0
    percentContribution: float = 0  # pointsClosed / (totalPoints) * %100
    expectedGrade: float = 0  # floor((pointsClosed / trimmedMean) * %100 , %100)
    lectureTopicTasksClosed: int = 0


@dataclass
class MilestoneData:
    sprints: int = 2
    totalPointsClosed: float = 0
    startDate: datetime = datetime.now()
    endDate: datetime = datetime.now()
    devMetrics: dict[str, DeveloperMetrics] = field(default_factory=dict)


@dataclass
class LectureTopicTaskData:
    totalLectureTopicTasks: int = 0
    lectureTopicTasksByDeveloper: dict[str, int] = field(default_factory=dict)
