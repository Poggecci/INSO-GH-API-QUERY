from src.utils.models import Milestone, ParsingError
from datetime import datetime


def parseMilestone(milestone_dict: dict, /) -> Milestone:
    """
    Parses a dictionary representing a GitHub Milestone fetched through the GraphQL API and returns a Milestone object.

    Args:
        milestone_dict (dict): The dictionary containing the details of the GitHub milestone, typically retrieved from the API.
                             This dictionary is expected to have fields like 'url' and 'title'.

    Returns:
        Milestone: An instance of the Milestone dataclass populated with the url and title.

    Raises:
        ParsingError: If the milestone dictionary is missing or empty.
        KeyError: If required fields ('url' or 'title') are missing from the milestone dictionary.
    """
    # Validate that we have milestone data to parse
    if (
        milestone_dict is None
        or not isinstance(milestone_dict, dict)
        or len(milestone_dict) < 1
    ):
        raise ParsingError(
            "Missing, empty, or incorrectly typed milestone data. This could be due to permission issues or API changes."
        )

    url: str = milestone_dict["url"]
    title: str = milestone_dict["title"]
    if "dueOn" in milestone_dict:
        dueOn = datetime.fromisoformat(milestone_dict["dueOn"])
    else:
        dueOn = None

    return Milestone(url=url, title=title, dueOn=dueOn)
