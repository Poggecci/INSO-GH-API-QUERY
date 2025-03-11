import csv
from datetime import datetime
import json

from dotenv import load_dotenv
from src.getTeamMembers import getTeamMembers

from src.utils.discussions import (
    calculateWeeklyDiscussionPenalties,
    findWeeklyDiscussionParticipation,
    getDiscussions,
    getWeeks,
)
from src.utils.parseDateTime import get_milestone_start, get_milestone_end


def write_discussion_participation_data_to_csv(
    participation: dict, weeks: int, csv_file_path: str
):
    penalties = calculateWeeklyDiscussionPenalties(
        participation=participation, weeks=weeks
    )
    with open(csv_file_path, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ["Developer"] + [f"Week #{week+1}" for week in range(weeks)] + ["Penalty"]
        )
        for developer, weeks_participated in participation.items():
            writer.writerow(
                [developer]
                + [week in weeks_participated for week in range(weeks)]
                + [penalties[developer]]
            )


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        exit(0)
    _, course_config_file, *_ = sys.argv
    load_dotenv()
    with open(course_config_file) as course_config:
        course_data = json.load(course_config)
    organization = course_data["organization"]
    metricsDirectory = course_data["metricsDirectory"]
    startDate = get_milestone_start(course_data["milestoneStartsOn"])
    endDate = get_milestone_end(course_data["milestoneEndsOn"])
    teams = course_data["teams"]
    print("Organization: ", course_data["organization"])
    for team, team_data in teams.items():
        print("Team: ", team)
        print("Managers: ", team_data["managers"])
        members = getTeamMembers(organization, team)
        milestone = team_data["milestone"]
        discussionParticipation = findWeeklyDiscussionParticipation(
            members=set(members),
            discussions=getDiscussions(org=organization, team=team),
            milestone=milestone,
            milestoneStart=startDate,
            milestoneEnd=endDate,
        )
        os.makedirs(metricsDirectory, exist_ok=True)
        write_discussion_participation_data_to_csv(
            participation=discussionParticipation,
            weeks=getWeeks(milestoneStart=startDate, milestoneEnd=endDate),
            csv_file_path=f"{metricsDirectory}/Discussion Participation-{team}-{organization}.csv",
        )
