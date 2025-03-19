from datetime import datetime
from src.utils.discussions import calculateWeeklyDiscussionPenalties
from src.utils.models import MilestoneData
from src.utils.constants import pr_tz


def writeMilestoneToMarkdown(milestone_data: MilestoneData, md_file_path: str):
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


def writeSprintTaskCompletionToMarkdown(
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
            current_indicator = " [current]" if is_current_sprint else ""

            md_file.write(
                f" Sprint {sprint+1}{current_indicator}<br>{sprint_start.strftime('%Y/%m/%d, %I:%M %p')}<br>{sprint_end.strftime('%Y/%m/%d, %I:%M %p')} |"
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


def writeWeeklyDiscussionParticipationToMarkdown(
    participation: dict, weeks: int, md_file_path: str
):
    penalties = calculateWeeklyDiscussionPenalties(
        participation=participation, weeks=weeks
    )

    with open(md_file_path, mode="a") as md_file:
        md_file.write("\n## Weekly Discussion Participation\n\n")
        md_file.write("| Developer |")
        for week in range(weeks):
            md_file.write(f" Week #{week + 1} |")
        md_file.write(" Penalty |\n")
        md_file.write("|" + "---|" * (weeks + 2) + "\n")

        for dev in participation.keys():
            md_file.write(
                f"| {dev} | "
                + " | ".join(
                    [
                        "Yes" if week in participation[dev] else "No"
                        for week in range(weeks)
                    ]
                )
                + f" | {str(penalties[dev])} |\n"
            )


def writePointPercentByLabelToMarkdown(
    milestone_data: MilestoneData, md_file_path: str
):
    with open(md_file_path, mode="a") as md_file:
        md_file.write("\n## Point Percent by Label\n\n")
        first_read_done = False
        labels = []
        for dev, metrics in milestone_data.devMetrics.items():
            if not first_read_done:
                labels = list(metrics.pointPercentByLabel.keys())
                if len(labels) == 0:
                    md_file.write("There are no labels assigned to any issue\n")
                    break
                md_file.write("| Developer | " + " | ".join(labels) + " |\n")
                md_file.write("|---|" + "---|" * len(labels) + "\n")
                first_read_done = True
            md_file.write(
                f"| {dev} | "
                + " | ".join(
                    [
                        str(round(metrics.pointPercentByLabel[label], 1)) + "%"
                        for label in labels
                    ]
                )
                + " |\n"
            )


def writeLogsToMarkdown(log_file_path: str, md_file_path: str):
    with open(log_file_path, mode="r") as log_file:
        with open(md_file_path, mode="a") as md_file:
            md_file.write("# Metrics Generation Logs\n\n")
            md_file.write("| Message |\n")
            md_file.write("| ------- |\n")
            for log_message in log_file.readlines():
                md_file.write("| " + log_message.strip("\n") + " |\n")
