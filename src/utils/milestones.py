from src.utils.models import Milestone, ParsingError


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

    # Extract the fields from the milestone dictionary
    url: str | None = milestone_dict.get("url")
    title: str = milestone_dict[
        "title"
    ]  # This is required, so we let it raise KeyError if missing

    # Return the populated Milestone dataclass
    return Milestone(url=url, title=title)
