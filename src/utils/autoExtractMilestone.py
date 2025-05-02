from datetime import date


def auto_extract_milestone(
    now: date, milestones: list[tuple[str, date | None]]
) -> str | None:
    if len(milestones) == 0:
        return None
    milestone, _ = milestones[0]
    for m, date in milestones:
        if date is None:
            continue
        if date <= now:
            milestone = m
        else:
            break
    return milestone
