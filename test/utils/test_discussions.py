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
                title="Week 0 Discussion",
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
                title="Week 1 Discussion",
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
        filter_func = lambda d: True  # Accept all discussions

        participation = findWeeklyDiscussionParticipation(
            members=members,
            discussions=sample_discussions,
            discussionFilter=filter_func,
            milestoneStart=start,
            milestoneEnd=end,
        )

        assert participation["user1"] == {0, 1}  # Week 0 discussion, Week 1 comment
        assert participation["user2"] == {0, 1}  # Week 0 comment, Week 1 discussion

    def test_filtered_participation(self, sample_discussions, milestone_dates):
        start, end = milestone_dates
        members = {"user1", "user2"}
        filter_func = lambda d: "Week 0" in d.title

        participation = findWeeklyDiscussionParticipation(
            members=members,
            discussions=sample_discussions,
            discussionFilter=filter_func,
            milestoneStart=start,
            milestoneEnd=end,
        )

        assert participation["user1"] == {0}  # Only Week 0 discussion
        assert participation["user2"] == {0}  # Only Week 0 comment


# Test calculateWeeklyDiscussionPenalties function
class TestCalculateWeeklyDiscussionPenalties:
    def test_perfect_participation(self):
        participation = {"user1": {0, 1, 2, 3}}  # Participated every week
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 0.0

    def test_single_miss(self):
        participation = {"user1": {0, 1, 3}}  # Missed week 2
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 2.0  # Base penalty for one miss

    def test_consecutive_misses(self):
        participation = {"user1": {0, 3}}  # Missed weeks 1 and 2 consecutively
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=4)
        assert penalties["user1"] == 5.0  # 2 + (2 + 1)

    def test_max_penalty(self):
        participation = {"user1": set()}  # Missed all weeks
        penalties = calculateWeeklyDiscussionPenalties(participation, weeks=99)
        assert penalties["user1"] == 100.0  # Should cap at 100
