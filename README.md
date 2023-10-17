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
4. Run the script from the command line:
```
poetry run python exportMetricsForCourseMilestone.py <organization> <milestone>
```
Replace `<organization>` with the name of your GitHub organization and `<milestone>` with the desired milestone.
### Example:
```
poetry run python exportMetricsForCourseMilestone.py "uprm-inso4116-2023-2024-s1" "Milestone #1"
```
The script will generate CSV files containing team metrics for each specified team. The CSV files will be named `<milestone>-<team>-<organization>.csv`.
