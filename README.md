# Team Metrics Generator

This script generates team metrics for a specified milestone in a GitHub organization. It collects data on points closed and percent contribution for each developer in the specified teams and outputs the results to CSV files.

## Usage

### Setup

1. Ensure you have the necessary dependencies installed:

```bash
poetry install
```

2. You must create a GitHub classic personal access token with the permissions `read:org`
   and `read:project`.
3. Assign your Github classic PAT to the environment variable `GITHUB_API_TOKEN`. This
   allows you to keep the token in an encrypted file. For example,

```bash
export GITHUB_API_TOKEN=`YOUR_PERSONAL_ACCESS_TOKEN`
```

### Points Closed Team Metrics

1. The course is described in a JSON file. The fields of the JSON file are
   - `organization` this will be used as the name of the organization
   - `milestoneStartsOn` the `datetime` at which the milestone starts
   - `milestoneEndsOn` the `datetime` at which the milestone ends
     if either one of `milestoneStartsOn` or `milestoneEndsOn` is missing then there will
     not be any use of the decay function in the calculation of the score of issues
   - `teams` this field is a list of key/value pairs. The key of each pair is the team
     name. It _must_ also be the name of the project board owned by that team from which the
     closed issues, with their urgency and difficulty can be collected. The value of each
     pair is a JSON with the fields
     - `managers` which contains a list of the GitHub logins that belong to the managers
       of the team and therefore do not get any points for closing issues, even if they
       were assigned to them.
     - `milestone` which must be the name of the milestone to use, so that different
       projects can use different milestone names
     - `milestoneGrade` which specifies the maximum grade achievable for this milestone, determined by the professor based on the team's overall performance (what they promised vs delivered, etc.).
2. Run the script from the command line:

```bash
poetry run python exportMetricsForCourseMilestone.py <json_config_file_path>
```

#### Example

```bash
poetry run python exportMetricsForCourseMilestone.py exampleConfig.json
```

The script will generate CSV files containing team metrics for each specified team. The CSV files will be named `<milestone>-<team>-<organization>.csv`.

### Lecture Topic Tasks

1. The course is described in a JSON file. The fields of the JSON file are

   - `organization` this will be used as the name of the organization
   - `teams` this field is a list of key/value pairs. The key of each pair is the team name. It must also be the name of the project board owned by that team from which the closed issues, with their urgency and difficulty can be collected. The value of each pair is a JSON with the fields

   - `managers` which contains a list of the GitHub logins that belong to the managers
     of the team and therefore do not get any points for closing issues, even if they
     were assigned to them.

2. Run the script from the command line:

```bash
poetry run python exportMetricsForLectureTopicTasks.py <json_config_file_path>
```

#### Example

```bash
poetry run python exportMetricsForLectureTopicTasks.py exampleConfig.json
```

The script will generate CSV files containing team metrics for each specified team. The CSV files will be named `Lecture Topic Tasks-<team>-<organization>.csv`.
