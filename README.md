# Team Metrics Generator

This script generates team metrics for a specified milestone in a GitHub organization. It collects data on points closed and percent contribution for each developer in the specified teams and outputs the results to CSV files. You can now also use Github Actions generate the metrics as a Markdown that is stored in a separate branch of your repository. Checkout [this](https://github.com/Poggecci/INSO-GH-API-QUERY/blob/main/scoring.md) to learn more about how issues are counted.

## Usage

### Github Actions (Recommended for students)

When using this repo through actions, the generated metrics will be placed in a `metrics/` folder in your repository on the `inso-metrics` branch. If you have the repository permissions to let Actions create pull requests, the workflow will also create a pull request to merge the metrics onto the main branch.

#### Setup

##### Secrets Setup

1. Go to `https://github.com/settings/tokens` and generate a _Classic_ Personal Access Token (PAT).
2. Name the token something meaningful like "INSO Metrics Generation Token"
3. Ensure the token has the `read:org` and `read:project` permissions.
4. Set your expiration to the final date you expect to require the metrics (or set no expiration, though this is not recommended).
5. Copy the token somewhere private, we will be utilizing it promptly
6. Navigate to the repository you would like to generate metrics for
7. Go to the **Settings** page.
8. On the sidebar, press the _Secrets and variables_ dropdown, and select **Actions**.
9. Press the **New Repository Secret** button.
10. Create a secret with the name `GH_API_TOKEN` and put the PAT you generated as the value.

##### Config File Setup

1. On the main branch of your repository, create a file named `gh_metrics_config.json`.
2. Populate the .json file with the following fields:

- `version` : Version of the config used for the project. The latest version is `2.0`.
- `projectName` : Name of the Github Project associated with your repository. **Must** also be the name of the team on Github (case-sensitive).
- `managers` : a list of the GitHub logins (usernames) that belong to the managers (case-sensitive).
- `milestones` : a nested JSON object mapping each milestone's name to its details including:
  - `startDate`: start date of the milestone in the format YYYY-MM-DD (not including this field will disable decay)
  - `endDate`: end date of the milestone in the format YYYY-MM-DD (not including this field will disable decay)
  - `projectedGroupGrade`: the maximum grade achievable for this milestone, determined by the professor based on the team's overall performance (defaults to `100.0`)
- `lectureTopicTaskQuota` : number of lecture topic tasks expected to be completed by each developer by the end of the course. Reminder that there **is no** required number of lecture topic tasks per developer per milestone. Only a quota that each developer must fill by the end of the course. Defaults to `0`.
- `countOpenIssues` : boolean flag to determine if open issues should be included in the score calculation. Useful when trying to estimate how the developer points will look like by the end of a milestone. Defaults to `false`.
- `sprints` : number of sprints in the milestone (defaults to 2 if not specified)
- `minTasksPerSprint` : minimum number of tasks expected to be completed per sprint (defaults to 1 if not specified)

**Example `gh_metrics_config.json` file:**

```json
{
  "version": "2.0",
  "projectName": "College Toolbox",
  "managers": ["Poggecci"],
  "milestones": {
    "Milestone #1": {
      "startDate": "2024-01-15",
      "endDate": "2024-02-09",
      "projectedGroupGrade": 100.0
    },
    "Milestone #2": {
      "startDate": "2024-02-12",
      "endDate": "2024-03-08",
      "projectedGroupGrade": 100.0
    },
    "Milestone #3": {
      "startDate": "2024-03-11",
      "endDate": "2024-04-05",
      "projectedGroupGrade": 100.0
    }
  },
  "lectureTopicTaskQuota": 0,
  "countOpenIssues": false,
  "sprints": 2,
  "minTasksPerSprint": 1,
  ""
}
```

3. If working locally, push the changes onto the remote such that they are visible on the main branch from the Github page for the repository

##### Workflow setup

1. On your repository's main branch, create the directory .github/workflows

```bash
mkdir .github/workflows
```

2. Copy the `dev-metrics.yml` file from this repo onto the `.github/workflows` directory from your repository.
3. Commit and push the changes.

You should now see a new Workflow on the **Actions** tab on Github. This will run daily, but can be triggered manually.

# **_End of Actions Setup_**

### Local Run Setup

When running locally, you can setup your config file to generate metrics for multiple teams, but remember that you will only be able to see the issues and thus metrics of teams you have permissions to view or are a part of.

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

   - `organization` : this will be used as the name of the organization
   - `milestoneStartsOn` : the `datetime` at which the milestone starts
   - `milestoneEndsOn` : the `datetime` at which the milestone ends
     if either one of `milestoneStartsOn` or `milestoneEndsOn` is missing then there will
     not be any use of the decay function in the calculation of the score of issues
   - `teams` : this field is a list of key/value pairs. The key of each pair is the team
     name. It _must_ also be the name of the project board owned by that team from which the
     closed issues, with their urgency and difficulty can be collected. The value of each
     pair is a JSON with the fields
     - `managers` : which contains a list of the GitHub logins that belong to the managers
       of the team and therefore do not get any points for closing issues, even if they
       were assigned to them.
     - `milestone` : which must be the name of the milestone to use, so that different
       projects can use different milestone names
     - `milestoneGrade` : which specifies the maximum grade achievable for this milestone, determined by the professor based on the team's overall performance (what they promised vs delivered, etc.).
   - `lectureTopicTaskQuota` : number of lecture topic tasks expected to be completed by each developer by the end of the course.
   - `sprints` : number of sprints in the milestone (defaults to 2 if not specified)
   - `minTasksPerSprint` : minimum number of tasks expected to be completed per sprint (defaults to 1 if not specified)
   - `countOpenIssues` : boolean flag to determine if open issues should be included in the score calculation (defaults to false if not specified)

2. Run the script from the command line:

```bash
poetry run python exportMetricsForCourseMilestone.py <json_config_file_path>
```

#### Example

```bash
poetry run python exportMetricsForCourseMilestone.py exampleConfig.json
```

**Example `exampleConfig.json` file:**

```json
{
  "organization": "uprm-inso4116-2023-2024-S1",
  "teams": {
    "College Toolbox": {
      "managers": ["Ryan8702", "EdwinC1339"],
      "milestone": "Milestone #1",
      "milestoneGrade": 100.0
    }
  },
  "milestoneStartsOn": "2023-08-14",
  "milestoneEndsOn": "2023-09-16",
  "lectureTopicTaskQuota": 4,
  "sprints": 2,
  "minTasksPerSprint": 1,
  "countOpenIssues": false
}
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
