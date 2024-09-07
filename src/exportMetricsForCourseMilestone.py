import csv
import json
from datetime import datetime
from generateTeamMetrics import getTeamMetricsForMilestone
from getTeamMembers import get_team_members

from utils.models import MilestoneData


def write_milestone_data_to_csv(milestone_data: MilestoneData, csv_file_path: str):
    with open(csv_file_path, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            ["Developer", "Points Closed", "Percent Contribution", "Expected Grade"]
        )
        writer.writerow(["Total", milestone_data.totalPointsClosed, "/100%", "/100%"])
        for developer, metrics in milestone_data.devMetrics.items():
            writer.writerow(
                [
                    developer,
                    round(metrics.pointsClosed, 1),
                    round(metrics.percentContribution, 1),
                    round(metrics.expectedGrade, 1),
                ]
            )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        exit(0)
    _, course_config_file, *_ = sys.argv
    # idk why this isn't working, so hardcode for now. Kinda had to anyway cuz managers are hard coded rn
    # teams = get_teams(org)
    with open(course_config_file) as course_config:
        course_data = json.load(course_config)
    organization = course_data["organization"]
    teams_and_teamdata = course_data["teams"]
    if (
        course_data.get("milestoneStartsOn", None) is None
        or not course_data["milestoneStartsOn"]
        or course_data["milestoneStartsOn"] is None
        or course_data.get("milestoneEndsOn", None) is None
        or course_data["milestoneEndsOn"] is None
        or not course_data["milestoneEndsOn"]
    ):
        startDate = datetime.now()
        endDate = datetime.now()
        useDecay = False
    else:
        startDate = datetime.fromisoformat(course_data["milestoneStartsOn"])
        endDate = datetime.fromisoformat(course_data["milestoneEndsOn"])
        useDecay = True

    print("Organization: ", organization)

    team_metrics = {}
    for team, teamdata in teams_and_teamdata.items():
        print("Team: ", team)
        print("Managers: ", teamdata["managers"])
        print("Milestone: ", teamdata["milestone"])
        members = get_team_members(organization, team)
        team_metrics[team] = getTeamMetricsForMilestone(
            org=organization,
            team=team,
            milestone=teamdata["milestone"],
            milestoneGrade=teamdata["milestoneGrade"],
            members=members,
            managers=teamdata["managers"],
            startDate=startDate,
            endDate=endDate,
            useDecay=useDecay,
        )
        write_milestone_data_to_csv(
            team_metrics[team], f"{teamdata['milestone']}-{team}-{organization}.csv"
        )
