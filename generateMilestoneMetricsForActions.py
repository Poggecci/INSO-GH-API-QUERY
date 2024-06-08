from datetime import datetime
import json
import os
import logging
from generateTeamMetrics import getTeamMetricsForMilestone

from getTeamMembers import get_team_members
from utils.models import MilestoneData


def write_milestone_data_to_md(milestone_data: MilestoneData, md_file_path: str):
    with open(md_file_path, mode="w") as md_file:
        md_file.write("# Milestone Data\n\n")
        md_file.write(f"## Date Generated: {datetime.now().date}\n")
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
        md_file.write("\n")


def write_log_data_to_md(log_file_path: str, md_file_path: str):
    with open(log_file_path, mode="r") as log_file:
        with open(md_file_path, mode="a") as md_file:
            md_file.write("# Metrics Generation Logs\n\n")
            md_file.write("| Message |\n")
            md_file.write("| ------- |\n")
            for log_message in log_file.readlines():
                md_file.write("| " + log_message.strip("\n") + " |\n")


def generateMetricsFromV1Config(config: dict):
    team = config["projectName"]
    organization = os.environ["ORGANIZATION"]
    milestone = config["milestoneName"]
    managers = config["managers"]
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

    logger = logging.getLogger(milestone)
    logFileName = f"{milestone}-{team}-{organization}.log"
    logFileHandler = logging.FileHandler(logFileName)
    formatter = logging.Formatter("%(levelname)s: %(message)s")
    logFileHandler.setFormatter(formatter)
    logger.addHandler(logFileHandler)

    try:
        startDate = datetime.fromisoformat(
            f"{config.get('milestoneStartDate')}T00:00:00.000Z"
        )
        endDate = datetime.fromisoformat(
            f"{config.get('milestoneEndDate')}T23:59:59.000Z"
        )
        useDecay = True
    except Exception as e:
        print(f"Error while parsing milestone dates: {e}")
        print(
            "Warning: startDate and/or endDate couldn't be interpreted, proceeding without decay."
        )
        logger.error(f"Error while parsing milestone dates: {e}")
        logger.warning(
            f"startDate and/or endDate for {milestone} couldn't be interpreted, proceeding without decay."
        )
        startDate = datetime.now()
        endDate = datetime.now()
        useDecay = False
    team_metrics = MilestoneData()
    try:
        team_metrics = getTeamMetricsForMilestone(
            org=organization,
            team=team,
            milestone=milestone,
            milestoneGrade=config.get("projectedGroupGrade", 100.0),
            members=members,
            managers=managers,
            startDate=startDate,
            endDate=endDate,
            useDecay=useDecay,
            shouldCountOpenIssues=config.get("countOpenIssues", False),
            logger=logger,
        )
    except Exception as e:
        logger.critical(e)
    strippedMilestoneName = milestone.replace(" ", "")
    output_markdown_path = f"{strippedMilestoneName}-{team}-{organization}.md"
    write_milestone_data_to_md(
        milestone_data=team_metrics, md_file_path=output_markdown_path
    )
    write_log_data_to_md(log_file_path=logFileName, md_file_path=output_markdown_path)


def generateMetricsFromV2Config(config: dict):
    team = config["projectName"]
    organization = os.environ["ORGANIZATION"]
    milestones: dict = config["milestones"]
    managers = config["managers"]
    print("Team: ", team)
    print("Managers: ", managers)
    print("Milestones: ", ", ".join(milestones.keys()))
    members = get_team_members(organization, team)
    if len(members) == 0:
        print(
            "Warning: No team members found. This likely means your projectName isn't "
            "the same as your Team name on Github. Remember both the Github Project and "
            "The Github Team need to have the same name (this is whitespace and case sensitive!)."
        )
    for milestone, mData in milestones.items():
        logger = logging.getLogger(milestone)
        logFileName = f"{milestone}-{team}-{organization}.log"
        logFileHandler = logging.FileHandler(logFileName)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        logFileHandler.setFormatter(formatter)
        logger.addHandler(logFileHandler)

        try:
            startDate = datetime.fromisoformat(
                f"{mData.get('startDate')}T00:00:00.000Z"
            )
            endDate = datetime.fromisoformat(f"{mData.get('endDate')}T23:59:59.000Z")
            useDecay = True
        except Exception as e:
            print(f"Error while parsing milestone dates: {e}")
            print(
                "Warning: startDate and/or endDate couldn't be interpreted, proceeding without decay."
            )
            logger.error(f"Error while parsing milestone dates: {e}")
            logger.warning(
                f"startDate and/or endDate for {milestone} couldn't be interpreted, proceeding without decay."
            )
            startDate = datetime.now()
            endDate = datetime.now()
            useDecay = False
        team_metrics = MilestoneData()
        try:
            team_metrics = getTeamMetricsForMilestone(
                org=organization,
                team=team,
                milestone=milestone,
                milestoneGrade=mData.get("projectedGroupGrade", 100.0),
                members=members,
                managers=managers,
                startDate=startDate,
                endDate=endDate,
                useDecay=useDecay,
                shouldCountOpenIssues=config.get("countOpenIssues", False),
                logger=logger,
            )
        except Exception as e:
            logger.critical(e)
        strippedMilestoneName = milestone.replace(" ", "")
        output_markdown_path = f"{strippedMilestoneName}-{team}-{organization}.md"
        write_milestone_data_to_md(
            milestone_data=team_metrics, md_file_path=output_markdown_path
        )
        write_log_data_to_md(
            log_file_path=logFileName, md_file_path=output_markdown_path
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        exit(0)
    _, course_config_file, *_ = sys.argv
    with open(course_config_file) as course_config:
        course_data: dict = json.load(course_config)
    version = course_data.get("version", "1.0")
    match version:
        case "1.0":
            generateMetricsFromV1Config(config=course_data)
        case "2.0":
            generateMetricsFromV2Config(config=course_data)
