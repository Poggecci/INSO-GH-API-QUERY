import os

import pytz

pr_tz = pytz.timezone("America/Puerto_Rico")


def getToken():
    return os.environ["GITHUB_API_TOKEN"]
