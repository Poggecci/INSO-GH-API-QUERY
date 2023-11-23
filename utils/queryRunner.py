import requests
from utils.constants import getToken


def run_graphql_query(query, variables=None):
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
        raise Exception(
            f"Query failed to run, status code {response.status_code}\n{response.text}"
        )

    # Return the JSON response
    return response.json()
