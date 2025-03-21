import os

import pytz
from datetime import time

pr_tz = pytz.timezone("America/Puerto_Rico")
default_start_time = time(hour=8, minute=0)
default_end_time = time(hour=20, minute=0)


def getToken():
    return os.environ["GITHUB_API_TOKEN"]
