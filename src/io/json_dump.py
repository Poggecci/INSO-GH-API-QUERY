from datetime import datetime
import os
import re
from src.utils.models import MilestoneData
from src.utils.constants import json_time_placeholder, json_dumps_dir


def smartDumpMilestoneMetrics(milestone_data: MilestoneData, json_file_format: str):
    time_regex = r"\d{8}T\d{6}"
    files = sorted(
        [
            f
            for f in os.listdir(json_dumps_dir)
            if re.match(
                rf"^{json_file_format.replace(json_time_placeholder, time_regex)}$", f
            )
        ]
    )
    if len(files) > 0:
        most_recent = json_dumps_dir + "/" + files[-1]
        metrics = loadMilestoneMetrics(most_recent)
        if milestone_data == metrics:
            print(
                "Generated metrics equal to most recent metrics. Metrics will not be dumped..."
            )
            return

    file_name = (
        json_dumps_dir
        + "/"
        + json_file_format.replace(
            json_time_placeholder, datetime.now().strftime("%Y%m%dT%H%M%S")
        )
    )
    dumpMilestoneMetrics(milestone_data, json_file_path=file_name)
    print(f"Metrics dumped to file {file_name}")


def dumpMilestoneMetrics(milestone_data: MilestoneData, json_file_path: str):
    os.makedirs(json_dumps_dir, exist_ok=True)
    with open(json_file_path, mode="w") as file:
        file.write(milestone_data.model_dump_json(indent=2))


def loadMilestoneMetrics(json_file_path: str) -> MilestoneData:
    with open(json_file_path, mode="r") as file:
        return MilestoneData.model_validate_json(file.read())
