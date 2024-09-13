from datetime import datetime
import json
import os
import logging
from src.generateTeamMetrics import getTeamMetricsForMilestone
from src.utils.constants import pr_tz
from src.getTeamMembers import get_team_members
from src.utils.models import MilestoneData


def write_milestone_data_to_md(milestone_data: MilestoneData, md_file_path: str):
    with open(md_file_path, mode="w") as md_file:
        md_file.write("# Milestone Data\n\n")
        md_file.write(f"## Date Generated: {datetime.now().date()}\n")
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


def write_sprint_task_completion_to_md(
    milestone_data: MilestoneData, md_file_path: str, minTasksPerSprint: int
):
    current_date = datetime.now(tz=pr_tz)
    with open(md_file_path, mode="a") as md_file:
        md_file.write("\n## Sprint Task Completion\n\n")

        # Write header row
        md_file.write("| Developer |")
        for sprint in range(milestone_data.sprints):
            sprint_start = milestone_data.startDate + (
                milestone_data.endDate - milestone_data.startDate
            ) * (sprint / milestone_data.sprints)
            sprint_end = milestone_data.startDate + (
                milestone_data.endDate - milestone_data.startDate
            ) * ((sprint + 1) / milestone_data.sprints)

            # Check if this is the current sprint
            is_current_sprint = sprint_start <= current_date <= sprint_end
            current_indicator = "[current] " if is_current_sprint else ""

            md_file.write(
                f" {current_indicator}S{sprint+1} ({sprint_start.strftime('%Y/%m/%d')}-{sprint_end.strftime('%Y/%m/%d')}) |"
            )
        md_file.write("\n")

        # Write separator row
        md_file.write("|" + "---|" * (milestone_data.sprints + 1) + "\n")

        # Write data rows
        for developer, metrics in milestone_data.devMetrics.items():
            md_file.write(f"| {developer} |")
            for sprint_tasks in metrics.tasksBySprint:
                md_file.write(f" {sprint_tasks}/{minTasksPerSprint} |")
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
    logger.warning(
        'Using V1 Metrics is deprecated. New projects should use V2 metrics. Please update your config to have "version":"2.0".'
    )

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
        startDate = datetime.now(tz=pr_tz)
        endDate = datetime.now(tz=pr_tz)
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
            sprints=1,
            minTasksPerSprint=0,
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
            startDate = pr_tz.localize(
                datetime.fromisoformat(f"{mData.get('startDate')}T00:00:00")
            )
            endDate = pr_tz.localize(
                datetime.fromisoformat(f"{mData.get('endDate')}T23:59:59")
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
            startDate = datetime.now(tz=pr_tz)
            endDate = datetime.now(tz=pr_tz)
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
                sprints=config.get("sprints", 2),
                minTasksPerSprint=config.get("minTasksPerSprint", 1),
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
        write_sprint_task_completion_to_md(
            milestone_data=team_metrics,
            md_file_path=output_markdown_path,
            minTasksPerSprint=config.get("minTasksPerSprint", 1),
        )
        write_log_data_to_md(
            log_file_path=logFileName, md_file_path=output_markdown_path
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Please pass in the path to your config (See README.md for how to do it)")
        exit(0)
    _, course_config_file, *_ = sys.argv
    with open(course_config_file) as course_config:
        course_data: dict = json.load(course_config)
    version: str = course_data.get("version", "1.0")
    if version.startswith("1."):
        generateMetricsFromV1Config(config=course_data)
    elif version.startswith("2."):
        generateMetricsFromV2Config(config=course_data)
