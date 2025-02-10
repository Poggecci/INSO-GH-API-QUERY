from src.io.markdown import writeWeeklyDiscussionParticipationToMarkdown

participation = {
    "dev1": {0, 2},
    "dev2": {0, 1, 2, 3, 4},
    "dev3": {0, 1, 2},
    "dev4": {1, 3, 4},
    "dev5": {0, 4},
    "dev6": {0, 1, 3, 4},
    "dev7": {},
}
md_file_path = "test/io/discussion_participation/result.md"

with open(md_file_path, mode="w"):
    pass

writeWeeklyDiscussionParticipationToMarkdown(
    participation=participation, weeks=5, md_file_path=md_file_path
)
