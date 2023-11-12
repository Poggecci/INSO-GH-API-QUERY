# Team Metrics Generator

This script generates team metrics for a specified milestone in a GitHub organization. It collects data on points closed and percent contribution for each developer in the specified teams and outputs the results to CSV files.
## Usage

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
4. The course is described in a JSON file. The fields of the JSON file are
   - `organization` this will be used as the name of the organization
   - `teams` this field is a list of key/value pairs. The key of each pair is the team
     name. It _must_ also be the name of the project board owned by that team from which the
     closed issues, with their urgency and difficulty can be collected. The value of each
     pair is a JSON with the fields 
     - `managers` which contains a list of the GitHub logins that belong to the managers
       of the team
     - `milestone` which must be the name of the milestone to use, so that different
       projects can use different milestone names
  5. Run the script from the command line:
```
poetry run python exportMetricsForCourseMilestone.py <some course desctiption>.json
```
### Example:
```
poetry run python exportMetricsForCourseMilestone.py uprm-inso4116-2023-2024-s1.json
```
The script will generate CSV files containing team metrics for each specified team. The CSV files will be named `<milestone>-<team>-<organization>.csv`.
