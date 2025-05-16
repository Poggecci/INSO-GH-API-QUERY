from datetime import datetime
import json
import os
import logging
import sys
from typing import Any
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
from src.utils.parseDateTime import (
    get_milestone_start,
    get_milestone_end,
    safe_parse_iso_date,
)
from src.utils.autoExtractMilestone import auto_extract_milestone
import argparse


def generateMetricsFromV2Config(
    config: dict[str, Any], optimize_milestone_fetch: bool = False
):
    team = config["projectName"]
    organization = os.environ["ORGANIZATION"]
    milestones: dict[str, Any] = config["milestones"]
    managers = config["managers"]
    print("Team: ", team)
    print("Managers: ", managers)
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

    if optimize_milestone_fetch:
        milestone = auto_extract_milestone(
            datetime.now(tz=pr_tz).date(),
            [
                (m, safe_parse_iso_date(data.get("startDate")))
                for m, data in milestones.items()
            ],
        )
        if milestone is not None:
            milestones = {milestone: milestones[milestone]}

    print("Milestones: ", ", ".join(milestones.keys()))
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
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument("course_config_file")
    parser.add_argument(
        "--no-optimize-milestone-fetch", action="store_false", default=True
    )
    args = parser.parse_args()
    course_config_file = args.course_config_file
    with open(course_config_file) as course_config:
        course_data: dict = json.load(course_config)
    version: str = course_data.get("version", "1.0")
    if version.startswith("1."):
        generateMetricsFromV1Config(config=course_data)
    elif version.startswith("2."):
        generateMetricsFromV2Config(
            config=course_data,
            optimize_milestone_fetch=args.no_optimize_milestone_fetch,
        )
