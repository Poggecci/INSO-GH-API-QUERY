from datetime import datetime
from src.utils.models import MilestoneData
from src.utils.constants import pr_tz


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
