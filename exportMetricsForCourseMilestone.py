import csv
from generateTeamMetrics import getTeamMetricsForMilestone
from getTeamMembers import get_team_members

from utils.models import MilestoneData


def write_milestone_data_to_csv(milestone_data: MilestoneData, csv_file_path: str):
    with open(csv_file_path, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Developer", "Points Closed", "Percent Contribution"])
        writer.writerow(["Total", milestone_data.totalPointsClosed, "100"])
        for developer, metrics in milestone_data.devMetrics.items():
            writer.writerow(
                [developer, metrics.pointsClosed, metrics.percentContribution]
            )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        exit(0)
    _, org, milestone, *_ = sys.argv
    # idk why this isn't working, so hardcode for now. Kinda had to anyway cuz managers are hard coded rn
    # teams = get_teams(org)
    teams_and_managers = {"College Toolbox": ["EdwinC1339", "Ryan8702"]}
    team_metrics = {}
    for team, managers in teams_and_managers.items():
        members = get_team_members(org, team)
        team_metrics[team] = getTeamMetricsForMilestone(
            org=org,
            team=team,
            milestone=milestone,
            members=members,
            managers=managers,
        )
    for team, metrics in team_metrics.items():
        write_milestone_data_to_csv(metrics, f"{milestone}-{team}-{org}.csv")
