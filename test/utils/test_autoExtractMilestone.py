from datetime import date
from src.utils.autoExtractMilestone import auto_extract_milestone


class TestAutoExtractMilestone:
    def test_default_case_1(self):
        now = date(2025, 1, 10)
        milestones: list[tuple[str, date | None]] = [
            ("M1", date(2025, 1, 1)),
            ("M2", date(2025, 1, 14)),
            ("M3", date(2025, 1, 28)),
        ]
        assert auto_extract_milestone(now, milestones) == "M1"

    def test_default_case_2(self):
        now = date(2025, 1, 25)
        milestones: list[tuple[str, date | None]] = [
            ("M1", date(2025, 1, 1)),
            ("M2", date(2025, 1, 14)),
            ("M3", date(2025, 1, 28)),
        ]
        assert auto_extract_milestone(now, milestones) == "M2"

    def test_default_case_3(self):
        now = date(2025, 1, 30)
        milestones: list[tuple[str, date | None]] = [
            ("M1", date(2025, 1, 1)),
            ("M2", date(2025, 1, 14)),
            ("M3", date(2025, 1, 28)),
        ]
        assert auto_extract_milestone(now, milestones) == "M3"

    def test_before_milestone_start(self):
        now = date(2024, 12, 31)
        milestones: list[tuple[str, date | None]] = [
            ("M1", date(2025, 1, 1)),
            ("M2", date(2025, 1, 14)),
            ("M3", date(2025, 1, 28)),
        ]
        assert auto_extract_milestone(now, milestones) == "M1"

    def test_single_milestone(self):
        now = date(2024, 1, 1)
        milestones: list[tuple[str, date | None]] = [
            ("M3", date(2025, 1, 28)),
        ]
        assert auto_extract_milestone(now, milestones) == "M3"

    def test_no_milestones(self):
        now = date(2025, 1, 10)
        assert auto_extract_milestone(now, []) == None

    def test_null_date(self):
        now = date(2024, 1, 1)
        milestones: list[tuple[str, date | None]] = [
            ("M1", None),
            ("M2", None),
        ]
        # Do not return None since there exists a milestone to fetch
        assert auto_extract_milestone(now, milestones) == "M1"
