import csv
import json
from src.generateLectureTopicTaskMetrics import getLectureTopicTaskMetrics
from src.getTeamMembers import getTeamMembers

from src.utils.models import LectureTopicTaskData


def write_lecture_topic_task_data_to_csv(
    ltt_data: LectureTopicTaskData, csv_file_path: str, task_quota: int
):
    with open(csv_file_path, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Developer", "Lecture Topic Tasks Completed", "Met Quota"])
        # writer.writerow(["Total", ltt_data.totalLectureTopicTasks, "N/A"])
        for developer, tasks_closed in ltt_data.lectureTopicTasksByDeveloper.items():
            writer.writerow([developer, tasks_closed, tasks_closed >= task_quota])


if __name__ == "__main__":
    import sys
    import os

    if len(sys.argv) < 2:
        exit(0)
    _, course_config_file, *_ = sys.argv
    # idk why this isn't working, so hardcode for now. Kinda had to anyway cuz managers are hard coded rn
    # teams = get_teams(org)
    with open(course_config_file) as course_config:
        course_data = json.load(course_config)
    organization = course_data["organization"]
    metricsDirectory = course_data["metricsDirectory"]
    teams_and_managers = course_data["teams"]
    lecture_topic_task_quota = course_data["lectureTopicTaskQuota"]
    print("Organization: ", course_data["organization"])
    lecture_topic_task_metrics_by_team = {}
    for team, managers in teams_and_managers.items():
        print("Team: ", team)
        print("Managers: ", managers)
        members = getTeamMembers(organization, team)
        lecture_topic_task_metrics_by_team[team] = getLectureTopicTaskMetrics(
            org=organization, team=team, members=members
        )
        os.makedirs(metricsDirectory, exist_ok=True)
        write_lecture_topic_task_data_to_csv(
            lecture_topic_task_metrics_by_team[team],
            f"{metricsDirectory}/Lecture Topic Tasks-{team}-{organization}.csv",
            lecture_topic_task_quota,
        )
