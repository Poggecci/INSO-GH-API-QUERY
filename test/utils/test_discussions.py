import pytest
from datetime import datetime, timedelta, timezone
from src.utils.discussions import (
    calculateWeeklyDiscussionPenalties,
    findWeeklyDiscussionParticipation,
    getWeekIndex,
    parseDiscussion,
)
from src.utils.models import Category, Discussion, DiscussionComment, ParsingError


# Mock data and fixtures
@pytest.fixture
def sample_discussion_dict():
    return {
        "author": {"login": "testuser"},
        "title": "Test Discussion",
        "body": "Test body content",
        "publishedAt": "2024-01-01T12:00:00Z",
        "category": {"id": 0, "name": "General"},
        "comments": {
            "nodes": [
                {
                    "author": {"login": "commenter1"},
                    "body": "Test comment",
                    "publishedAt": "2024-01-01T13:00:00Z",
                }
            ]
        },
    }


@pytest.fixture
def sample_discussion(sample_discussion_dict):
    return Discussion(
        author="testuser",
        title="Test Discussion",
        body="Test body content",
        category=Category(id=0, name="General"),
        comments=[
            DiscussionComment(
                author="commenter1",
                body="Test comment",
                publishedAt=datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc),
            )
        ],
        publishedAt=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def milestone_dates():
    start = datetime(2024, 1, 1)  # Monday
    end = datetime(2024, 1, 31)  # Wednesday
    return start, end


# Test parseDiscussion function
class TestParseDiscussion:
    def test_valid_discussion_parsing(self, sample_discussion_dict, sample_discussion):
        result = parseDiscussion(discussion_dict=sample_discussion_dict)
        assert result == sample_discussion

    def test_invalid_discussion_dict(self):
        with pytest.raises(ParsingError):
            parseDiscussion(discussion_dict={})

    def test_missing_author(self, sample_discussion_dict):
        sample_discussion_dict["author"] = None
        with pytest.raises(TypeError):
            parseDiscussion(discussion_dict=sample_discussion_dict)


# Test getWeekIndex function
class TestGetWeekIndex:
    def test_date_in_first_partial_week(self, milestone_dates):
        start, end = milestone_dates
        date = start + timedelta(days=2)  # Wednesday of first week
        assert (
            getWeekIndex(dateOfInterest=date, milestoneStart=start, milestoneEnd=end)
            == 0
        )

    def test_date_in_second_week(self, milestone_dates):
        start, end = milestone_dates
        date = start + timedelta(days=8)  # Tuesday of second week
        assert (
            getWeekIndex(dateOfInterest=date, milestoneStart=start, milestoneEnd=end)
            == 1
        )

    def test_date_before_milestone(self, milestone_dates):
        start, end = milestone_dates
        date = start - timedelta(days=1)
        assert (
            getWeekIndex(dateOfInterest=date, milestoneStart=start, milestoneEnd=end)
            == -1
        )

    def test_date_after_milestone(self, milestone_dates):
        start, end = milestone_dates
        date = end + timedelta(days=1)
        assert (
            getWeekIndex(dateOfInterest=date, milestoneStart=start, milestoneEnd=end)
            == -1
        )


# Test findWeeklyDiscussionParticipation function
class TestFindWeeklyDiscussionParticipation:
    @pytest.fixture
    def sample_discussions(self):
        return [
            Discussion(
                author="user1",
                title="Scrum Prep Milestone 0 - Week 1",
                body="Test",
                category=Category(id=0, name="General"),
                comments=[
                    DiscussionComment(
                        author="user2", body="Comment", publishedAt=datetime(2024, 1, 3)
                    )
                ],
                publishedAt=datetime(2024, 1, 2),
            ),
            Discussion(
                author="user2",
                title="Scrum Prep Milestone 0 - Week 2",
                body="Test",
                category=Category(id=0, name="General"),
                comments=[
                    DiscussionComment(
                        author="user1",
                        body="Comment",
                        publishedAt=datetime(2024, 1, 10),
                    )
                ],
                publishedAt=datetime(2024, 1, 9),
            ),
        ]

    def test_participation_tracking(self, sample_discussions, milestone_dates):
        start, end = milestone_dates
        members = {"user1", "user2"}

        participation = findWeeklyDiscussionParticipation(
            members=members,
            discussions=sample_discussions,
            milestone="Milestone 0",
            milestoneStart=start,
            milestoneEnd=end,
        )

        assert participation["user1"] == {0, 1}  # Week 1 discussion, Week 2 comment
        assert participation["user2"] == {0, 1}  # Week 1 comment, Week 2 discussion

    def test_no_milestone_discussion(self, sample_discussions, milestone_dates):
        start, end = milestone_dates
        members = {"user1", "user2"}

        participation = findWeeklyDiscussionParticipation(
            members=members,
            discussions=sample_discussions,
            milestone="Milestone 1",
            milestoneStart=start,
            milestoneEnd=end,
        )

        assert len(participation["user1"]) == 0  # No discussion for Milestone 1
        assert len(participation["user2"]) == 0  # No discussion for Milestone 1


# Test calculateWeeklyDiscussionPenalties function
class TestCalculateWeeklyDiscussionPenalties:
    def test_perfect_participation(self):
        participation = {"user1": {0, 1, 2, 3}}  # Participated every week
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 0.0

    def test_single_miss_week1(self):
        participation = {"user1": {1, 2, 3}}  # Missed week 1
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 1.0  # 2^0 = 1

    def test_single_miss_week2(self):
        participation = {"user1": {0, 2, 3}}  # Missed week 2
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 2.0  # 2^1 = 2

    def test_single_miss_week3(self):
        participation = {"user1": {0, 1, 3}}  # Missed week 3
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 4.0  # 2^2 = 4

    def test_single_miss_week4(self):
        participation = {"user1": {0, 1, 2}}  # Missed week 4
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 8.0  # 2^3 = 8

    def test_consecutive_misses_weeks_1_2_3(self):
        participation = {"user1": {3}}  # Missed weeks 1, 2, 3
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 7.0  # 1 + 2 + 4 = 7

    def test_all_weeks_missed_4_weeks(self):
        participation = {"user1": set()}  # Missed all 4 weeks
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 15.0  # 1 + 2 + 4 + 8 = 15

    def test_non_consecutive_misses(self):
        participation = {"user1": {1, 3}}  # Missed weeks 1 and 3
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 5.0  # 1 + 4 = 5

    def test_max_penalty(self):
        participation = {"user1": set()}  # Missed all weeks
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=99)
        assert penalties["user1"] == 100.0  # Should cap at 100
