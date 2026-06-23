from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from src.utils.constants import pr_tz


@dataclass
class DeveloperMetrics:
    tasksBySprint: list[int] = field(default_factory=list)
    pointsClosed: float = 0
    percentContribution: float = 0  # pointsClosed / (totalPoints) * %100
    individualGrade: float = 0  # floor((pointsClosed / trimmedMean) * %100 , %100)
    milestoneGrade: float = 0
    lectureTopicTasksClosed: int = 0
    pointPercentByLabel: dict[str, float] = field(default_factory=dict)
    # Cycle/lead time data: list of (issue_number, cycle_time_hours, lead_time_hours)
    issueTimings: list[tuple[int | None, float, float]] = field(default_factory=list)


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
    totalMilestones: set[str] = field(default_factory=set)
    lectureTopicTasksByDeveloperByMilestone: dict[str, dict[str, int]] = field(default_factory=dict)


class ReactionKind(StrEnum):
    HOORAY = "HOORAY"


@dataclass(kw_only=True)
class Reaction:
    user_login: str
    kind: ReactionKind


@dataclass(kw_only=True)
class TimelineEvent:
    """Represents a timeline event on a GitHub issue."""
    event_type: str  # "closed", "assigned", "cross_referenced"
    actor: str | None
    created_at: datetime | None
    assignee: str | None = None  # For AssignedEvent
    pr_number: int | None = None  # For CrossReferencedEvent with PR
    pr_url: str | None = None
    pr_merged: bool | None = None


@dataclass(kw_only=True)
class IssueComment:
    author_login: str
    reactions: list[Reaction] = field(default_factory=list)


@dataclass(kw_only=True)
class Issue:
    url: str | None
    number: int | None
    title: str
    author: str
    createdAt: datetime
    closedAt: datetime | None
    closed: bool
    closedBy: str | None
    milestone: str | None
    assignees: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    reactions: list[Reaction] = field(default_factory=list)
    comments: list[IssueComment] = field(default_factory=list)
    timeline: list[TimelineEvent] = field(default_factory=list)
    urgency: float | None
    difficulty: float | None
    modifier: float | None
    isLectureTopicTask: bool


@dataclass(kw_only=True)
class IssueMetrics:
    pointsByDeveloper: dict[str, float]
    bonusesByDeveloper: dict[str, float]


@dataclass(kw_only=True, frozen=True)
class Project:
    name: str
    number: int
    url: str
    public: bool


class ParsingError(Exception):
    """Custom exception for parsing errors."""

    def __init__(self, message: str):
        super().__init__(message)


@dataclass(kw_only=True)
class Milestone:
    url: str
    title: str
    dueOn: datetime | None


@dataclass(kw_only=True)
class Category:
    name: str
    id: int


@dataclass(kw_only=True)
class DiscussionComment:
    author: str
    body: str
    publishedAt: datetime


@dataclass(kw_only=True)
class Discussion:
    author: str
    title: str
    body: str
    category: Category
    comments: list[DiscussionComment]
    publishedAt: datetime
