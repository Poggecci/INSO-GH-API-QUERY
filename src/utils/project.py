from src.utils.models import ParsingError, Project


def parseProject(project_dict: dict, /) -> Project:
    """
    Parses a dictionary representing a GitHub Project (v2) fetched through the GraphQL API and returns a Project object.

    Args:
        project_dict (dict): The dictionary containing the details of the GitHub project, typically retrieved from the API.
                           This dictionary is expected to have fields like 'title', 'number', 'public', and 'url'.

    Returns:
        Project: An instance of the Project dataclass populated with all the relevant project details such as
                name (title), number, url, and public status.

    Raises:
        ParsingError: If the project dictionary is missing or empty.
        KeyError: If the structure of the project_dict does not match the expected format, either due to missing fields
                 or permission errors. Required fields: 'title', 'number', 'url', 'public'
    """
    # Validate that we have project data to parse
    if (
        project_dict is None
        or not isinstance(project_dict, dict)
        or len(project_dict) < 1
    ):
        raise ParsingError(
            "Missing, empty, or incorrectly typed project data. This could be due to permission issues or API changes."
        )

    # All fields are required according to the API schema, so we let KeyError propagate if any are missing
    name = project_dict["title"]
    number = int(project_dict["number"])
    url = project_dict["url"]
    public = project_dict["public"]

    # Return the populated Project dataclass
    return Project(name=name, number=number, url=url, public=public)
