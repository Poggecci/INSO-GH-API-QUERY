from datetime import datetime
import logging
from src.generateTeamMetrics import getTeamMetricsForMilestone
from src.getTeamMembers import getTeamMembers
from src.utils.constants import pr_tz
from src.io.markdown import (
    writeLogsToMarkdown,
    writeMilestoneToMarkdown,
)
from src.utils.models import MilestoneData


def generateMetricsFromV1Config(config: dict):
    team = config["projectName"]
    organization = "uprm-inso4116-2024-2025-S1"
    milestone = config["milestoneName"]
    managers = config["managers"]
    print("Team: ", team)
    print("Managers: ", managers)
    print("Milestone: ", milestone)
    members = getTeamMembers(organization, team)
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
    writeMilestoneToMarkdown(
        milestone_data=team_metrics, md_file_path=output_markdown_path
    )
    writeLogsToMarkdown(log_file_path=logFileName, md_file_path=output_markdown_path)
