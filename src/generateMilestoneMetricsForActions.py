from datetime import datetime
import json
import os
import logging
import sys
from dotenv import load_dotenv
from src.generateTeamMetrics import getTeamMetricsForMilestone
from src.io.markdown import (
    writeLogsToMarkdown,
    writeMilestoneToMarkdown,
    writePointPercentByLabelToMarkdown,
    writeSprintTaskCompletionToMarkdown,
    writeWeeklyDiscussionParticipationToMarkdown,
)
from src.legacy.generateMilestoneMetricsForActions import generateMetricsFromV1Config
from src.utils.constants import pr_tz
from src.getTeamMembers import getTeamMembers
from src.utils.discussions import (
    findWeeklyDiscussionParticipation,
    getDiscussions,
    getWeeks,
)
from src.utils.models import MilestoneData
from src.utils.parseDateTime import get_milestone_start, get_milestone_end


def generateMetricsFromV2Config(config: dict):
    team = config["projectName"]
    organization = os.environ["ORGANIZATION"]
    milestones: dict = config["milestones"]
    managers = config["managers"]
    print("Team: ", team)
    print("Managers: ", managers)
    print("Milestones: ", ", ".join(milestones.keys()))
    members = getTeamMembers(organization, team)
    if len(members) == 0:
        print(
            "Warning: No team members found. This likely means your projectName isn't "
            "the same as your Team name on Github. Remember both the Github Project and "
            "The Github Team need to have the same name (this is whitespace and case sensitive!)."
        )

    loggingLevels = [logging.ERROR, logging.INFO, logging.DEBUG]
    configVerbosity = int(config.get("verbosity", 1))
    if configVerbosity < 0 or configVerbosity >= len(loggingLevels):
        print(
            f"Verbosity value must be within [0, {len(loggingLevels)}). Default value 1 will be used."
        )
        configVerbosity = 1
    verbosity = loggingLevels[configVerbosity]

    for milestone, mData in milestones.items():
        logger = logging.getLogger(milestone)
        logger.setLevel(verbosity)
        logFileName = f"{milestone}-{team}-{organization}.log"
        logFileHandler = logging.FileHandler(logFileName)
        formatter = logging.Formatter("%(levelname)s: %(message)s")
        logFileHandler.setFormatter(formatter)
        logger.addHandler(logFileHandler)

        try:
            startDate = get_milestone_start(mData.get("startDate"))
            endDate = get_milestone_end(mData.get("endDate"))
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
        discussionParticipation = {}
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
            discussionParticipation = findWeeklyDiscussionParticipation(
                members=set(members),
                discussions=getDiscussions(org=organization, team=team),
                milestone=milestone,
                milestoneStart=startDate,
                milestoneEnd=endDate,
                logger=logger,
            )
        except Exception as e:
            logger.exception(e)
        strippedMilestoneName = milestone.replace(" ", "")
        output_markdown_path = f"{strippedMilestoneName}-{team}-{organization}.md"
        writeMilestoneToMarkdown(
            milestone_data=team_metrics, md_file_path=output_markdown_path
        )
        writeSprintTaskCompletionToMarkdown(
            milestone_data=team_metrics,
            md_file_path=output_markdown_path,
            minTasksPerSprint=config.get("minTasksPerSprint", 1),
        )
        writeWeeklyDiscussionParticipationToMarkdown(
            participation=discussionParticipation,
            weeks=getWeeks(milestoneStart=startDate, milestoneEnd=endDate),
            md_file_path=output_markdown_path,
            logger=logger,
        )
        writePointPercentByLabelToMarkdown(
            milestone_data=team_metrics, md_file_path=output_markdown_path
        )
        writeLogsToMarkdown(
            log_file_path=logFileName, md_file_path=output_markdown_path
        )


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Please pass in the path to your config (See README.md for how to do it)")
        exit(0)
    _, course_config_file, *_ = sys.argv
    load_dotenv()
    with open(course_config_file) as course_config:
        course_data: dict = json.load(course_config)
    version: str = course_data.get("version", "1.0")
    if version.startswith("1."):
        generateMetricsFromV1Config(config=course_data)
    elif version.startswith("2."):
        generateMetricsFromV2Config(config=course_data)
