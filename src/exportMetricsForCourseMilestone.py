import csv
import json
from datetime import datetime
from src.utils.constants import pr_tz
from src.generateTeamMetrics import getTeamMetricsForMilestone
from src.getTeamMembers import get_team_members

from src.utils.models import MilestoneData


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
        config_dict = json.load(course_config)

    if config_dict.get("version", "1.0").startswith("1."):
        organization = config_dict["organization"]
        teams_and_teamdata = config_dict["teams"]
        if (
            config_dict.get("milestoneStartsOn", None) is None
            or not config_dict["milestoneStartsOn"]
            or config_dict["milestoneStartsOn"] is None
            or config_dict.get("milestoneEndsOn", None) is None
            or config_dict["milestoneEndsOn"] is None
            or not config_dict["milestoneEndsOn"]
        ):
            startDate = datetime.now(tz=pr_tz)
            endDate = datetime.now(tz=pr_tz)
            useDecay = False
        else:
            startDate = pr_tz.localize(
                datetime.fromisoformat(
                    config_dict["milestoneStartsOn"],
                )
            )
            endDate = pr_tz.localize(
                datetime.fromisoformat(config_dict["milestoneEndsOn"])
            )
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
                sprints=config_dict.get("sprints", 2),
                minTasksPerSprint=config_dict.get("minTasksPerSprint", 1),
            )
            write_milestone_data_to_csv(
                team_metrics[team], f"{teamdata['milestone']}-{team}-{organization}.csv"
            )
