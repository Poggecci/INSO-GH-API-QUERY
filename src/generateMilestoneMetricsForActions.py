from datetime import datetime
import json
import os
import logging
from src.generateTeamMetrics import getTeamMetricsForMilestone
from src.io.markdown import (
    write_log_data_to_md,
    write_milestone_data_to_md,
    write_sprint_task_completion_to_md,
)
from src.legacy.generateMilestoneMetricsForActions import generateMetricsFromV1Config
from src.utils.constants import pr_tz
from src.getTeamMembers import get_team_members
from src.utils.models import MilestoneData


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
            logger.exception(f"Error while parsing milestone dates: {e}")
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
            logger.exception(e)
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
