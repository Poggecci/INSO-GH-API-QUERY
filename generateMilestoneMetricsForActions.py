from datetime import datetime
import json
import os
from generateTeamMetrics import getTeamMetricsForMilestone

from getTeamMembers import get_team_members
from utils.models import MilestoneData


def write_milestone_data_to_md(milestone_data: MilestoneData, md_file_path: str):
    with open(md_file_path, mode="w") as md_file:
        md_file.write("# Milestone Data\n\n")
        md_file.write(
            "| Developer | Points Closed | Percent Contribution | Projected Grade | Lecture Topic Tasks |\n"
        )
        md_file.write(
            "| --------- | ------------- | -------------------- | --------------- | ------------------- |\n"
        )
        totalLectureTopicTasks = 0
        for developer, metrics in milestone_data.devMetrics.items():
            totalLectureTopicTasks += metrics.lectureTopicTasksClosed
            md_file.write(
                f"| {developer} | {round(metrics.pointsClosed, 1)} | {round(metrics.percentContribution, 1)}% | {round(metrics.expectedGrade, 1)}% | {metrics.lectureTopicTasksClosed} |\n"
            )
        md_file.write(
            f"| Total | {milestone_data.totalPointsClosed} | /100% | /100% | {totalLectureTopicTasks} |\n"
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        exit(0)
    _, course_config_file, *_ = sys.argv
    with open(course_config_file) as course_config:
        course_data: dict = json.load(course_config)
    team = course_data["projectName"]
    organization = os.environ["ORGANIZATION"]
    milestone: str = course_data["milestoneName"]
    managers = course_data["managers"]
    print("Team: ", team)
    print("Managers: ", managers)
    print("Milestone: ", milestone)
    members = get_team_members(organization, team)
    if len(members) == 0:
        print(
            "Warning: No team members found. This likely means your projectName isn't "
            "the same as your Team name on Github. Remember both the Github Project and "
            "The Github Team need to have the same name (this is whitespace and case sensitive!)."
        )

    try:
        startDate = datetime.fromisoformat(
            f"{course_data.get('milestoneStartDate')}T00:00:00.000Z"
        )
        endDate = datetime.fromisoformat(
            f"{course_data.get('milestoneEndDate')}T23:59:59.000Z"
        )
        useDecay = True
    except Exception as e:
        print(f"Error while parsing milestone dates: {e}")
        print(
            "Warning: milestoneStartDate and/or milestoneEndDate couldn't be interpreted, proceeding without decay."
        )
        startDate = datetime.now()
        endDate = datetime.now()
        useDecay = False
    team_metrics = getTeamMetricsForMilestone(
        org=organization,
        team=team,
        milestone=milestone,
        milestoneGrade=course_data.get("projectedMilestoneGroupGrade", 100.0),
        members=members,
        managers=managers,
        startDate=startDate,
        endDate=endDate,
        useDecay=useDecay,
        shouldCountOpenIssues=course_data.get("countOpenIssues", False),
    )
    strippedMilestoneName = milestone.replace(" ", "")
    write_milestone_data_to_md(
        team_metrics, f"{strippedMilestoneName}-{team}-{organization}.md"
    )
