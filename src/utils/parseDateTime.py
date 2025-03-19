from datetime import datetime
from src.utils.constants import pr_tz, default_start_time, default_end_time


def parse_iso_datetime(iso_string: str) -> tuple[datetime, bool, bool]:
    try:
        dt = datetime.fromisoformat(iso_string)
    except ValueError:
        raise ValueError("Invalid ISO datetime format")

    return (
        dt,
        "T" in iso_string,
        dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None,
    )


def get_milestone_start(iso_string: str) -> datetime:
    result, has_time, has_tz = parse_iso_datetime(iso_string=iso_string)
    if not has_time:
        result = result.replace(
            hour=default_start_time.hour, minute=default_start_time.minute
        )
    if not has_tz:
        result = pr_tz.localize(result)
    return result


def get_milestone_end(iso_string: str) -> datetime:
    result, has_time, has_tz = parse_iso_datetime(iso_string=iso_string)
    if not has_time:
        result = result.replace(
            hour=default_end_time.hour, minute=default_end_time.minute
        )
    if not has_tz:
        result = pr_tz.localize(result)
    return result
