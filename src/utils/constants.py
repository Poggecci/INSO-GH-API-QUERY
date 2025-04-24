import os

import pytz
from datetime import time

pr_tz = pytz.timezone("America/Puerto_Rico")
default_start_time = time(hour=8, minute=0)
default_end_time = time(hour=20, minute=0)
json_time_placeholder = "[time]"
json_dumps_dir = "dumps"


def getToken():
    return os.environ["GITHUB_API_TOKEN"]
