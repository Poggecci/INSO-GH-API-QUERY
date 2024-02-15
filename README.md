# Team Metrics Generator

This script generates team metrics for a specified milestone in a GitHub organization. It collects data on points closed and percent contribution for each developer in the specified teams and outputs the results to CSV files. You can now also use Github Actions generate the metrics as a Markdown that is stored in a separate branch of your repository.

## Usage

### Github Actions

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
2. Populate the .json file with the following fields: (An example can be found in the `exampleActionsConfig.json` file in this repo)

- `projectName` : Name of the Github Project associated with your repository
- `managers` : a list of the GitHub logins (usernames) that belong to the managers
- `milestoneName` : name of the current milestone
- `projectedMilestoneGroupGrade` which specifies the maximum grade achievable for this milestone, determined by the professor based on the team's overall performance (what they promised vs delivered, etc.).
- `milestoneStartDate` : start date of the current milestone in the format YYYY-MM-DD
- `milestoneEndDate` : end date of the current milestone in the format YYYY-MM-DD
- `lectureTopicTaskQuota` : number of lecture topic tasks expected to be completed by each developer this milestone

3. If working locally, push the changes onto the remote such that they are visible on the main branch from the Github page for the repository

##### Workflow setup

1. On your repository's main branch, create the directory .github/workflows

```bash
mkdir .github/workflows
```

2. Copy the `dev-metrics.yml` file from this repo onto the `.github/workflows` directory from your repository.
3. Commit and push the changes.

You should now see a new Workflow on the **Actions** tab on Github. This will run daily, but can be triggered manually.

# ***End of Actions Setup***
</br>
</br>
</br>
</br>
</br>
</br>
</br>
</br>
</br>

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
