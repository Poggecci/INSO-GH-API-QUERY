# INSO4XXX Course Project Developer Grading Guide

This document outlines the requirements and expectations for the individual contribution grading in the UPRM Software Engineering courses (INSO4101, INSO4115, INSO4116, INSO4117). The individual contribution makes up 60% of your grade each milestone (the other 40% is the group grade, roughly determined by the amount of features delivered versus the amount promised). It covers issue requirements (ensuring your issues actually get counted), student expectations, and factors affecting scoring.

## Issue Requirements

For an issue to be counted towards a student's grade, it must meet the following criteria:

1. **Milestone Association**: The issue must be associated with the correct milestone for the current grading period.

2. **Closure Status**:
   The issue must be **closed**. If you'd like to see what your "predicted" score would be if you closed all the issues you have open, consider setting up [metrics](https://github.com/Poggecci/INSO-GH-API-QUERY) on your team's repository and setting the `countOpenIssues` setting in the config to `true`

3. **Closed by Manager**: Only issues closed by **team managers** are accredited.

4. **Field Population**: Both `Urgency` and `Difficulty` fields must be populated with numerical values.

5. **Assignment**: The issue must be assigned to at least one team member who is not a manager.

## Student Expectations

To achieve a good grade each milestone, students should:

1. **Complete Minimum Tasks**: Meet the minimum number of tasks required per sprint. Milestones are divided up into equal time periods called _sprints_ and students who do not complete the minimum each sprint will receive a **0** on the individual portion of that milestone (as of the time of writing of this document there are **2** sprints in a milestone, with **1** task minimum per sprint)

2. **Create Tasks Early**: Create issues as early as you can, even if they aren't well defined at first. Issues are worth fewer points when they are created near the end of a milestone. Instead, create early and add more details to the issue as you talk with team members or get new insights.

3. **No Empty Descriptions**: Issue descriptions should never be empty. Actually state what the problem you're trying to solve is, what is needed to solve it (requirements), and what the solution you're going for is.

4. **Take on Varied Tasks**: Work on a mix of tasks with different Difficulty and Urgency levels.

5. **Complete Lecture Topic Tasks**: These are issues relating to topics present in the lectures and unique to the course (ie. a task relating to setting up Integration Testing while you're taking the INSO4117 course). You can mark a task as a Lecture Topic task by adding "`[Lecture Topic Task]`" to the issue title or by adding a label titled "`lecture topic task`" to the issue. Students are expected to complete at least **4** total by the end of the course, where they must complete at least **1** lecture topic task in at least **2** milestones.

## Factors Affecting Issue Scoring

Several factors influence the calculated score for each issue:

1. **Issue Base Points Calculation**:

   ```
   Issue Score = (Difficulty * Urgency * Decay) + Modifier
   ```

   - Decay is optional and based on how early in the milestone the issue is created.

2. **Documentation Bonus**:

   - 10% bonus on the issue score if a manager reacts with 🎉 to the issue or a comment.
   - Only attributed to non-manager authors.

3. **Point Distribution**:

   - Points are divided equally among all non-manager assignees of an issue.

## Grade Calculation Info

1. **Developer Points**:

   - By the end of each milestone, each developer will have a points count equal to the sum of all their issue scores and bonuses.

2. **Contribution Percent**:

   - Equal to `100% * developer points / sum of points closed by all developers`. If your % is around or greater than `100 / # of developers`, expect a good grade for the milestone.

3. **Grading Benchmark**:

   - A benchmark is calculated based on the average points closed by all developers and adjusted by the group project grade (The lower the group project grade, the higher the benchmark, meaning developers need to close more points to get a perfect score)

4. **Sprint Completion**:

   - Failing to complete the minimum tasks in any sprint results in a grade of 0 for the entire milestone.

5. **Final Grade Calculation**:

   ```
   Expected Grade = min((Developer Points / Benchmark) * Milestone Grade, 100.0)
   ```

## Additional Notes

- The grading system uses a decay function to encourage early creation of issues.
- Managers' contributions to issues are tracked but not counted in the main scoring to avoid skewing the results.
- Regular participation throughout the milestone period is crucial for achieving a good grade. ANY sprint where a developer closed 0 tasks will result in the individual contribution milestone grade for that developer being **0**
- The maximum grade is capped at 100%, even if a student exceeds the benchmark significantly.
