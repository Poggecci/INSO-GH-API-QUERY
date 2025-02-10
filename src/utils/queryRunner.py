from typing import Any
import requests
from src.utils.constants import getToken


def runGraphqlQuery(*, query: str, variables: dict | None = None) -> dict:
    """Execute a GraphQL query against the GitHub API and return the response data.

    This function sends a POST request to GitHub's GraphQL API endpoint with the provided
    query and optional variables. It handles authentication using a bearer token and
    validates the response. If successful, it returns the contents of the "data" field
    from the JSON response.

    Args:
        query: The GraphQL query string to execute.
        variables: Dictionary of variables to pass with the query.
            Defaults to None.

    Returns:
        dict: The contents of the "data" field from the successful GraphQL response.

    Raises:
        ConnectionError: In two cases:
            1. If the HTTP request fails (status code != 200), with the status code
               and response text in the error message.
            2. If the response contains an "errors" field, with the GraphQL error
               details in the error message.

    Example:
        >>> query = '''
        ... query($owner: String!, $name: String!) {
        ...     repository(owner: $owner, name: $name) {
        ...         name
        ...         description
        ...     }
        ... }'''
        >>> variables = {"owner": "octocat", "name": "Hello-World"}
        >>> result = runGraphqlQuery(query=query, variables=variables)
        >>> print(result["repository"]["name"])
        'Hello-World'
    """
    # GitHub GraphQL API endpoint
    url = "https://api.github.com/graphql"
    token = getToken()

    # Set up the request headers
    headers = {
        "Authorization": f"bearer {token}",
        "Content-Type": "application/json",
    }

    # Set up the request payload
    payload = {
        "query": query,
        "variables": variables,
    }

    # Make the request to the GitHub GraphQL API
    response = requests.post(url, headers=headers, json=payload)

    # Check for errors
    if response.status_code != 200:
        raise ConnectionError(
            f"Query failed to run, status code {response.status_code}\n{response.text}"
        )
    response_dict = response.json()
    if "errors" in response_dict:
        raise ConnectionError(f"Error executing query: {response_dict['errors']}")
    return response_dict["data"]
