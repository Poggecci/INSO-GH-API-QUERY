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
   allows you to keep the token in an encrypted file.  For example,
```
export GITHUB_API_TOKEN=`pass show GitHub/uprm-inso4116-2023-2024-s1`
```
### Points Closed Team Metrics
1. The course is described in a JSON file. The fields of the JSON file are
   - `organization` this will be used as the name of the organization
   - `milestone` this is the name of the milestone to use, all teams and projects must use
     the same milestone names. For example, "Milestone 1", "Milestone 2", etc. or
     "Milestone #1", "Milestone #2", etc., but if one team uses e.g. "Milestone #1" and
     that's the name on the milestone field, then only milestone data for a milestone of
     that name will be collected.
   - `teams` this field is a list of key/value pairs. The key of each pair is the team
     name. It must also be the name of the project board owned by that team from which the
     closed issues, with their urgency and difficulty can be collected. The value of each
     pair is the list of logins that should be counted as managers and therefore do not
     get any points for closing issues, even if they were assigned to them.
2. Run the script from the command line:
```
poetry run python exportMetricsForCourseMilestone.py <json_config_file_path>
```
#### Example:
```
poetry run python exportMetricsForCourseMilestone.py course_config.json
```
The script will generate CSV files containing team metrics for each specified team. The CSV files will be named `<milestone>-<team>-<organization>.csv`.

### Lecture Topic Tasks
1. The course is described in a JSON file. The fields of the JSON file are
   - `organization` this will be used as the name of the organization
   - `teams` this field is a list of key/value pairs. The key of each pair is the team
     name. It must also be the name of the project board owned by that team from which the
     closed issues can be collected. The value of each
     pair is the list of logins that should be counted as managers.
   - `lecture_topic_tasks_quota` this field specifies how many lecture topic tasks each member of the team is expected to complete.
2. Run the script from the command line:
```
poetry run python exportMetricsForLectureTopicTasks.py <json_config_file_path>
```
#### Example:
```
poetry run python exportMetricsForLectureTopicTasks.py course_config.json
```
The script will generate CSV files containing team metrics for each specified team. The CSV files will be named `Lecture Topic Tasks-<team>-<organization>.csv`.

