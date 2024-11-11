import csv
import json
from datetime import datetime

from dotenv import load_dotenv
from src.utils.constants import pr_tz
from src.generateTeamMetrics import getTeamMetricsForMilestone
from src.getTeamMembers import getTeamMembers

from src.utils.models import MilestoneData


def writeMilestoneToCsv(milestone_data: MilestoneData, csv_file_path: str):
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


def ensureDatetimeLocalized(aDateTime: datetime) -> datetime:
    if aDateTime.tzinfo is None or aDateTime.tzinfo.utcoffset(aDateTime) is None:
        return pr_tz.localize(aDateTime)
    else:
        return aDateTime


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        exit(0)
    _, course_config_file, *_ = sys.argv
    load_dotenv()
    # idk why this isn't working, so hardcode for now. Kinda had to anyway cuz managers are hard coded rn
    # teams = get_teams(org)
    with open(course_config_file) as course_config:
        config_dict = json.load(course_config)

    if config_dict.get("version", "1.0").startswith("1."):
        organization = config_dict["organization"]
        metricsDirectory = config_dict["metricsDirectory"]
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
            startDate = ensureDatetimeLocalized(
                datetime.fromisoformat(
                    config_dict["milestoneStartsOn"],
                )
            )
            endDate = ensureDatetimeLocalized(
                datetime.fromisoformat(config_dict["milestoneEndsOn"])
            )
            useDecay = True

        print("Organization: ", organization)

        team_metrics = {}
        for team, teamdata in teams_and_teamdata.items():
            print("Team: ", team)
            print("Managers: ", teamdata["managers"])
            print("Milestone: ", teamdata["milestone"])
            members = getTeamMembers(organization, team)
            team_metrics[team] = getTeamMetricsForMilestone(
                org=organization,
                team=team,
                milestone=teamdata["milestone"],
                milestoneGrade=teamdata["milestoneGrade"],
                members=members,
                managers=[manager["name"] for manager in teamdata["managers"]],
                startDate=startDate,
                endDate=endDate,
                useDecay=useDecay,
                sprints=config_dict.get("sprints", 2),
                minTasksPerSprint=config_dict.get("minTasksPerSprint", 1),
            )
            os.makedirs(metricsDirectory, exist_ok=True)
            writeMilestoneToCsv(
                team_metrics[team],
                f"{metricsDirectory}/{teamdata['milestone']}-{team}-{organization}.csv",
            )
