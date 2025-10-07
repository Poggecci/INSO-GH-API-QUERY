import csv
import json
import logging

from dotenv import load_dotenv
from src.generateLectureTopicTaskMetrics import getLectureTopicTaskMetrics
from src.getTeamMembers import getTeamMembers

from src.utils.models import LectureTopicTaskData


def met_quota(developer_tasks_by_milestone: dict[str, int], task_quota: int):
    milestones_worked = 0
    total_points = 0
    for points in developer_tasks_by_milestone.values():
        if points > 0:
            milestones_worked += 1
            total_points += points
    return total_points >= task_quota and milestones_worked >= 2


def write_lecture_topic_task_data_to_csv(
    ltt_data: LectureTopicTaskData, csv_file_path: str, task_quota: int
):
    with open(csv_file_path, mode="w", newline="") as csv_file:
        writer = csv.writer(csv_file)
        milestones = sorted(list(ltt_data.totalMilestones))
        writer.writerow(["Developer"] + milestones + ["Met Quota"])
        for (
            developer,
            tasks_by_milestone,
        ) in ltt_data.lectureTopicTasksByDeveloperByMilestone.items():
            writer.writerow(
                [developer]
                + [tasks_by_milestone.get(milestone, 0) for milestone in milestones]
                + [met_quota(tasks_by_milestone, task_quota)]
            )


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
        course_data = json.load(course_config)
    organization = course_data["organization"]
    metricsDirectory = course_data["metricsDirectory"]
    teams = course_data["teams"]
    lecture_topic_task_quota = course_data["lectureTopicTaskQuota"]
    print("Organization: ", course_data["organization"])
    lecture_topic_task_metrics_by_team = {}
    for team, team_data in teams.items():
        print("Team: ", team)
        managers = [manager["name"] for manager in team_data["managers"]]
        print("Managers: ", managers)
        members = getTeamMembers(organization, team)
        milestone = team_data["milestone"]
        print("Milestone: ", milestone)
        loggingLevels = [logging.ERROR, logging.INFO, logging.DEBUG]
        configVerbosity = int(team_data.get("verbosity", 1))
        if configVerbosity < 0 or configVerbosity >= len(loggingLevels):
            print(
                f"Verbosity value must be within [0, {len(loggingLevels)}). Default value 1 will be used."
            )
            configVerbosity = 1
        verbosity = loggingLevels[configVerbosity]
        logger = logging.getLogger(milestone)
        logger.setLevel(verbosity)
        logFileName = f"{milestone}-{team}-{organization}.log"
        logFileHandler = logging.FileHandler(logFileName)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        logFileHandler.setFormatter(formatter)
        logger.addHandler(logFileHandler)
        lecture_topic_task_metrics_by_team[team] = getLectureTopicTaskMetrics(
            org=organization,
            team=team,
            members=members,
            managers=managers,
            shouldCountOpenIssues=course_data.get("countOpenIssues", False),
            logger=logger,
        )
        os.makedirs(metricsDirectory, exist_ok=True)
        write_lecture_topic_task_data_to_csv(
            lecture_topic_task_metrics_by_team[team],
            f"{metricsDirectory}/Lecture Topic Tasks-{team}-{organization}.csv",
            lecture_topic_task_quota,
        )
